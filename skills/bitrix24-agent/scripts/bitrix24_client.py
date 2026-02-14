#!/usr/bin/env python3
"""Bitrix24 REST client baseline for skills/bitrix24-agent.

Features:
- webhook and OAuth auth modes,
- REST v2 and REST v3 URL support,
- retry with jitter for transient failures,
- optional OAuth refresh callback,
- optional shared limiter hook.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple


@dataclass
class TenantConfig:
    domain: str
    auth_mode: str  # "webhook" or "oauth"
    webhook_user_id: Optional[str] = None
    webhook_code: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


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
        return self.code in {"QUERY_LIMIT_EXCEEDED"} or self.status >= 500


class NoopRateLimiter:
    def acquire(self, key: str) -> None:
        _ = key
        return


RefreshCallback = Callable[[TenantConfig], Tuple[str, Optional[str]]]


class Bitrix24Client:
    def __init__(
        self,
        tenant: TenantConfig,
        *,
        timeout: int = 30,
        max_attempts: int = 5,
        rate_limiter: Optional[NoopRateLimiter] = None,
        refresh_callback: Optional[RefreshCallback] = None,
    ) -> None:
        self.tenant = tenant
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.rate_limiter = rate_limiter or NoopRateLimiter()
        self.refresh_callback = refresh_callback

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
                payload["auth"] = self.tenant.access_token

            try:
                result = self._post_json(url, payload)
                self._raise_for_api_error(result, status=200)
                return result
            except BitrixAPIError as exc:
                if (
                    exc.code == "expired_token"
                    and not refreshed
                    and self.tenant.auth_mode == "oauth"
                    and self.refresh_callback
                ):
                    access_token, refresh_token = self.refresh_callback(self.tenant)
                    self.tenant.access_token = access_token
                    if refresh_token:
                        self.tenant.refresh_token = refresh_token
                    refreshed = True
                    continue

                if not exc.retryable or attempt == self.max_attempts:
                    raise

                self._backoff(attempt)
            except urllib.error.HTTPError as exc:
                status, body = self._read_http_error(exc)
                parsed = self._safe_json_parse(body)
                api_exc = self._to_api_error(status=status, body=parsed or {})

                if (
                    api_exc.code == "expired_token"
                    and not refreshed
                    and self.tenant.auth_mode == "oauth"
                    and self.refresh_callback
                ):
                    access_token, refresh_token = self.refresh_callback(self.tenant)
                    self.tenant.access_token = access_token
                    if refresh_token:
                        self.tenant.refresh_token = refresh_token
                    refreshed = True
                    continue

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

    def _build_url(self, *, method: str, rest_v3: bool) -> str:
        domain = self.tenant.domain.strip().rstrip("/")
        if not domain.startswith("http://") and not domain.startswith("https://"):
            domain = f"https://{domain}"

        if self.tenant.auth_mode == "webhook":
            if not self.tenant.webhook_user_id or not self.tenant.webhook_code:
                raise ValueError("webhook_user_id and webhook_code are required for webhook mode")
            if rest_v3:
                return (
                    f"{domain}/rest/api/"
                    f"{self.tenant.webhook_user_id}/{self.tenant.webhook_code}/{method}"
                )
            return (
                f"{domain}/rest/"
                f"{self.tenant.webhook_user_id}/{self.tenant.webhook_code}/{method}"
            )

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
        # 0.5, 1, 2, 4, 8 + jitter
        base_ms = 500 * (2 ** (attempt - 1))
        jitter_ms = random.randint(0, 250)
        time.sleep((base_ms + jitter_ms) / 1000.0)


def refresh_via_oauth_server(tenant: TenantConfig) -> Tuple[str, Optional[str]]:
    """Refresh OAuth token using oauth.bitrix24.tech.

    Required env:
    - B24_CLIENT_ID
    - B24_CLIENT_SECRET
    """
    if not tenant.refresh_token:
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
            "refresh_token": tenant.refresh_token,
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
    refresh_token = body.get("refresh_token")
    if not access_token:
        raise BitrixAPIError("OAuth refresh returned no access_token", code="INVALID_REFRESH_RESPONSE")
    return access_token, refresh_token


def load_tenant_config_from_env() -> TenantConfig:
    domain = os.getenv("B24_DOMAIN", "").strip()
    auth_mode = os.getenv("B24_AUTH_MODE", "webhook").strip().lower()
    if not domain:
        raise ValueError("B24_DOMAIN is required")
    if auth_mode not in {"webhook", "oauth"}:
        raise ValueError("B24_AUTH_MODE must be 'webhook' or 'oauth'")

    if auth_mode == "webhook":
        return TenantConfig(
            domain=domain,
            auth_mode="webhook",
            webhook_user_id=os.getenv("B24_WEBHOOK_USER_ID", "").strip() or None,
            webhook_code=os.getenv("B24_WEBHOOK_CODE", "").strip() or None,
        )

    return TenantConfig(
        domain=domain,
        auth_mode="oauth",
        access_token=os.getenv("B24_ACCESS_TOKEN", "").strip() or None,
        refresh_token=os.getenv("B24_REFRESH_TOKEN", "").strip() or None,
    )


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
        help="Use /rest/api/ path",
    )
    parser.add_argument(
        "--auto-refresh",
        action="store_true",
        help="Enable token refresh via oauth.bitrix24.tech (OAuth mode only)",
    )
    args = parser.parse_args()

    params = json.loads(args.params)
    tenant = load_tenant_config_from_env()
    refresh_callback = refresh_via_oauth_server if args.auto_refresh else None
    client = Bitrix24Client(tenant, refresh_callback=refresh_callback)
    response = client.call(args.method, params=params, rest_v3=args.rest_v3)
    print(json.dumps(response, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
