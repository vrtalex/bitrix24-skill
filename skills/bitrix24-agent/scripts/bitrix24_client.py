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
import fnmatch
import hashlib
import hmac
import json
import os
import pathlib
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Set, Tuple, Union

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

# Maximum backoff delay in milliseconds to prevent overflow
MAX_BACKOFF_MS = 30_000

# Secrets patterns to mask in output
_SECRETS_PATTERNS = [
    re.compile(r'"(access_token|refresh_token|auth|webhook_code|client_secret|application_token)"\s*:\s*"[^"]*"', re.IGNORECASE),
    re.compile(r'(access_token|refresh_token|auth|application_token)=[^&\s"]+', re.IGNORECASE),
]

# Fatal error codes that should not be retried and must stop retry/worker loops.
# Includes auth/permission failures, dead OAuth refresh tokens (invalid_grant), and
# OVERLOAD_LIMIT (a manual portal block that only Bitrix24 support can clear).
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
    "invalid_grant",
    "OVERLOAD_LIMIT",
})

# Limit codes that are transient but must NOT be retried inside a single call():
# OPERATION_TIME_LIMIT (HTTP 429) blocks one method for ~10 minutes, so in-call retry
# only burns attempts. Callers (e.g. the offline worker) should back off and resume later.
NON_RETRYABLE_LIMIT_CODES: Set[str] = frozenset({
    "OPERATION_TIME_LIMIT",
})

DEFAULT_METHOD_ALLOWLIST: Tuple[str, ...] = (
    # Base allowlist is intentionally narrow; packs expand it.
    "batch",
)

PACK_METHOD_ALLOWLIST: Dict[str, Tuple[str, ...]] = {
    "core": (
        "batch",
        "user.*",
        "department.*",
        "crm.*",
        "tasks.task.*",
        "task.*",
        "event.*",
    ),
    "comms": (
        "im.*",
        "imbot.*",
        "imopenlines.*",
        "imconnector.*",
        "messageservice.*",
        "mailservice.*",
        "telephony.*",
    ),
    "automation": (
        "bizproc.*",
        "crm.automation.*",
        "lists.*",
    ),
    "collab": (
        "sonet_group.*",
        "socialnetwork.*",
        "log.*",
        "calendar.*",
        "vote.*",
    ),
    "content": (
        "disk.*",
        "file.*",
        "files.*",
        "documentgenerator.*",
    ),
    "boards": (
        "tasks.api.scrum.*",
        "tasks.scrum.*",
    ),
    "commerce": (
        "sale.*",
        "catalog.*",
    ),
    "services": (
        "booking.*",
        "calendar.*",
        "timeman.*",
    ),
    "platform": (
        "entity.*",
        "biconnector.*",
        "ai.*",
    ),
    "sites": (
        "landing.*",
    ),
    "compliance": (
        "userconsent.*",
        "sign.*",
    ),
    "diagnostics": (
        "method.get",
        "methods",
        "events",
        "feature.get",
        "scope",
        "server.time",
    ),
    "bots": (
        "imbot.v2.*",
        "imbot.*",
    ),
    "booking": (
        "booking.*",
    ),
    "mail": (
        "mail.*",
    ),
    "templates": (
        "tasks.template.*",
    ),
}

DEFAULT_PACKS: Tuple[str, ...] = ("core",)

METHOD_NAME_SCHEMA: Dict[str, Any] = {
    "type": "string",
    # Mixed case allowed: v2/v3 namespaces are case-sensitive (e.g. imbot.v2.Bot.list).
    "pattern": r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*$",
    "minLength": 3,
}

GENERIC_PARAMS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
}

BATCH_PARAMS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["cmd"],
    "additionalProperties": True,
    "properties": {
        "cmd": {
            "type": "object",
            "minProperties": 1,
            "maxProperties": 50,
            "additionalProperties": {"type": "string"},
        },
        "halt": {
            "anyOf": [
                {"type": "boolean"},
                {"type": "integer", "enum": [0, 1]},
            ]
        },
    },
}

EVENT_OFFLINE_GET_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "clear": {
            "anyOf": [
                {"type": "integer", "enum": [0, 1]},
                {"type": "string", "enum": ["0", "1"]},
            ]
        }
    },
}

WRITE_METHOD_RE = re.compile(r"(?:^|\.)(add|update|set|register|bind|import|complete|start|stop|move|clear)$")
DESTRUCTIVE_METHOD_RE = re.compile(r"(?:^|\.)(delete|remove|recyclebin|unregister|unbind)$")


def mask_secrets(text: str) -> str:
    """Mask sensitive values in text for safe logging."""
    result = text
    for pattern in _SECRETS_PATTERNS:
        result = pattern.sub(lambda m: m.group(0).split(":")[0] + ':"***"' if ":" in m.group(0) else m.group(0).split("=")[0] + "=***", result)
    return result


def _result_rows(response: Dict[str, Any]) -> Tuple[Optional[List[Any]], Optional[Tuple[str, ...]]]:
    """Locate the row array in a response: top-level list result, or result.items (crm.item.*)."""
    result = response.get("result")
    if isinstance(result, list):
        return result, ("result",)
    if isinstance(result, dict) and isinstance(result.get("items"), list):
        return result["items"], ("result", "items")
    return None, None


def _row_id(row: Any) -> Any:
    if isinstance(row, dict):
        return row.get("id") or row.get("ID")
    return row


def shape_output(response: Dict[str, Any], mode: str = "full", max_items: int = 0) -> str:
    """Render a response for the agent. Opt-in token economy; 'full' = unchanged default.

    - full    : pretty JSON (indent=2).
    - compact : minified JSON (no whitespace).
    - summary : a digest of list results — {count, ids(<=10), next, total}.
    max_items>0 truncates the result rows (list or result.items) and adds a _truncated marker.
    Never mutates the input.
    """
    if mode == "summary":
        rows, _ = _result_rows(response)
        digest = {
            "count": len(rows) if rows is not None else None,
            "ids": [_row_id(r) for r in (rows or [])[:10]],
            "next": response.get("next"),
            "total": response.get("total"),
        }
        return json.dumps(digest, ensure_ascii=False, separators=(",", ":"))

    payload = response
    if max_items and max_items > 0:
        rows, path = _result_rows(response)
        if rows is not None and len(rows) > max_items:
            payload = dict(response)
            payload["_truncated"] = {"shown": max_items, "of": len(rows)}
            if path == ("result",):
                payload["result"] = rows[:max_items]
            else:
                payload["result"] = dict(response["result"])
                payload["result"]["items"] = rows[:max_items]

    if mode == "compact":
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(payload, ensure_ascii=False, indent=2)


def parse_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _lock_handle(fh: Any) -> None:
    if fcntl is None:
        return
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)


def _unlock_handle(fh: Any) -> None:
    if fcntl is None:
        return
    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _read_json_state(path: pathlib.Path) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as fh:
        _lock_handle(fh)
        try:
            fh.seek(0)
            raw = fh.read().strip()
            if not raw:
                return {}
            state = json.loads(raw)
            if not isinstance(state, dict):
                return {}
            return state
        except Exception:
            return {}
        finally:
            _unlock_handle(fh)


def _mutate_json_state(path: pathlib.Path, mutator: Callable[[Dict[str, Any]], Tuple[Dict[str, Any], Any]]) -> Any:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as fh:
        _lock_handle(fh)
        try:
            fh.seek(0)
            raw = fh.read().strip()
            try:
                state = json.loads(raw) if raw else {}
            except Exception:
                state = {}
            if not isinstance(state, dict):
                state = {}

            new_state, result = mutator(state)
            if not isinstance(new_state, dict):
                new_state = {}

            fh.seek(0)
            fh.truncate(0)
            fh.write(json.dumps(new_state, ensure_ascii=True, sort_keys=True))
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass
            return result
        finally:
            _unlock_handle(fh)


def secure_compare(a: Optional[str], b: Optional[str]) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    if a is None or b is None:
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def validate_json_schema(value: Any, schema: Dict[str, Any], path: str = "$") -> None:
    if "anyOf" in schema:
        sub_errors: List[str] = []
        for sub_schema in schema["anyOf"]:
            try:
                validate_json_schema(value, sub_schema, path=path)
                return
            except ValueError as exc:
                sub_errors.append(str(exc))
        raise ValueError(f"{path}: value does not match any allowed schema ({'; '.join(sub_errors)})")

    expected_type = schema.get("type")
    if expected_type and not _matches_type(value, expected_type):
        raise ValueError(f"{path}: expected type {expected_type}")

    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: value {value!r} not in enum {schema['enum']}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ValueError(f"{path}: string shorter than minLength={schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ValueError(f"{path}: string longer than maxLength={schema['maxLength']}")
        if "pattern" in schema and not re.match(schema["pattern"], value):
            raise ValueError(f"{path}: string does not match required pattern")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(f"{path}: number less than minimum={schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValueError(f"{path}: number greater than maximum={schema['maximum']}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ValueError(f"{path}: array shorter than minItems={schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ValueError(f"{path}: array longer than maxItems={schema['maxItems']}")
        items_schema = schema.get("items")
        if items_schema:
            for idx, item in enumerate(value):
                validate_json_schema(item, items_schema, path=f"{path}[{idx}]")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise ValueError(f"{path}: missing required field '{key}'")

        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                validate_json_schema(item, properties[key], path=f"{path}.{key}")
            else:
                additional = schema.get("additionalProperties", True)
                if additional is False:
                    raise ValueError(f"{path}: unexpected field '{key}'")
                if isinstance(additional, dict):
                    validate_json_schema(item, additional, path=f"{path}.{key}")

        if "minProperties" in schema and len(value) < schema["minProperties"]:
            raise ValueError(f"{path}: object has fewer fields than minProperties={schema['minProperties']}")
        if "maxProperties" in schema and len(value) > schema["maxProperties"]:
            raise ValueError(f"{path}: object has more fields than maxProperties={schema['maxProperties']}")


def parse_method_allowlist(raw: Optional[str]) -> List[str]:
    if not raw:
        return list(DEFAULT_METHOD_ALLOWLIST)
    patterns = [pattern.strip().lower() for pattern in raw.split(",") if pattern.strip()]
    return patterns or list(DEFAULT_METHOD_ALLOWLIST)


def parse_pack_list(raw: Optional[str]) -> List[str]:
    if raw is None or not raw.strip():
        return list(DEFAULT_PACKS)
    pack_names = [name.strip().lower() for name in raw.split(",") if name.strip()]
    if pack_names == ["none"]:
        return []

    deduped: List[str] = []
    seen: Set[str] = set()
    for name in pack_names:
        if name not in PACK_METHOD_ALLOWLIST:
            available = ", ".join(sorted(PACK_METHOD_ALLOWLIST.keys()))
            raise ValueError(f"unknown pack '{name}', available packs: {available}")
        if name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return deduped


def expand_allowlist_with_packs(base_patterns: Sequence[str], packs: Sequence[str]) -> List[str]:
    merged: List[str] = []
    seen: Set[str] = set()
    for pattern in list(base_patterns):
        key = pattern.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(key)

    for pack in packs:
        for pattern in PACK_METHOD_ALLOWLIST[pack]:
            key = pattern.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(key)
    return merged


def is_method_allowed(method: str, patterns: Sequence[str]) -> bool:
    method_l = method.lower()
    return any(fnmatch.fnmatchcase(method_l, pattern) for pattern in patterns)


def batch_command_method(command: str) -> str:
    method = command.split("?", 1)[0].strip().lower()
    return method


def classify_method_risk(
    method: str,
    params: Optional[Union[Dict[str, Any], List[Any]]] = None,
    risk_map: Optional[Dict[str, str]] = None,
) -> str:
    method_l = method.lower()
    if method_l == "batch":
        cmd = params.get("cmd", {}) if isinstance(params, dict) else {}
        if isinstance(cmd, dict):
            batch_risks = [classify_method_risk(batch_command_method(v), None) for v in cmd.values() if isinstance(v, str)]
            if "destructive" in batch_risks:
                return "destructive"
            if "write" in batch_risks:
                return "write"
        return "read"

    # The curated catalog Risk column is the source of truth (the name regex misses verbs
    # like defer/pause/setOwner/send). Fall back to the heuristic for uncatalogued methods.
    if risk_map is None:
        risk_map = load_method_risk_map()
    mapped = risk_map.get(method_l)
    if mapped in ("read", "write", "destructive"):
        return mapped

    if DESTRUCTIVE_METHOD_RE.search(method_l):
        return "destructive"
    if WRITE_METHOD_RE.search(method_l):
        return "write"
    return "read"


def validate_method_and_params(method: str, params: Union[Dict[str, Any], List[Any]]) -> None:
    validate_json_schema(method, METHOD_NAME_SCHEMA, path="method")
    if isinstance(params, list):
        # Positional params are only valid for order-sensitive methods. batch and
        # event.offline.get require a named object; reject arrays cleanly here so the
        # downstream batch-allowlist walk never sees a list.
        if method.lower() in ("batch", "event.offline.get"):
            raise ValueError(f"method '{method}' requires a JSON object, not a positional array")
        return
    validate_json_schema(params, GENERIC_PARAMS_SCHEMA, path="params")
    method_l = method.lower()
    if method_l == "batch":
        validate_json_schema(params, BATCH_PARAMS_SCHEMA, path="params")
    elif method_l == "event.offline.get":
        validate_json_schema(params, EVENT_OFFLINE_GET_SCHEMA, path="params")


def missing_required_params(
    method: str,
    params: Union[Dict[str, Any], List[Any]],
    required_map: Dict[str, List[str]],
) -> List[str]:
    """Return required params absent from a named (dict) payload, per the bundled map.

    Returns [] for positional (list) payloads (can't be checked by name) and for methods
    not in the map (the discovered long tail), avoiding false positives.
    """
    if not isinstance(params, dict):
        return []
    required = required_map.get(method) or []
    return [name for name in required if name not in params]


def load_method_risk_map() -> Dict[str, str]:
    """Load the optional, bundled per-method risk map (next to this script).

    Keys are lower-cased method names -> 'read'|'write'|'destructive', derived from the
    catalog Risk column. Missing/unreadable file -> empty (regex heuristic then applies).
    """
    path = pathlib.Path(__file__).resolve().parent / "method_risk.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_required_params_map() -> Dict[str, List[str]]:
    """Load the optional, bundled required-params map (next to this script).

    Missing/unreadable file -> empty map (pre-flight then gracefully no-ops).
    """
    path = pathlib.Path(__file__).resolve().parent / "required_params.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def get_audit_file_path(cli_value: Optional[str]) -> Optional[pathlib.Path]:
    if cli_value is not None:
        raw = cli_value.strip()
    else:
        raw = os.getenv("B24_AUDIT_FILE", ".runtime/bitrix24_audit.jsonl").strip()
    if not raw:
        return None
    return pathlib.Path(raw)


def write_audit_row(audit_file: Optional[pathlib.Path], row: Dict[str, Any]) -> None:
    if audit_file is None:
        return
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=True) + "\n"
    # Hold an exclusive lock around the append so concurrent processes/threads cannot
    # interleave partial JSONL lines (no-op locking on platforms without fcntl).
    with audit_file.open("a", encoding="utf-8") as fh:
        _lock_handle(fh)
        try:
            fh.write(line)
            fh.flush()
        finally:
            _unlock_handle(fh)


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
        """Check if error is retryable (transient) within a single call()."""
        if self.code in FATAL_ERROR_CODES:
            return False
        if self.code in NON_RETRYABLE_LIMIT_CODES:
            # Transient but method-blocked for minutes; surface instead of tight-retrying.
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


class FileRateLimiter:
    """Cross-process file-backed token bucket limiter keyed by tenant domain."""

    def __init__(
        self,
        state_file: pathlib.Path,
        *,
        rate_per_sec: float = 2.0,
        burst: float = 10.0,
        state_ttl_sec: int = 3600,
    ) -> None:
        self.state_file = state_file
        self.rate_per_sec = max(rate_per_sec, 0.1)
        self.burst = max(burst, 1.0)
        self.state_ttl_sec = max(state_ttl_sec, 60)

    def acquire(self, key: str) -> None:
        while True:
            wait_sec = self._reserve(key)
            if wait_sec <= 0:
                return
            time.sleep(wait_sec)

    def _reserve(self, key: str) -> float:
        now = time.time()

        def mutate(state: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
            per_key = state.get(key, {})
            last = float(per_key.get("last", now))
            tokens = float(per_key.get("tokens", self.burst))

            elapsed = max(0.0, now - last)
            tokens = min(self.burst, tokens + elapsed * self.rate_per_sec)

            wait = 0.0
            if tokens >= 1.0:
                tokens -= 1.0
            else:
                wait = (1.0 - tokens) / self.rate_per_sec

            per_key["last"] = now
            per_key["tokens"] = tokens
            state[key] = per_key

            stale_keys = []
            for candidate, candidate_val in state.items():
                if not isinstance(candidate_val, dict):
                    stale_keys.append(candidate)
                    continue
                candidate_last = float(candidate_val.get("last", now))
                if (now - candidate_last) > self.state_ttl_sec:
                    stale_keys.append(candidate)
            for stale in stale_keys:
                state.pop(stale, None)

            return state, wait

        return float(_mutate_json_state(self.state_file, mutate))


class PlanStore:
    def __init__(self, state_file: pathlib.Path, ttl_sec: int = 1800) -> None:
        self.state_file = state_file
        self.ttl_sec = max(ttl_sec, 60)

    def create(
        self,
        *,
        tenant: str,
        method: str,
        params: Dict[str, Any],
        risk: str,
        allowlisted: bool,
        packs: Sequence[str],
    ) -> Dict[str, Any]:
        now = int(time.time())
        params_json = json.dumps(params, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        seed = f"{tenant}|{method}|{risk}|{params_json}|{now}|{uuid.uuid4().hex}"
        plan_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]

        plan = {
            "plan_id": plan_id,
            "tenant": tenant,
            "method": method,
            "params": params,
            "risk": risk,
            "allowlisted": bool(allowlisted),
            "packs": list(packs),
            "created_at": now,
            "expires_at": now + self.ttl_sec,
            "executed": False,
        }

        def mutate(state: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
            plans = state.get("plans")
            if not isinstance(plans, dict):
                plans = {}
            plans = self._cleanup_plans(plans, now)
            plans[plan_id] = plan
            state["plans"] = plans
            return state, plan

        return dict(_mutate_json_state(self.state_file, mutate))

    def consume(self, plan_id: str, *, tenant: str) -> Dict[str, Any]:
        now = int(time.time())

        def mutate(state: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
            plans = state.get("plans")
            if not isinstance(plans, dict):
                plans = {}
            plans = self._cleanup_plans(plans, now)
            plan = plans.get(plan_id)
            if not isinstance(plan, dict):
                raise ValueError(f"plan '{plan_id}' not found or expired")
            if plan.get("tenant") != tenant:
                raise ValueError("plan tenant mismatch")
            if plan.get("executed"):
                raise ValueError(f"plan '{plan_id}' already executed")
            plan["executed"] = True
            plan["executed_at"] = now
            plans[plan_id] = plan
            state["plans"] = plans
            return state, plan

        return dict(_mutate_json_state(self.state_file, mutate))

    @staticmethod
    def _cleanup_plans(plans: Dict[str, Any], now: int) -> Dict[str, Any]:
        cleaned: Dict[str, Any] = {}
        for pid, payload in plans.items():
            if not isinstance(payload, dict):
                continue
            expires_at = int(payload.get("expires_at", 0))
            if expires_at and expires_at < now:
                continue
            cleaned[pid] = payload
        return cleaned


class IdempotencyStore:
    def __init__(self, state_file: pathlib.Path, ttl_sec: int = 86400) -> None:
        self.state_file = state_file
        self.ttl_sec = max(ttl_sec, 60)

    def key_for(
        self,
        *,
        tenant: str,
        method: str,
        params: Union[Dict[str, Any], List[Any]],
        explicit_key: Optional[str] = None,
    ) -> str:
        if explicit_key:
            raw_key = explicit_key.strip()
            if raw_key:
                return f"{tenant}|{method}|{raw_key}"

        if isinstance(params, dict):
            for candidate in (
                "idempotency_key",
                "IDEMPOTENCY_KEY",
                "origin_id",
                "ORIGIN_ID",
                "external_id",
                "EXTERNAL_ID",
            ):
                value = params.get(candidate)
                if isinstance(value, (str, int)):
                    return f"{tenant}|{method}|{candidate}:{value}"

        payload = json.dumps(params, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(f"{tenant}|{method}|{payload}".encode("utf-8")).hexdigest()[:24]
        return f"{tenant}|{method}|auto:{digest}"

    def check_replay(self, key: str) -> Optional[Dict[str, Any]]:
        state = _read_json_state(self.state_file)
        now = int(time.time())
        entries = state.get("entries")
        if not isinstance(entries, dict):
            return None
        payload = entries.get(key)
        if not isinstance(payload, dict):
            return None
        if int(payload.get("expires_at", 0)) < now:
            return None
        if payload.get("status") != "done":
            return None
        response = payload.get("response")
        if isinstance(response, dict):
            return response
        return None

    def start(self, key: str) -> None:
        now = int(time.time())
        expires_at = now + self.ttl_sec

        def mutate(state: Dict[str, Any]) -> Tuple[Dict[str, Any], None]:
            entries = state.get("entries")
            if not isinstance(entries, dict):
                entries = {}
            entries = self._cleanup(entries, now)
            entries[key] = {
                "status": "in_progress",
                "updated_at": now,
                "expires_at": expires_at,
            }
            state["entries"] = entries
            return state, None

        _mutate_json_state(self.state_file, mutate)

    def done(self, key: str, response: Dict[str, Any]) -> None:
        now = int(time.time())
        expires_at = now + self.ttl_sec
        # Mask secrets before persisting the cached response at rest (mirrors the DLQ writer).
        try:
            masked = json.loads(mask_secrets(json.dumps(response, ensure_ascii=True)))
        except (TypeError, ValueError):
            masked = response

        def mutate(state: Dict[str, Any]) -> Tuple[Dict[str, Any], None]:
            entries = state.get("entries")
            if not isinstance(entries, dict):
                entries = {}
            entries = self._cleanup(entries, now)
            entries[key] = {
                "status": "done",
                "updated_at": now,
                "expires_at": expires_at,
                "response": masked,
            }
            state["entries"] = entries
            return state, None

        _mutate_json_state(self.state_file, mutate)

    def clear(self, key: str) -> None:
        now = int(time.time())

        def mutate(state: Dict[str, Any]) -> Tuple[Dict[str, Any], None]:
            entries = state.get("entries")
            if not isinstance(entries, dict):
                entries = {}
            entries = self._cleanup(entries, now)
            entries.pop(key, None)
            state["entries"] = entries
            return state, None

        _mutate_json_state(self.state_file, mutate)

    @staticmethod
    def _cleanup(entries: Dict[str, Any], now: int) -> Dict[str, Any]:
        cleaned: Dict[str, Any] = {}
        for key, payload in entries.items():
            if not isinstance(payload, dict):
                continue
            expires_at = int(payload.get("expires_at", 0))
            if expires_at and expires_at < now:
                continue
            cleaned[key] = payload
        return cleaned


def build_rate_limiter_from_env() -> Any:
    mode = os.getenv("B24_RATE_LIMITER", "file").strip().lower()
    if mode in {"", "off", "none", "noop"}:
        return NoopRateLimiter()
    state_file = pathlib.Path(os.getenv("B24_RATE_LIMITER_FILE", ".runtime/bitrix24_rate_limiter.json"))
    rate = float(os.getenv("B24_RATE_LIMITER_RATE", "2.0"))
    burst = float(os.getenv("B24_RATE_LIMITER_BURST", "10.0"))
    ttl_sec = int(os.getenv("B24_RATE_LIMITER_TTL_SEC", "3600"))
    return FileRateLimiter(state_file, rate_per_sec=rate, burst=burst, state_ttl_sec=ttl_sec)


RefreshCallback = Callable[[TenantConfig, TokenStore], Tuple[str, Optional[str]]]


class Bitrix24Client:
    def __init__(
        self,
        tenant: TenantConfig,
        *,
        token_store: Optional[TokenStore] = None,
        timeout: int = 30,
        max_attempts: int = 5,
        rate_limiter: Optional[Any] = None,
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
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
        *,
        rest_v3: bool = False,
    ) -> Dict[str, Any]:
        # Most methods take a named object (dict). Order-sensitive methods such as
        # task.commentitem.add / task.checklistitem.complete require a positional array
        # (list) per Bitrix24 docs — those must NOT be passed by name.
        if params is None:
            payload: Union[Dict[str, Any], List[Any]] = {}
        elif isinstance(params, dict):
            payload = dict(params)
        elif isinstance(params, list):
            payload = list(params)
        else:
            raise ValueError("params must be a dict (named) or a list (positional)")
        base_url = self._build_url(method=method, rest_v3=rest_v3)

        refreshed = False
        for attempt in range(1, self.max_attempts + 1):
            self.rate_limiter.acquire(self.tenant.domain)
            url = base_url
            if self.tenant.auth_mode == "oauth":
                access_token, _ = self.token_store.get_tokens()
                if isinstance(payload, dict):
                    payload["auth"] = access_token
                elif access_token:
                    # Positional payloads cannot carry an 'auth' field; pass it in the query.
                    url = self._with_auth_query(base_url, access_token)

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
        """Thread-safe token refresh using a singleflight pattern.

        The winner performs the refresh. Losers wait for the winner to finish and
        then verify the access token actually changed: if the winner's refresh failed
        (token unchanged), losers must NOT assume success, otherwise every waiting
        thread would retry with a stale token and the real error would be swallowed.
        """
        old_access, _ = self.token_store.get_tokens()
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
            # Another thread is refreshing; wait for it, then confirm it succeeded.
            with self._refresh_lock:
                pass
            new_access, _ = self.token_store.get_tokens()
            return new_access is not None and new_access != old_access

    def iter_list(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        rest_v3: bool = False,
    ) -> Iterator[Dict[str, Any]]:
        """Iterate over all items from a paginated *.list method.

        Yields individual items, advancing the ``start`` offset by following the
        ``next`` cursor in each response until it is absent. Bitrix24 list methods
        page in fixed blocks of 50; there is no client-tunable page size.
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
                items = result.get("items")
                if isinstance(items, list):
                    # Universal methods (crm.item.*) nest rows under result.items.
                    for item in items:
                        yield item
                else:
                    # Legacy dict-of-records result.
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
        scheme = domain.lower()
        if scheme.startswith("http://"):
            # Refuse plaintext: webhook codes and OAuth tokens must never travel over HTTP.
            raise ValueError("Bitrix24 domain must use https:// (plaintext http:// is not allowed)")
        if not scheme.startswith("https://"):
            domain = f"https://{domain}"

        if self.tenant.auth_mode == "webhook":
            if not self.tenant.webhook_user_id or not self.tenant.webhook_code:
                raise ValueError("webhook_user_id and webhook_code are required for webhook mode")
            # REST v3 webhooks use the /rest/api/ prefix; v2 uses /rest/.
            prefix = "rest/api" if rest_v3 else "rest"
            return (
                f"{domain}/{prefix}/"
                f"{self.tenant.webhook_user_id}/{self.tenant.webhook_code}/{method}"
            )

        # OAuth mode
        if rest_v3:
            return f"{domain}/rest/api/{method}"
        return f"{domain}/rest/{method}"

    @staticmethod
    def _with_auth_query(url: str, token: str) -> str:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}auth={urllib.parse.quote(token, safe='')}"

    def _post_json(self, url: str, payload: Union[Dict[str, Any], List[Any]]) -> Dict[str, Any]:
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
    parser.add_argument("method", nargs="?", help="Bitrix24 method, e.g. crm.lead.list")
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
    parser.add_argument(
        "--out",
        choices=["full", "compact", "summary"],
        default="full",
        help="Output shape (default full). compact=minified JSON; summary=list digest. Saves agent tokens.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=0,
        help="Truncate result rows to N (0=no limit); adds a _truncated marker.",
    )
    parser.add_argument(
        "--method-allowlist",
        default=os.getenv("B24_METHOD_ALLOWLIST", ""),
        help="Comma-separated method allowlist patterns, e.g. 'user.*,crm.*,batch'",
    )
    parser.add_argument(
        "--packs",
        default=os.getenv("B24_PACKS", ",".join(DEFAULT_PACKS)),
        help=(
            "Comma-separated capability packs: "
            "core,comms,automation,collab,content,boards,commerce,services,platform,sites,compliance,diagnostics. "
            "Use 'none' to disable packs."
        ),
    )
    parser.add_argument(
        "--list-packs",
        action="store_true",
        help="Print available packs and exit.",
    )
    parser.add_argument(
        "--allow-unlisted",
        action="store_true",
        help="Allow methods outside allowlist for this call",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Locally check required params before calling (uses bundled required_params.json)",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Create and persist execution plan, print plan payload, do not execute API call",
    )
    parser.add_argument(
        "--execute-plan",
        default="",
        help="Execute previously created plan id from plan store",
    )
    parser.add_argument(
        "--plan-file",
        default=os.getenv("B24_PLAN_FILE", ".runtime/bitrix24_plans.json"),
        help="Path to persisted plan store JSON (default: B24_PLAN_FILE or .runtime/bitrix24_plans.json)",
    )
    parser.add_argument(
        "--plan-ttl-sec",
        type=int,
        default=int(os.getenv("B24_PLAN_TTL_SEC", "1800")),
        help="Plan expiration time in seconds (default: B24_PLAN_TTL_SEC or 1800)",
    )
    parser.add_argument(
        "--require-plan",
        action="store_true",
        default=parse_bool_env("B24_REQUIRE_PLAN", default=False),
        help="Require plan->execute for write/destructive operations (default from B24_REQUIRE_PLAN)",
    )
    parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Required for write methods and write batch commands",
    )
    parser.add_argument(
        "--confirm-destructive",
        action="store_true",
        help="Required for destructive methods (delete/remove/unbind/unregister)",
    )
    parser.add_argument(
        "--audit-file",
        default=None,
        help="Path to JSONL audit file (default: B24_AUDIT_FILE or .runtime/bitrix24_audit.jsonl)",
    )
    parser.add_argument(
        "--no-audit",
        action="store_true",
        help="Disable audit logging for this call",
    )
    parser.add_argument(
        "--idempotency-key",
        default="",
        help="Explicit idempotency key for write/destructive operations",
    )
    parser.add_argument(
        "--idempotency-file",
        default=os.getenv("B24_IDEMPOTENCY_FILE", ".runtime/bitrix24_idempotency.json"),
        help="Path to idempotency store JSON (default: B24_IDEMPOTENCY_FILE or .runtime/bitrix24_idempotency.json)",
    )
    parser.add_argument(
        "--idempotency-ttl-sec",
        type=int,
        default=int(os.getenv("B24_IDEMPOTENCY_TTL_SEC", "86400")),
        help="TTL for idempotency records in seconds (default: B24_IDEMPOTENCY_TTL_SEC or 86400)",
    )
    parser.add_argument(
        "--no-idempotency",
        action="store_true",
        help="Disable idempotency layer for write/destructive operations",
    )
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in --params: {e}", file=sys.stderr)
        raise SystemExit(1)

    if not isinstance(params, (dict, list)):
        print("Error: --params must decode to a JSON object or array", file=sys.stderr)
        raise SystemExit(1)

    tenant, token_store = load_tenant_config_from_env()
    # Preserve method-name case: v2/v3 namespaces are case-sensitive (e.g. imbot.v2.Bot.list).
    # Allowlist/risk/validation lower-case internally, so matching is unaffected.
    method = (args.method or "").strip()

    if args.execute_plan:
        plan_store = PlanStore(pathlib.Path(args.plan_file), ttl_sec=args.plan_ttl_sec)
        try:
            plan = plan_store.consume(args.execute_plan.strip(), tenant=tenant.domain)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            raise SystemExit(2)

        planned_method = str(plan.get("method", "")).strip()
        planned_params = plan.get("params", {})
        if not isinstance(planned_params, (dict, list)):
            print("Error: stored plan payload is invalid", file=sys.stderr)
            raise SystemExit(2)
        if method and method.lower() != planned_method.lower():
            print(
                f"Error: CLI method '{method}' does not match planned method '{planned_method}'",
                file=sys.stderr,
            )
            raise SystemExit(2)
        method = planned_method
        params = planned_params

    if args.list_packs and not method:
        # list-packs can work without method
        pass
    elif not method:
        print("Error: method is required (or use --execute-plan)", file=sys.stderr)
        raise SystemExit(2)

    try:
        if method:
            validate_method_and_params(method, params)
    except ValueError as exc:
        print(f"Error: Schema validation failed: {exc}", file=sys.stderr)
        raise SystemExit(2)

    allowlist_patterns = parse_method_allowlist(args.method_allowlist)
    try:
        selected_packs = parse_pack_list(args.packs)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2)

    if args.list_packs:
        print(
            json.dumps(
                {
                    "default_packs": list(DEFAULT_PACKS),
                    "available_packs": PACK_METHOD_ALLOWLIST,
                    "selected_packs": selected_packs,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(0)

    allowlist_patterns = expand_allowlist_with_packs(allowlist_patterns, selected_packs)
    method_allowed = is_method_allowed(method, allowlist_patterns)
    if not method_allowed and not args.allow_unlisted:
        print(
            f"Error: method '{method}' is outside allowlist. "
            "Use --allow-unlisted to bypass or extend --method-allowlist/--packs.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    if method.lower() == "batch":
        batch_cmd = params.get("cmd", {})
        if isinstance(batch_cmd, dict):
            for name, command in batch_cmd.items():
                if not isinstance(command, str):
                    continue
                command_method = batch_command_method(command)
                if not is_method_allowed(command_method, allowlist_patterns) and not args.allow_unlisted:
                    print(
                        f"Error: batch command '{name}' uses non-allowlisted method '{command_method}'. "
                        "Use --allow-unlisted to bypass.",
                        file=sys.stderr,
                    )
                    raise SystemExit(2)

    method_risk = classify_method_risk(method, params=params)

    if args.preflight:
        missing = missing_required_params(method, params, load_required_params_map())
        if missing:
            print(
                f"Error: method '{method}' is missing required params: {', '.join(missing)}. "
                "Add them, or omit --preflight to bypass.",
                file=sys.stderr,
            )
            raise SystemExit(2)

    if args.plan_only:
        plan_store = PlanStore(pathlib.Path(args.plan_file), ttl_sec=args.plan_ttl_sec)
        plan = plan_store.create(
            tenant=tenant.domain,
            method=method,
            params=params,
            risk=method_risk,
            allowlisted=method_allowed,
            packs=selected_packs,
        )
        plan_result = {
            "plan": plan,
            "next": {
                "execute_command": f"python3 skills/bitrix24-agent/scripts/bitrix24_client.py --execute-plan {plan['plan_id']}"
            },
        }
        print(json.dumps(plan_result, ensure_ascii=False, indent=2))
        raise SystemExit(0)

    if args.require_plan and method_risk in {"write", "destructive"} and not args.execute_plan:
        print(
            "Error: plan is required for write/destructive operation. "
            "Run with --plan-only, then execute with --execute-plan <plan_id>.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    if method_risk == "write" and not args.confirm_write:
        print(
            "Error: write method detected. Add --confirm-write to execute.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if method_risk == "destructive" and not args.confirm_destructive:
        print(
            "Error: destructive method detected. Add --confirm-destructive to execute.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    refresh_callback = refresh_via_oauth_server if args.auto_refresh else None
    client = Bitrix24Client(
        tenant,
        token_store=token_store,
        refresh_callback=refresh_callback,
        rate_limiter=build_rate_limiter_from_env(),
    )
    request_id = uuid.uuid4().hex[:12]
    started = time.time()
    # Audit records only parameter shape, never values. Positional (list) payloads have no keys.
    param_keys = sorted(params.keys()) if isinstance(params, dict) else []
    audit_file = None if args.no_audit else get_audit_file_path(args.audit_file)
    idempotency_enabled = method_risk in {"write", "destructive"} and not args.no_idempotency
    idempotency_store = None
    idempotency_key = ""
    replayed = False

    if idempotency_enabled:
        idempotency_store = IdempotencyStore(
            pathlib.Path(args.idempotency_file),
            ttl_sec=args.idempotency_ttl_sec,
        )
        idempotency_key = idempotency_store.key_for(
            tenant=tenant.domain,
            method=method,
            params=params,
            explicit_key=args.idempotency_key,
        )
        cached = idempotency_store.check_replay(idempotency_key)
        if isinstance(cached, dict):
            replayed = True
            write_audit_row(
                audit_file,
                {
                    "ts": int(time.time()),
                    "request_id": request_id,
                    "tenant": tenant.domain,
                    "method": method,
                    "risk": method_risk,
                    "status": "idempotent_replay",
                    "duration_ms": int((time.time() - started) * 1000),
                    "allowlisted": method_allowed,
                    "packs": selected_packs,
                    "rest_v3": args.rest_v3,
                    "param_keys": param_keys,
                    "plan_id": args.execute_plan or "",
                    "idempotency_key": idempotency_key,
                },
            )
            output = shape_output(cached, mode=args.out, max_items=args.max_items)
            if args.mask_secrets:
                output = mask_secrets(output)
            print(output)
            raise SystemExit(0)
        idempotency_store.start(idempotency_key)

    try:
        response = client.call(method, params=params, rest_v3=args.rest_v3)
    except BitrixAPIError as exc:
        if idempotency_store and idempotency_key:
            idempotency_store.clear(idempotency_key)
        write_audit_row(
            audit_file,
            {
                "ts": int(time.time()),
                "request_id": request_id,
                "tenant": tenant.domain,
                "method": method,
                "risk": method_risk,
                "status": "error",
                "error_code": exc.code,
                "error_message": str(exc),
                "duration_ms": int((time.time() - started) * 1000),
                "allowlisted": method_allowed,
                "packs": selected_packs,
                "rest_v3": args.rest_v3,
                "param_keys": param_keys,
                "plan_id": args.execute_plan or "",
                "idempotency_key": idempotency_key,
                "idempotent_replay": replayed,
            },
        )
        print(f"Bitrix API error: code={exc.code} status={exc.status} msg={exc}", file=sys.stderr)
        raise SystemExit(1)

    if idempotency_store and idempotency_key:
        idempotency_store.done(idempotency_key, response)

    write_audit_row(
        audit_file,
        {
            "ts": int(time.time()),
            "request_id": request_id,
            "tenant": tenant.domain,
            "method": method,
            "risk": method_risk,
            "status": "ok",
            "duration_ms": int((time.time() - started) * 1000),
            "allowlisted": method_allowed,
            "packs": selected_packs,
            "rest_v3": args.rest_v3,
            "param_keys": param_keys,
            "plan_id": args.execute_plan or "",
            "idempotency_key": idempotency_key,
            "idempotent_replay": replayed,
        },
    )

    output = shape_output(response, mode=args.out, max_items=args.max_items)
    if args.mask_secrets:
        output = mask_secrets(output)
    print(output)


if __name__ == "__main__":
    main()
