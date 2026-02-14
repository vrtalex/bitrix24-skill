#!/usr/bin/env python3
"""Offline event worker baseline for Bitrix24.

This worker:
- pulls offline events via event.offline.get(clear=0),
- retries failed records with bounded budget,
- sends exhausted records to DLQ jsonl,
- clears only successfully processed (or DLQ'ed) records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = pathlib.Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from bitrix24_client import Bitrix24Client, BitrixAPIError, load_tenant_config_from_env


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
            self._state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            self._state = {}

    def save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self._state, ensure_ascii=True, indent=2), encoding="utf-8")

    def fail(self, key: str) -> int:
        count = self._state.get(key, 0) + 1
        self._state[key] = count
        return count

    def clear(self, key: str) -> None:
        if key in self._state:
            del self._state[key]

    def exhausted(self, key: str) -> bool:
        return self._state.get(key, 0) >= self.max_retries


def write_dlq(dlq_path: pathlib.Path, *, tenant: str, event_item: Dict[str, Any], error: str, retries: int) -> None:
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
    with dlq_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=True) + "\n")


def process_event_default(event_item: Dict[str, Any]) -> None:
    """Replace this with domain-specific processing."""
    _ = event_item
    return


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


def run_once(
    client: Bitrix24Client,
    *,
    tenant_key: str,
    retry_budget: RetryBudget,
    dlq_path: pathlib.Path,
) -> int:
    response = client.call("event.offline.get", params={"clear": 0})
    process_id, events = parse_offline_get(response)
    if not process_id or not events:
        return 0

    clear_ids: List[str] = []
    has_pending_failures = False
    for event_item in events:
        dedup = event_dedup_key(event_item)
        msg_id = event_message_id(event_item)
        try:
            process_event_default(event_item)
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
            else:
                has_pending_failures = True

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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    tenant = load_tenant_config_from_env()
    tenant_key = tenant.domain
    client = Bitrix24Client(tenant)
    retry_budget = RetryBudget(pathlib.Path(args.state_file), max_retries=args.max_retries)
    dlq_path = pathlib.Path(args.dlq_file)

    while True:
        try:
            count = run_once(
                client,
                tenant_key=tenant_key,
                retry_budget=retry_budget,
                dlq_path=dlq_path,
            )
            if args.once:
                print(f"Processed batch size: {count}")
                return
            if count == 0:
                time.sleep(args.sleep)
        except BitrixAPIError as exc:
            print(f"Bitrix API error: code={exc.code} status={exc.status} msg={exc}")
            if args.once:
                return
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
