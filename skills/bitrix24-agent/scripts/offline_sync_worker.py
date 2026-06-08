#!/usr/bin/env python3
"""Offline event worker baseline for Bitrix24.

Requires OAuth application auth (B24_AUTH_MODE=oauth): event.offline.* are denied for
incoming webhooks (the portal returns WRONG_AUTH_TYPE / HTTP 403). Bind the offline
handler with event.bind using event_type=offline (no handler URL).

This worker:
- pulls offline events via event.offline.get(clear=0),
- retries failed records with bounded budget,
- sends exhausted records to DLQ jsonl with file locking,
- clears only successfully processed (or DLQ'ed) records,
- supports graceful shutdown via SIGTERM/SIGINT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import signal
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows has no fcntl; locking degrades to no-op
    fcntl = None  # type: ignore[assignment]

THIS_DIR = pathlib.Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from bitrix24_client import (  # noqa: E402  (import follows sys.path bootstrap above)
    Bitrix24Client,
    BitrixAPIError,
    build_rate_limiter_from_env,
    load_tenant_config_from_env,
    mask_secrets,
    refresh_via_oauth_server,
    secure_compare,
)


class GracefulShutdown:
    """Handle graceful shutdown on SIGTERM/SIGINT."""

    def __init__(self) -> None:
        self._shutdown_requested = False
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum: int, frame: Any) -> None:
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self._shutdown_requested = True

    @property
    def should_stop(self) -> bool:
        return self._shutdown_requested


def parse_offline_get(response: Dict[str, Any]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    result = response.get("result", {})
    process_id = result.get("process_id")

    candidates = (
        result.get("events"),
        result.get("items"),
        result.get("result"),
    )
    events: List[Dict[str, Any]] = []
    for candidate in candidates:
        if isinstance(candidate, list):
            events = [item for item in candidate if isinstance(item, dict)]
            break
        if isinstance(candidate, dict):
            events = [value for value in candidate.values() if isinstance(value, dict)]
            break

    return process_id, events


def validate_offline_get_response_schema(response: Dict[str, Any]) -> Optional[str]:
    if not isinstance(response, dict):
        return "response is not an object"
    result = response.get("result")
    if result is None:
        return "missing result field"
    if not isinstance(result, dict):
        return "result is not an object"
    process_id = result.get("process_id")
    if process_id is not None and not isinstance(process_id, str):
        return "result.process_id must be string when present"
    return None


def event_message_id(event_item: Dict[str, Any]) -> Optional[str]:
    for key in ("message_id", "MESSAGE_ID", "id", "ID"):
        value = event_item.get(key)
        if value is not None:
            return str(value)
    return None


def event_dedup_key(event_item: Dict[str, Any]) -> str:
    event_name = str(event_item.get("event") or event_item.get("EVENT") or "unknown")
    payload = event_item.get("data") or event_item.get("DATA") or {}
    stable = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    digest = hashlib.sha256(stable.encode("utf-8")).hexdigest()[:16]
    return f"{event_name}:{digest}"


def validate_event_item_schema(event_item: Dict[str, Any]) -> Optional[str]:
    if not isinstance(event_item, dict):
        return "event item is not an object"
    event_name = event_item.get("event") or event_item.get("EVENT")
    if event_name is not None and not isinstance(event_name, str):
        return "event field must be a string"
    data = event_item.get("data") or event_item.get("DATA")
    if data is not None and not isinstance(data, dict):
        return "data field must be an object"
    auth = event_item.get("auth") or event_item.get("AUTH")
    if auth is not None and not isinstance(auth, dict):
        return "auth field must be an object"
    return None


def validate_application_token(
    event_auth: Dict[str, Any],
    expected_token: Optional[str],
) -> bool:
    """Validate application_token from event using constant-time comparison."""
    if expected_token is None:
        return True  # No validation configured
    received_token = event_auth.get("application_token")
    return secure_compare(received_token, expected_token)


class RetryBudget:
    def __init__(self, state_file: pathlib.Path, max_retries: int) -> None:
        self.state_file = state_file
        self.max_retries = max_retries
        self._state: Dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        if not self.state_file.exists():
            self._state = {}
            return
        try:
            loaded = json.loads(self.state_file.read_text(encoding="utf-8"))
            self._state = loaded if isinstance(loaded, dict) else {}
        except Exception as exc:  # noqa: BLE001
            # A corrupt/partial state file would otherwise silently wipe all retry counts,
            # defeating the DLQ-after-N-failures guarantee. Surface it loudly.
            print(
                f"WARNING: could not read retry state {self.state_file} ({exc}); "
                "starting with empty retry counts",
                file=sys.stderr,
            )
            self._state = {}

    def save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        # Use atomic write with temp file
        temp_file = self.state_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(self._state, ensure_ascii=True, indent=2), encoding="utf-8")
        temp_file.rename(self.state_file)

    def fail(self, key: str) -> int:
        count = self._state.get(key, 0) + 1
        self._state[key] = count
        return count

    def clear(self, key: str) -> None:
        if key in self._state:
            del self._state[key]

    def exhausted(self, key: str) -> bool:
        return self._state.get(key, 0) >= self.max_retries

    def has_pending(self) -> bool:
        """True if any event is mid-retry (kept un-acknowledged for redelivery)."""
        return bool(self._state)


def tenant_lock_path(lock_file: str, tenant_key: str) -> pathlib.Path:
    """Derive a per-tenant lock file path so different portals never block each other."""
    base = pathlib.Path(lock_file)
    safe_tenant = tenant_key.replace("/", "_").replace(":", "_")
    return base.with_name(f"{base.stem}_{safe_tenant}{base.suffix}")


def acquire_single_instance_lock(lock_path: pathlib.Path) -> Any:
    """Acquire an advisory single-instance lock for the worker.

    Two workers polling the same tenant would fight over offline batches and clobber
    shared retry/DLQ state. Holding an exclusive, non-blocking flock prevents that.
    Returns the open file handle (keep it alive for the worker's lifetime). Raises
    RuntimeError if another instance already holds the lock. Locking is skipped on
    platforms without fcntl.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("w", encoding="utf-8")
    if fcntl is not None:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise RuntimeError(
                f"another worker instance already holds {lock_path}; "
                "run one worker per tenant"
            )
    return handle


def write_dlq(
    dlq_path: pathlib.Path,
    *,
    tenant: str,
    event_item: Dict[str, Any],
    error: str,
    retries: int,
) -> None:
    """Write to DLQ with file locking to prevent corruption from concurrent writes."""
    dlq_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "tenant": tenant,
        "event": event_item.get("event") or event_item.get("EVENT"),
        "message_id": event_message_id(event_item),
        "retry_count": retries,
        "error": error,
        "payload": event_item,
        "ts": int(time.time()),
    }
    # Mask secrets (e.g. auth.application_token) before persisting the full payload at rest.
    row_json = mask_secrets(json.dumps(row, ensure_ascii=True)) + "\n"

    # Open with append mode and use an exclusive lock for the write (no-op without fcntl).
    with dlq_path.open("a", encoding="utf-8") as fh:
        if fcntl is not None:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.write(row_json)
            fh.flush()
        finally:
            if fcntl is not None:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def process_event_default(event_item: Dict[str, Any]) -> None:
    """Default fallback handler: no-op (log-and-ack). Replace or register per-event handlers."""
    _ = event_item
    return


# Per-event-name handler registry. Keys are upper-cased event names (e.g. "ONCRMDEALADD").
# Register a handler to process a specific event; unregistered events use process_event_default.
#   from offline_sync_worker import register_handler
#   def on_deal_add(event_item): ...   # event_item["data"] holds the payload
#   register_handler("ONCRMDEALADD", on_deal_add)
EVENT_HANDLERS: Dict[str, Any] = {}


def register_handler(event_name: str, handler: Any) -> None:
    """Register a callable(event_item) for a specific Bitrix24 event name (case-insensitive)."""
    EVENT_HANDLERS[event_name.upper()] = handler


def dispatch_event(event_item: Dict[str, Any]) -> None:
    """Route an event to its registered handler, falling back to process_event_default."""
    name = str(event_item.get("event") or event_item.get("EVENT") or "").upper()
    EVENT_HANDLERS.get(name, process_event_default)(event_item)


def redrive_dlq(dlq_path: pathlib.Path) -> Tuple[int, int]:
    """Re-process dead-lettered events through the handler registry.

    Each DLQ row's payload is dispatched again; rows that succeed are removed, rows that
    still fail are kept. Returns (reprocessed, remaining). File-locked like write_dlq.
    """
    if not dlq_path.exists():
        return (0, 0)
    reprocessed = 0
    remaining: List[str] = []
    with dlq_path.open("r+", encoding="utf-8") as fh:
        if fcntl is not None:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            for line in fh.read().splitlines():
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line).get("payload") or {}
                    dispatch_event(payload)
                    reprocessed += 1
                except Exception:  # noqa: BLE001 - keep anything that fails to reprocess
                    remaining.append(line)
            fh.seek(0)
            fh.truncate(0)
            if remaining:
                fh.write("\n".join(remaining) + "\n")
            fh.flush()
        finally:
            if fcntl is not None:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    return (reprocessed, len(remaining))


def bootstrap_offline(client: Bitrix24Client, event_name: str) -> Dict[str, Any]:
    """Register an offline handler for event_name (event.bind, event_type=offline).

    Requires OAuth application auth (see module docstring). After binding, the worker
    drains the queue with event.offline.get(clear=0).
    """
    return client.call("event.bind", params={"event": event_name, "event_type": "offline"})


def clear_processed(
    client: Bitrix24Client,
    *,
    process_id: str,
    message_ids: List[str],
) -> None:
    params: Dict[str, Any] = {"process_id": process_id}
    if message_ids:
        params["message_id"] = message_ids
    client.call("event.offline.clear", params=params)


def report_offline_error(
    client: Bitrix24Client,
    *,
    process_id: str,
    message_ids: List[str],
) -> None:
    if not message_ids:
        return
    try:
        client.call(
            "event.offline.error",
            params={
                "process_id": process_id,
                "message_id": message_ids,
            },
        )
    except BitrixAPIError as exc:
        print(f"Warning: failed to report event.offline.error ({exc.code}): {exc}")


def run_once(
    client: Bitrix24Client,
    *,
    tenant_key: str,
    retry_budget: RetryBudget,
    dlq_path: pathlib.Path,
    application_token: Optional[str] = None,
) -> int:
    response = client.call("event.offline.get", params={"clear": "0"})
    response_error = validate_offline_get_response_schema(response)
    if response_error:
        raise BitrixAPIError(
            f"Invalid offline response schema: {response_error}",
            code="INVALID_OFFLINE_RESPONSE_SCHEMA",
            payload={"raw": response},
        )
    process_id, events = parse_offline_get(response)
    if not process_id or not events:
        return 0

    clear_ids: List[str] = []
    error_ids: List[str] = []
    has_pending_failures = False
    for event_item in events:
        event_schema_error = validate_event_item_schema(event_item)
        if event_schema_error:
            msg_id = event_message_id(event_item)
            write_dlq(
                dlq_path,
                tenant=tenant_key,
                event_item=event_item,
                error=f"INVALID_EVENT_SCHEMA: {event_schema_error}",
                retries=0,
            )
            if msg_id:
                clear_ids.append(msg_id)
                error_ids.append(msg_id)
            else:
                has_pending_failures = True
            continue

        # Validate application_token if configured
        event_auth = event_item.get("auth") or {}
        if not validate_application_token(event_auth, application_token):
            # Log security event and skip (don't clear - might be injection attempt)
            print(f"SECURITY: Invalid application_token for event {event_message_id(event_item)}")
            has_pending_failures = True
            continue

        dedup = event_dedup_key(event_item)
        msg_id = event_message_id(event_item)
        try:
            dispatch_event(event_item)
            retry_budget.clear(dedup)
            if msg_id:
                clear_ids.append(msg_id)
        except Exception as exc:  # noqa: BLE001
            retries = retry_budget.fail(dedup)
            if retry_budget.exhausted(dedup):
                write_dlq(
                    dlq_path,
                    tenant=tenant_key,
                    event_item=event_item,
                    error=str(exc),
                    retries=retries,
                )
                retry_budget.clear(dedup)
                if msg_id:
                    clear_ids.append(msg_id)
                    error_ids.append(msg_id)
            else:
                has_pending_failures = True

    if error_ids:
        report_offline_error(client, process_id=process_id, message_ids=error_ids)

    # If there are no pending failures, clear whole process_id even when message IDs are absent.
    # If there are pending failures, clear only explicitly successful/DLQ'ed message IDs.
    if (not has_pending_failures) or clear_ids:
        clear_processed(client, process_id=process_id, message_ids=clear_ids)
    retry_budget.save()
    return len(events)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bitrix24 offline events worker")
    parser.add_argument("--sleep", type=float, default=3.0, help="Sleep seconds between polling cycles")
    parser.add_argument("--once", action="store_true", help="Run one polling iteration and exit")
    parser.add_argument("--max-retries", type=int, default=5, help="Retry budget per dedup event key")
    parser.add_argument(
        "--state-file",
        default=".runtime/offline_retry_state.json",
        help="Path to retry state JSON",
    )
    parser.add_argument(
        "--dlq-file",
        default=".runtime/offline_dlq.jsonl",
        help="Path to DLQ jsonl output",
    )
    parser.add_argument(
        "--application-token",
        default=None,
        help="Expected application_token for event validation (optional)",
    )
    parser.add_argument(
        "--auto-refresh",
        action="store_true",
        help="Enable OAuth token refresh via oauth.bitrix24.tech (OAuth mode only)",
    )
    parser.add_argument(
        "--lock-file",
        default=".runtime/offline_worker.lock",
        help="Single-instance advisory lock file (per tenant). Set empty to disable.",
    )
    parser.add_argument(
        "--redrive",
        action="store_true",
        help="Re-process the DLQ through registered handlers, then exit (no portal needed).",
    )
    parser.add_argument(
        "--bind-offline",
        default="",
        metavar="EVENT",
        help="Register an offline handler (event.bind event_type=offline) for EVENT, then exit (OAuth).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # DLQ re-drive is a one-shot that needs no portal/tenant — handle it first.
    if args.redrive:
        reprocessed, remaining = redrive_dlq(pathlib.Path(args.dlq_file))
        print(f"DLQ re-drive: reprocessed={reprocessed}, remaining={remaining}")
        return

    # Setup graceful shutdown handler
    shutdown = GracefulShutdown()

    tenant, token_store = load_tenant_config_from_env()
    tenant_key = tenant.domain

    # Prevent two workers from racing over the same tenant's offline batches and state.
    # The lock is always scoped per tenant so different portals can run concurrently.
    lock_handle = None
    if args.lock_file:
        lock_path = tenant_lock_path(args.lock_file, tenant_key)
        try:
            lock_handle = acquire_single_instance_lock(lock_path)
        except RuntimeError as exc:
            print(f"FATAL: {exc}", file=sys.stderr)
            sys.exit(1)

    # Share the per-portal rate limiter and (optionally) OAuth refresh with the client so the
    # polling loop is throttled and can recover expired tokens like the CLI does.
    refresh_callback = refresh_via_oauth_server if args.auto_refresh else None
    client = Bitrix24Client(
        tenant,
        token_store=token_store,
        rate_limiter=build_rate_limiter_from_env(),
        refresh_callback=refresh_callback,
    )
    if args.bind_offline:
        print(bootstrap_offline(client, args.bind_offline))
        if lock_handle is not None:
            lock_handle.close()
        return

    retry_budget = RetryBudget(pathlib.Path(args.state_file), max_retries=args.max_retries)
    dlq_path = pathlib.Path(args.dlq_file)

    consecutive_errors = 0
    max_consecutive_errors = 10

    while not shutdown.should_stop:
        try:
            count = run_once(
                client,
                tenant_key=tenant_key,
                retry_budget=retry_budget,
                dlq_path=dlq_path,
                application_token=args.application_token,
            )
            consecutive_errors = 0  # Reset on success

            if args.once:
                print(f"Processed batch size: {count}")
                return
            # Sleep when idle OR when events were left un-acknowledged for retry, so a
            # persistently failing event cannot drive a tight, server-hammering poll loop.
            if count == 0 or retry_budget.has_pending():
                time.sleep(args.sleep)
        except BitrixAPIError as exc:
            consecutive_errors += 1
            print(f"Bitrix API error: code={exc.code} status={exc.status} msg={exc}")

            # Circuit breaker for fatal errors
            if exc.fatal:
                print(f"FATAL: Error code {exc.code} is not recoverable. Exiting.")
                sys.exit(1)

            if args.once:
                return

            # Circuit breaker for too many consecutive errors
            if consecutive_errors >= max_consecutive_errors:
                print(f"FATAL: {consecutive_errors} consecutive errors. Exiting to prevent infinite loop.")
                sys.exit(1)

            time.sleep(args.sleep)
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            break

    print("Worker stopped gracefully")
    if lock_handle is not None:
        lock_handle.close()


if __name__ == "__main__":
    main()
