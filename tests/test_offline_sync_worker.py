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


    def test_event_handler_registry_dispatch(self):
        seen = []
        worker.register_handler("ONCRMDEALADD", lambda ev: seen.append(ev.get("event")))
        try:
            # dispatch routes by event name, case-insensitively
            worker.dispatch_event({"event": "oncrmdealadd", "data": {}})
            self.assertEqual(seen, ["oncrmdealadd"])
            # unregistered event falls back to the no-op default handler (no raise)
            worker.dispatch_event({"event": "ONSOMETHINGELSE", "data": {}})
            self.assertEqual(seen, ["oncrmdealadd"])
        finally:
            worker.EVENT_HANDLERS.clear()

    def test_redrive_dlq_reprocesses_and_keeps_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            dlq = pathlib.Path(tmp) / "dlq.jsonl"
            worker.write_dlq(dlq, tenant="t", event_item={"event": "ONOK", "message_id": "1", "data": {}}, error="x", retries=1)
            worker.write_dlq(dlq, tenant="t", event_item={"event": "ONFAIL", "message_id": "2", "data": {}}, error="y", retries=1)

            def boom(ev):
                raise RuntimeError("still failing")

            worker.register_handler("ONOK", lambda ev: None)
            worker.register_handler("ONFAIL", boom)
            try:
                reprocessed, remaining = worker.redrive_dlq(dlq)
            finally:
                worker.EVENT_HANDLERS.clear()

            self.assertEqual((reprocessed, remaining), (1, 1))
            rows = [json.loads(line) for line in dlq.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["event"], "ONFAIL")

    def test_bootstrap_offline_binds_with_event_type_offline(self):
        class Rec:
            def __init__(self):
                self.calls = []

            def call(self, method, params=None, **kwargs):
                self.calls.append((method, params))
                return {"result": True}

        rec = Rec()
        worker.bootstrap_offline(rec, "ONCRMLEADADD")
        self.assertEqual(rec.calls[0], ("event.bind", {"event": "ONCRMLEADADD", "event_type": "offline"}))

    def test_retry_budget_has_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            rb = worker.RetryBudget(pathlib.Path(tmp) / "s.json", max_retries=3)
            self.assertFalse(rb.has_pending())
            rb.fail("k1")
            self.assertTrue(rb.has_pending())
            rb.clear("k1")
            self.assertFalse(rb.has_pending())

    def test_dlq_masks_application_token(self):
        # A retry-exhausted event is persisted to the DLQ with its full payload, which can
        # include an auth.application_token. That secret must be masked at rest.
        response = {
            "result": {
                "process_id": "p1",
                "events": [
                    {
                        "message_id": "1",
                        "event": "E1",
                        "data": {"v": 1},
                        "auth": {"application_token": "SEKRETTOKEN"},
                    }
                ],
            }
        }
        client = FakeClient(response)
        with tempfile.TemporaryDirectory() as tmp:
            dlq = pathlib.Path(tmp) / "dlq.jsonl"
            rb = worker.RetryBudget(pathlib.Path(tmp) / "s.json", max_retries=1)
            with mock.patch.object(worker, "process_event_default", side_effect=RuntimeError("boom")):
                worker.run_once(client, tenant_key="t", retry_budget=rb, dlq_path=dlq)
            text = dlq.read_text(encoding="utf-8")
        self.assertNotIn("SEKRETTOKEN", text)
        self.assertIn("***", text)
        # The row must still be valid JSON.
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        self.assertEqual(len(rows), 1)

    def test_single_instance_lock_blocks_second_acquire(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = pathlib.Path(tmp) / "worker.lock"
            handle = worker.acquire_single_instance_lock(lock)
            try:
                with self.assertRaises(RuntimeError):
                    worker.acquire_single_instance_lock(lock)
            finally:
                handle.close()

    def test_tenant_lock_path_scopes_by_tenant(self):
        p = worker.tenant_lock_path(".runtime/offline_worker.lock", "portal.example")
        self.assertEqual(p.as_posix(), ".runtime/offline_worker_portal.example.lock")
        # Different tenants must resolve to different lock files so they can run concurrently.
        p2 = worker.tenant_lock_path(".runtime/offline_worker.lock", "https://other.bitrix24.ru")
        self.assertNotEqual(p, p2)
        # Scheme/path separators in the tenant key must be sanitized out of the filename.
        self.assertNotIn("/", p2.name)
        self.assertNotIn(":", p2.name)

    def test_parse_args_auto_refresh_flag(self):
        with mock.patch.object(sys, "argv", ["prog", "--auto-refresh"]):
            args = worker.parse_args()
        self.assertTrue(args.auto_refresh)
        with mock.patch.object(sys, "argv", ["prog"]):
            args = worker.parse_args()
        self.assertFalse(args.auto_refresh)


from bitrix24_client import NoopRateLimiter, TenantConfig, TokenStore  # noqa: E402


class WorkerMainTests(unittest.TestCase):
    """Cover main() loop, circuit breakers, and graceful shutdown."""

    def _drive_main(self, argv, on_call):
        tenant = TenantConfig(domain="t.example", auth_mode="webhook", webhook_user_id="1", webhook_code="c")

        class FakeClient:
            def __init__(self, *a, **k):
                pass

            def call(self, method, params=None, **k):
                return on_call(method, params)

        with mock.patch.object(worker, "load_tenant_config_from_env", return_value=(tenant, TokenStore())), \
                mock.patch.object(worker, "build_rate_limiter_from_env", return_value=NoopRateLimiter()), \
                mock.patch.object(worker, "Bitrix24Client", FakeClient), \
                mock.patch.object(worker.time, "sleep", lambda s: None), \
                mock.patch.object(sys, "argv", ["prog", "--lock-file", "", *argv]):
            worker.main()

    def test_graceful_shutdown_handler_sets_flag(self):
        gs = worker.GracefulShutdown()
        self.assertFalse(gs.should_stop)
        gs._handle_signal(15, None)
        self.assertTrue(gs.should_stop)

    def test_main_once_empty_batch_returns_cleanly(self):
        # Empty offline queue -> run_once returns 0 -> --once returns without SystemExit.
        self._drive_main(["--once"], lambda m, p: {"result": {"process_id": "", "events": []}})

    def test_main_fatal_error_exits_1(self):
        def on_call(method, params):
            raise BitrixAPIError("denied", status=403, code="WRONG_AUTH_TYPE")

        with self.assertRaises(SystemExit) as cm:
            self._drive_main(["--once"], on_call)
        self.assertEqual(cm.exception.code, 1)

    def test_main_consecutive_errors_breaker_exits_1(self):
        # Non-fatal, non-once: the consecutive-error breaker must stop the loop (exit 1),
        # not spin forever.
        def on_call(method, params):
            raise BitrixAPIError("slow", status=503, code="QUERY_LIMIT_EXCEEDED")

        with self.assertRaises(SystemExit) as cm:
            self._drive_main([], on_call)  # no --once
        self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
