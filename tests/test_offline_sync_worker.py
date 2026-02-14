import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "skills" / "bitrix24-agent" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import offline_sync_worker as worker  # noqa: E402
from bitrix24_client import BitrixAPIError  # noqa: E402


class FakeClient:
    def __init__(self, offline_response):
        self.offline_response = offline_response
        self.calls = []

    def call(self, method, params=None, **kwargs):
        self.calls.append((method, params, kwargs))
        if method == "event.offline.get":
            return self.offline_response
        if method == "event.offline.clear":
            return {"result": True}
        if method == "event.offline.error":
            return {"result": True}
        raise AssertionError(f"Unexpected method: {method}")


class OfflineWorkerTests(unittest.TestCase):
    def test_parse_offline_get_from_events_list(self):
        response = {"result": {"process_id": "p1", "events": [{"ID": 1}, {"ID": 2}]}}
        process_id, events = worker.parse_offline_get(response)
        self.assertEqual(process_id, "p1")
        self.assertEqual(len(events), 2)

    def test_validate_offline_get_response_schema(self):
        self.assertEqual(worker.validate_offline_get_response_schema({"result": {"process_id": "x"}}), None)
        self.assertEqual(worker.validate_offline_get_response_schema({"result": 1}), "result is not an object")
        self.assertEqual(worker.validate_offline_get_response_schema({"result": {"process_id": 3}}), "result.process_id must be string when present")

    def test_validate_event_item_schema(self):
        self.assertIsNone(worker.validate_event_item_schema({"event": "ONCRMDEALADD", "data": {"FIELDS": {}}}))
        self.assertEqual(worker.validate_event_item_schema({"event": 10}), "event field must be a string")
        self.assertEqual(worker.validate_event_item_schema({"event": "X", "data": [1]}), "data field must be an object")
        self.assertEqual(worker.validate_event_item_schema({"event": "X", "auth": [1]}), "auth field must be an object")

    def test_event_message_id(self):
        self.assertEqual(worker.event_message_id({"message_id": 10}), "10")
        self.assertEqual(worker.event_message_id({"ID": "22"}), "22")
        self.assertIsNone(worker.event_message_id({"event": "X"}))

    def test_run_once_happy_path(self):
        response = {
            "result": {
                "process_id": "p1",
                "events": [
                    {"message_id": "1", "event": "E1", "data": {}},
                    {"message_id": "2", "event": "E2", "data": {}},
                ],
            }
        }
        client = FakeClient(response)
        with tempfile.TemporaryDirectory() as tmp:
            state = pathlib.Path(tmp) / "state.json"
            dlq = pathlib.Path(tmp) / "dlq.jsonl"
            retry_budget = worker.RetryBudget(state, max_retries=2)
            count = worker.run_once(client, tenant_key="t1", retry_budget=retry_budget, dlq_path=dlq)

        self.assertEqual(count, 2)
        clear_calls = [c for c in client.calls if c[0] == "event.offline.clear"]
        self.assertEqual(len(clear_calls), 1)
        self.assertEqual(clear_calls[0][1]["message_id"], ["1", "2"])

    def test_run_once_invalid_offline_schema_raises(self):
        client = FakeClient({"result": 1})
        with tempfile.TemporaryDirectory() as tmp:
            retry_budget = worker.RetryBudget(pathlib.Path(tmp) / "state.json", max_retries=2)
            with self.assertRaises(BitrixAPIError) as cm:
                worker.run_once(
                    client,
                    tenant_key="t1",
                    retry_budget=retry_budget,
                    dlq_path=pathlib.Path(tmp) / "dlq.jsonl",
                )
        self.assertEqual(cm.exception.code, "INVALID_OFFLINE_RESPONSE_SCHEMA")

    def test_run_once_invalid_event_schema_to_dlq(self):
        response = {
            "result": {
                "process_id": "p1",
                "events": [{"message_id": "9", "event": "E", "data": "bad"}],
            }
        }
        client = FakeClient(response)
        with tempfile.TemporaryDirectory() as tmp:
            dlq = pathlib.Path(tmp) / "dlq.jsonl"
            retry_budget = worker.RetryBudget(pathlib.Path(tmp) / "state.json", max_retries=2)
            count = worker.run_once(client, tenant_key="tenant-x", retry_budget=retry_budget, dlq_path=dlq)

            self.assertEqual(count, 1)
            rows = [json.loads(line) for line in dlq.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertIn("INVALID_EVENT_SCHEMA", rows[0]["error"])

        clear_calls = [c for c in client.calls if c[0] == "event.offline.clear"]
        self.assertEqual(len(clear_calls), 1)
        self.assertEqual(clear_calls[0][1]["message_id"], ["9"])
        error_calls = [c for c in client.calls if c[0] == "event.offline.error"]
        self.assertEqual(len(error_calls), 1)
        self.assertEqual(error_calls[0][1]["message_id"], ["9"])

    def test_run_once_retry_then_dlq_on_exhaust(self):
        response = {
            "result": {
                "process_id": "p1",
                "events": [{"message_id": "1", "event": "E1", "data": {"v": 1}}],
            }
        }
        client = FakeClient(response)
        with tempfile.TemporaryDirectory() as tmp:
            dlq = pathlib.Path(tmp) / "dlq.jsonl"
            retry_budget = worker.RetryBudget(pathlib.Path(tmp) / "state.json", max_retries=1)
            with mock.patch.object(worker, "process_event_default", side_effect=RuntimeError("boom")):
                count = worker.run_once(client, tenant_key="tenant-x", retry_budget=retry_budget, dlq_path=dlq)

            self.assertEqual(count, 1)
            rows = [json.loads(line) for line in dlq.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["error"], "boom")

        clear_calls = [c for c in client.calls if c[0] == "event.offline.clear"]
        self.assertEqual(len(clear_calls), 1)
        self.assertEqual(clear_calls[0][1]["message_id"], ["1"])
        error_calls = [c for c in client.calls if c[0] == "event.offline.error"]
        self.assertEqual(len(error_calls), 1)
        self.assertEqual(error_calls[0][1]["message_id"], ["1"])

    def test_run_once_invalid_application_token_does_not_clear(self):
        response = {
            "result": {
                "process_id": "p1",
                "events": [
                    {"message_id": "1", "event": "E1", "data": {}, "auth": {"application_token": "wrong"}}
                ],
            }
        }
        client = FakeClient(response)
        with tempfile.TemporaryDirectory() as tmp:
            retry_budget = worker.RetryBudget(pathlib.Path(tmp) / "state.json", max_retries=2)
            count = worker.run_once(
                client,
                tenant_key="t1",
                retry_budget=retry_budget,
                dlq_path=pathlib.Path(tmp) / "dlq.jsonl",
                application_token="expected",
            )
        self.assertEqual(count, 1)
        clear_calls = [c for c in client.calls if c[0] == "event.offline.clear"]
        self.assertEqual(len(clear_calls), 0)


if __name__ == "__main__":
    unittest.main()
