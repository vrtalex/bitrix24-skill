#!/usr/bin/env python3
"""Bitrix24 REST client baseline for skills/bitrix24-agent.

Features:
- webhook and OAuth auth modes,
- REST v2 and REST v3 URL support,
- retry with jitter for transient failures,
- optional OAuth refresh callback with thread-safe locking,
- optional shared limiter hook,
- circuit breaker for fatal errors,
- secrets masking in output,
- pagination and batch helpers.
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import random
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple

# Maximum backoff delay in milliseconds to prevent overflow
MAX_BACKOFF_MS = 30_000

# Secrets patterns to mask in output
_SECRETS_PATTERNS = [
    re.compile(r'"(access_token|refresh_token|auth|webhook_code|client_secret)"\s*:\s*"[^"]*"', re.IGNORECASE),
    re.compile(r'(access_token|refresh_token|auth)=[^&\s"]+', re.IGNORECASE),
]

# Fatal error codes that should not be retried
FATAL_ERROR_CODES: Set[str] = frozenset({
    "WRONG_AUTH_TYPE",
    "insufficient_scope",
    "INVALID_CREDENTIALS",
    "NO_AUTH_FOUND",
    "METHOD_NOT_FOUND",
    "ERROR_METHOD_NOT_FOUND",
    "INVALID_REQUEST",
    "ACCESS_DENIED",
    "PAYMENT_REQUIRED",
})


def mask_secrets(text: str) -> str:
    """Mask sensitive values in text for safe logging."""
    result = text
    for pattern in _SECRETS_PATTERNS:
        result = pattern.sub(lambda m: m.group(0).split(":")[0] + ':"***"' if ":" in m.group(0) else m.group(0).split("=")[0] + "=***", result)
    return result


def secure_compare(a: Optional[str], b: Optional[str]) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    if a is None or b is None:
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


@dataclass(frozen=True)
class TenantConfig:
    """Immutable tenant configuration."""
    domain: str
    auth_mode: str  # "webhook" or "oauth"
    webhook_user_id: Optional[str] = None
    webhook_code: Optional[str] = None
    # Note: tokens are stored in TokenStore, not here for OAuth mode


@dataclass
class TokenStore:
    """Thread-safe mutable token storage for OAuth mode."""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def get_tokens(self) -> Tuple[Optional[str], Optional[str]]:
        with self._lock:
            return self.access_token, self.refresh_token

    def set_tokens(self, access_token: str, refresh_token: Optional[str] = None) -> None:
        with self._lock:
            self.access_token = access_token
            if refresh_token is not None:
                self.refresh_token = refresh_token


class BitrixAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status: int = 0,
        code: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.payload = payload or {}

    @property
    def retryable(self) -> bool:
        """Check if error is retryable (transient)."""
        if self.code in FATAL_ERROR_CODES:
            return False
        return self.code in {"QUERY_LIMIT_EXCEEDED"} or self.status >= 500

    @property
    def fatal(self) -> bool:
        """Check if error is fatal and should stop retry loops entirely."""
        return self.code in FATAL_ERROR_CODES


class NoopRateLimiter:
    def acquire(self, key: str) -> None:
        _ = key
        return


RefreshCallback = Callable[[TenantConfig, TokenStore], Tuple[str, Optional[str]]]


class Bitrix24Client:
    def __init__(
        self,
        tenant: TenantConfig,
        *,
        token_store: Optional[TokenStore] = None,
        timeout: int = 30,
        max_attempts: int = 5,
        rate_limiter: Optional[NoopRateLimiter] = None,
        refresh_callback: Optional[RefreshCallback] = None,
    ) -> None:
        self.tenant = tenant
        self.token_store = token_store or TokenStore()
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.rate_limiter = rate_limiter or NoopRateLimiter()
        self.refresh_callback = refresh_callback
        self._refresh_lock = threading.Lock()

    def call(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        rest_v3: bool = False,
    ) -> Dict[str, Any]:
        payload = dict(params or {})
        url = self._build_url(method=method, rest_v3=rest_v3)

        refreshed = False
        for attempt in range(1, self.max_attempts + 1):
            self.rate_limiter.acquire(self.tenant.domain)
            if self.tenant.auth_mode == "oauth":
                access_token, _ = self.token_store.get_tokens()
                payload["auth"] = access_token

            try:
                result = self._post_json(url, payload)
                self._raise_for_api_error(result, status=200)
                return result
            except BitrixAPIError as exc:
                # Handle expired token with thread-safe refresh
                if (
                    exc.code == "expired_token"
                    and not refreshed
                    and self.tenant.auth_mode == "oauth"
                    and self.refresh_callback
                ):
                    refreshed = self._try_refresh_token()
                    if refreshed:
                        continue

                # Fatal errors should not be retried
                if exc.fatal:
                    raise

                if not exc.retryable or attempt == self.max_attempts:
                    raise

                self._backoff(attempt)
            except urllib.error.HTTPError as exc:
                status, body = self._read_http_error(exc)
                parsed = self._safe_json_parse(body)
                api_exc = self._to_api_error(status=status, body=parsed or {})

                # Handle expired token with thread-safe refresh
                if (
                    api_exc.code == "expired_token"
                    and not refreshed
                    and self.tenant.auth_mode == "oauth"
                    and self.refresh_callback
                ):
                    refreshed = self._try_refresh_token()
                    if refreshed:
                        continue

                # Fatal errors should not be retried
                if api_exc.fatal:
                    raise api_exc

                if not api_exc.retryable or attempt == self.max_attempts:
                    raise api_exc
                self._backoff(attempt)
            except urllib.error.URLError as exc:
                if attempt == self.max_attempts:
                    raise BitrixAPIError(
                        f"Network error: {exc}",
                        status=0,
                        code="NETWORK_ERROR",
                    ) from exc
                self._backoff(attempt)

        raise BitrixAPIError("Retries exhausted", code="RETRIES_EXHAUSTED")

    def _try_refresh_token(self) -> bool:
        """Thread-safe token refresh using singleflight pattern."""
        acquired = self._refresh_lock.acquire(blocking=False)
        if acquired:
            try:
                access_token, refresh_token = self.refresh_callback(self.tenant, self.token_store)
                self.token_store.set_tokens(access_token, refresh_token)
                return True
            except Exception:
                # Refresh failed, let caller handle retry
                return False
            finally:
                self._refresh_lock.release()
        else:
            # Another thread is refreshing, wait for it
            with self._refresh_lock:
                # Lock acquired means refresh is done, tokens should be updated
                pass
            return True

    def iter_list(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        rest_v3: bool = False,
        page_size: int = 50,
    ) -> Iterator[Dict[str, Any]]:
        """Iterate over all items from a paginated list method.

        Yields individual items from result list. Automatically handles pagination.
        """
        start = 0
        base_params = dict(params or {})

        while True:
            page_params = {**base_params, "start": start}
            response = self.call(method, params=page_params, rest_v3=rest_v3)

            result = response.get("result", [])
            if isinstance(result, list):
                for item in result:
                    yield item
            elif isinstance(result, dict):
                # Some methods return dict with items
                for item in result.values():
                    if isinstance(item, dict):
                        yield item

            # Check for next page
            next_start = response.get("next")
            if next_start is None:
                break
            start = next_start

    def batch(
        self,
        commands: Dict[str, str],
        *,
        halt: bool = True,
        rest_v3: bool = False,
    ) -> Dict[str, Any]:
        """Execute batch request with multiple commands.

        Args:
            commands: Dict of {name: "method?param=value"} command strings
            halt: Stop on first error if True
            rest_v3: Use REST v3 endpoint

        Returns:
            Full batch response with result, result_error, result_total, etc.
        """
        if len(commands) > 50:
            raise ValueError("Batch is limited to 50 commands")

        params = {
            "halt": 1 if halt else 0,
            "cmd": commands,
        }
        return self.call("batch", params=params, rest_v3=rest_v3)

    def _build_url(self, *, method: str, rest_v3: bool) -> str:
        domain = self.tenant.domain.strip().rstrip("/")
        if not domain.startswith("http://") and not domain.startswith("https://"):
            domain = f"https://{domain}"

        if self.tenant.auth_mode == "webhook":
            if not self.tenant.webhook_user_id or not self.tenant.webhook_code:
                raise ValueError("webhook_user_id and webhook_code are required for webhook mode")
            # REST v3 for webhooks uses same path structure as v2
            # The /rest/api/ prefix is for OAuth mode only per Bitrix24 docs
            return (
                f"{domain}/rest/"
                f"{self.tenant.webhook_user_id}/{self.tenant.webhook_code}/{method}"
            )

        # OAuth mode
        if rest_v3:
            return f"{domain}/rest/api/{method}"
        return f"{domain}/rest/{method}"

    def _post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        req = urllib.request.Request(
            url=url,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            data=json.dumps(payload).encode("utf-8"),
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8")
            parsed = self._safe_json_parse(raw)
            if parsed is None:
                raise BitrixAPIError("Invalid JSON response", code="INVALID_JSON")
            return parsed

    def _raise_for_api_error(self, body: Dict[str, Any], *, status: int) -> None:
        api_error = self._to_api_error(status=status, body=body)
        if api_error.code:
            raise api_error

    def _to_api_error(self, *, status: int, body: Dict[str, Any]) -> BitrixAPIError:
        # REST v2 format
        if "error" in body and isinstance(body["error"], str):
            code = body.get("error", "")
            msg = body.get("error_description", code) or code
            return BitrixAPIError(msg, status=status, code=code, payload=body)

        # REST v3 format
        if isinstance(body.get("error"), dict):
            err = body["error"]
            code = err.get("code", "")
            msg = err.get("message", code) or code
            return BitrixAPIError(msg, status=status, code=code, payload=body)

        return BitrixAPIError("", status=status, code="", payload=body)

    @staticmethod
    def _read_http_error(exc: urllib.error.HTTPError) -> Tuple[int, str]:
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = ""
        return exc.code, body

    @staticmethod
    def _safe_json_parse(raw: str) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return {"result": data}
        return data

    @staticmethod
    def _backoff(attempt: int) -> None:
        # Exponential backoff with jitter, capped to prevent overflow
        base_ms = min(500 * (2 ** (attempt - 1)), MAX_BACKOFF_MS)
        jitter_ms = random.randint(0, 250)
        time.sleep((base_ms + jitter_ms) / 1000.0)


def refresh_via_oauth_server(tenant: TenantConfig, token_store: TokenStore) -> Tuple[str, Optional[str]]:
    """Refresh OAuth token using oauth.bitrix24.tech.

    Required env:
    - B24_CLIENT_ID
    - B24_CLIENT_SECRET
    """
    _, refresh_token = token_store.get_tokens()
    if not refresh_token:
        raise BitrixAPIError("refresh_token missing", code="MISSING_REFRESH_TOKEN")

    client_id = os.getenv("B24_CLIENT_ID", "")
    client_secret = os.getenv("B24_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise BitrixAPIError(
            "B24_CLIENT_ID and B24_CLIENT_SECRET are required for refresh",
            code="MISSING_CLIENT_CREDENTIALS",
        )

    query = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }
    )
    url = f"https://oauth.bitrix24.tech/oauth/token/?{query}"
    req = urllib.request.Request(url=url, method="GET", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    if "error" in body:
        raise BitrixAPIError(
            body.get("error_description", body["error"]),
            code=body["error"],
            payload=body,
        )

    access_token = body.get("access_token")
    new_refresh_token = body.get("refresh_token")
    if not access_token:
        raise BitrixAPIError("OAuth refresh returned no access_token", code="INVALID_REFRESH_RESPONSE")
    return access_token, new_refresh_token


def load_tenant_config_from_env() -> Tuple[TenantConfig, TokenStore]:
    """Load tenant configuration and token store from environment variables."""
    domain = os.getenv("B24_DOMAIN", "").strip()
    auth_mode = os.getenv("B24_AUTH_MODE", "webhook").strip().lower()
    if not domain:
        raise ValueError("B24_DOMAIN is required")
    if auth_mode not in {"webhook", "oauth"}:
        raise ValueError("B24_AUTH_MODE must be 'webhook' or 'oauth'")

    if auth_mode == "webhook":
        tenant = TenantConfig(
            domain=domain,
            auth_mode="webhook",
            webhook_user_id=os.getenv("B24_WEBHOOK_USER_ID", "").strip() or None,
            webhook_code=os.getenv("B24_WEBHOOK_CODE", "").strip() or None,
        )
        return tenant, TokenStore()

    tenant = TenantConfig(
        domain=domain,
        auth_mode="oauth",
    )
    token_store = TokenStore(
        access_token=os.getenv("B24_ACCESS_TOKEN", "").strip() or None,
        refresh_token=os.getenv("B24_REFRESH_TOKEN", "").strip() or None,
    )
    return tenant, token_store


def main() -> None:
    parser = argparse.ArgumentParser(description="Bitrix24 REST call helper")
    parser.add_argument("method", help="Bitrix24 method, e.g. crm.lead.list")
    parser.add_argument(
        "--params",
        default="{}",
        help="JSON object with method params",
    )
    parser.add_argument(
        "--rest-v3",
        action="store_true",
        help="Use /rest/api/ path (OAuth mode only)",
    )
    parser.add_argument(
        "--auto-refresh",
        action="store_true",
        help="Enable token refresh via oauth.bitrix24.tech (OAuth mode only)",
    )
    parser.add_argument(
        "--mask-secrets",
        action="store_true",
        default=True,
        help="Mask sensitive values in output (default: true)",
    )
    parser.add_argument(
        "--no-mask-secrets",
        action="store_false",
        dest="mask_secrets",
        help="Disable secrets masking in output",
    )
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in --params: {e}", file=__import__("sys").stderr)
        raise SystemExit(1)

    tenant, token_store = load_tenant_config_from_env()
    refresh_callback = refresh_via_oauth_server if args.auto_refresh else None
    client = Bitrix24Client(tenant, token_store=token_store, refresh_callback=refresh_callback)
    response = client.call(args.method, params=params, rest_v3=args.rest_v3)

    output = json.dumps(response, ensure_ascii=False, indent=2)
    if args.mask_secrets:
        output = mask_secrets(output)
    print(output)


if __name__ == "__main__":
    main()
