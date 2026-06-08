import io
import json
import os
import pathlib
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import warnings
from unittest import mock


SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "skills" / "bitrix24-agent" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import bitrix24_client as b24  # noqa: E402


class Bitrix24ClientTests(unittest.TestCase):
    def test_parse_pack_list_defaults_to_core(self):
        self.assertEqual(b24.parse_pack_list(None), ["core"])
        self.assertEqual(b24.parse_pack_list(""), ["core"])

    def test_parse_pack_list_valid_and_unknown(self):
        packs = b24.parse_pack_list("core,comms,commerce,diagnostics,core")
        self.assertEqual(packs, ["core", "comms", "commerce", "diagnostics"])
        with self.assertRaises(ValueError):
            b24.parse_pack_list("unknown-pack")

    def test_expand_allowlist_with_packs(self):
        merged = b24.expand_allowlist_with_packs(["batch", "user.*"], ["core"])
        self.assertIn("crm.*", merged)
        self.assertIn("batch", merged)
        self.assertEqual(merged.count("batch"), 1)

    def test_is_method_allowed(self):
        patterns = ["crm.*", "user.*"]
        self.assertTrue(b24.is_method_allowed("crm.lead.add", patterns))
        self.assertFalse(b24.is_method_allowed("log.blogpost.add", patterns))

    def test_missing_required_params(self):
        req_map = {"crm.item.add": ["entityTypeId", "fields"]}
        # Missing both -> both reported, in declared order.
        self.assertEqual(
            b24.missing_required_params("crm.item.add", {}, req_map),
            ["entityTypeId", "fields"],
        )
        # One present, one missing.
        self.assertEqual(
            b24.missing_required_params("crm.item.add", {"entityTypeId": 1}, req_map),
            ["fields"],
        )
        # All present -> nothing missing.
        self.assertEqual(
            b24.missing_required_params("crm.item.add", {"entityTypeId": 1, "fields": {}}, req_map),
            [],
        )
        # Method not in the map -> skipped (no false positives for the discovered tail).
        self.assertEqual(b24.missing_required_params("some.unknown.method", {}, req_map), [])
        # Positional (list) params cannot be checked by name -> skipped.
        self.assertEqual(b24.missing_required_params("crm.item.add", [1, {}], req_map), [])

    def test_error_classification_limit_and_auth_codes(self):
        # QUERY_LIMIT_EXCEEDED (503) is a transient intensity limit -> retryable.
        query_limit = b24.BitrixAPIError("too many", status=503, code="QUERY_LIMIT_EXCEEDED")
        self.assertTrue(query_limit.retryable)
        self.assertFalse(query_limit.fatal)

        # OPERATION_TIME_LIMIT blocks a method for ~10 minutes; retrying in-call only burns
        # attempts. The code-based rule must override the status-based one: even if it arrives
        # with a 5xx status (where the generic rule would say "retry"), it must NOT be retryable.
        op_limit = b24.BitrixAPIError("method blocked", status=503, code="OPERATION_TIME_LIMIT")
        self.assertFalse(op_limit.retryable)
        self.assertFalse(op_limit.fatal)

        # OVERLOAD_LIMIT (503) is a manual block cleared only by Bitrix24 support:
        # despite status >= 500 it must NOT be retried and should stop worker loops.
        overload = b24.BitrixAPIError("rest blocked", status=503, code="OVERLOAD_LIMIT")
        self.assertFalse(overload.retryable)
        self.assertTrue(overload.fatal)

        # invalid_grant means the refresh_token is dead -> re-auth required, fatal.
        invalid_grant = b24.BitrixAPIError("bad refresh", status=400, code="invalid_grant")
        self.assertFalse(invalid_grant.retryable)
        self.assertTrue(invalid_grant.fatal)

        # A generic 5xx with no special code stays retryable.
        server_err = b24.BitrixAPIError("boom", status=500, code="")
        self.assertTrue(server_err.retryable)

    def test_classify_method_risk_simple_and_batch(self):
        self.assertEqual(b24.classify_method_risk("crm.lead.list"), "read")
        self.assertEqual(b24.classify_method_risk("crm.lead.add"), "write")
        self.assertEqual(b24.classify_method_risk("crm.lead.delete"), "destructive")
        batch_params = {"cmd": {"a": "crm.lead.list", "b": "crm.lead.delete?id=1"}}
        self.assertEqual(b24.classify_method_risk("batch", params=batch_params), "destructive")

    def test_classify_method_risk_prefers_catalog_risk_map(self):
        # The name-based regex misses verbs like defer/setOwner; the curated catalog Risk
        # column is the source of truth, so classify must consult it (case-insensitively).
        rmap = {"tasks.task.defer": "write", "im.chat.setowner": "write", "crm.item.delete": "destructive"}
        self.assertEqual(b24.classify_method_risk("tasks.task.defer", risk_map=rmap), "write")
        self.assertEqual(b24.classify_method_risk("im.chat.setOwner", risk_map=rmap), "write")
        self.assertEqual(b24.classify_method_risk("crm.item.delete", risk_map=rmap), "destructive")
        # uncatalogued method -> regex heuristic fallback
        self.assertEqual(b24.classify_method_risk("crm.unknown.add", risk_map=rmap), "write")
        # batch always recurses into cmd regardless of the map
        self.assertEqual(
            b24.classify_method_risk("batch", params={"cmd": {"a": "crm.lead.delete?id=1"}}, risk_map=rmap),
            "destructive",
        )

    def test_validate_method_and_params_batch_too_many_commands(self):
        commands = {f"cmd{i}": "crm.lead.list" for i in range(51)}
        with self.assertRaises(ValueError):
            b24.validate_method_and_params("batch", {"cmd": commands})

    def test_validate_method_and_params_method_pattern(self):
        with self.assertRaises(ValueError):
            b24.validate_method_and_params("crm.lead.add;", {})

    def test_validate_method_and_params_batch_rejects_array(self):
        # batch requires a named object with a `cmd` map; a positional array is invalid
        # and must be rejected cleanly (not crash later in the batch allowlist walk).
        with self.assertRaises(ValueError):
            b24.validate_method_and_params("batch", [1, 2, 3])
        with self.assertRaises(ValueError):
            b24.validate_method_and_params("event.offline.get", [1])

    def test_build_url_webhook_and_oauth(self):
        webhook_tenant = b24.TenantConfig(
            domain="example.test",
            auth_mode="webhook",
            webhook_user_id="1",
            webhook_code="abc",
        )
        client = b24.Bitrix24Client(webhook_tenant)
        self.assertEqual(
            client._build_url(method="crm.lead.list", rest_v3=False),
            "https://example.test/rest/1/abc/crm.lead.list",
        )

        # Webhook + REST v3 must use the /rest/api/{user}/{code}/ path, not silently fall
        # back to v2.
        self.assertEqual(
            client._build_url(method="crm.lead.list", rest_v3=True),
            "https://example.test/rest/api/1/abc/crm.lead.list",
        )

        oauth_tenant = b24.TenantConfig(domain="https://portal.example", auth_mode="oauth")
        oauth_client = b24.Bitrix24Client(oauth_tenant)
        self.assertEqual(
            oauth_client._build_url(method="crm.lead.list", rest_v3=False),
            "https://portal.example/rest/crm.lead.list",
        )
        self.assertEqual(
            oauth_client._build_url(method="crm.lead.list", rest_v3=True),
            "https://portal.example/rest/api/crm.lead.list",
        )

    def test_validate_accepts_camelcase_method(self):
        # v2/v3 namespaces are case-SENSITIVE (e.g. imbot.v2.Bot.list); the method-name
        # validator must accept mixed case so the client can send it verbatim.
        b24.validate_method_and_params("imbot.v2.Bot.list", {})  # must not raise
        b24.validate_method_and_params("tasks.api.scrum.kanban.getStages", {"sprintId": 1})

    def test_build_url_rejects_plaintext_http(self):
        tenant = b24.TenantConfig(
            domain="http://portal.example",
            auth_mode="webhook",
            webhook_user_id="1",
            webhook_code="abc",
        )
        client = b24.Bitrix24Client(tenant)
        with self.assertRaises(ValueError):
            client._build_url(method="crm.lead.list", rest_v3=False)

    def test_build_url_rejects_uppercase_http_scheme(self):
        # Scheme detection must be case-insensitive so 'HTTP://' cannot slip past the guard.
        tenant = b24.TenantConfig(
            domain="HTTP://portal.example",
            auth_mode="webhook",
            webhook_user_id="1",
            webhook_code="abc",
        )
        client = b24.Bitrix24Client(tenant)
        with self.assertRaises(ValueError):
            client._build_url(method="crm.lead.list", rest_v3=False)

    def test_mask_secrets_redacts_tokens_including_application_token(self):
        text = (
            '{"access_token": "AAA", "refresh_token": "RRR", '
            '"application_token": "PPP", "result": 7}'
        )
        masked = b24.mask_secrets(text)
        self.assertNotIn("AAA", masked)
        self.assertNotIn("RRR", masked)
        self.assertNotIn("PPP", masked)
        self.assertIn("result", masked)
        self.assertIn("7", masked)

    def test_load_tenant_config_from_env_webhook(self):
        env = {
            "B24_DOMAIN": "portal.example",
            "B24_AUTH_MODE": "webhook",
            "B24_WEBHOOK_USER_ID": "7",
            "B24_WEBHOOK_CODE": "secret",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            tenant, tokens = b24.load_tenant_config_from_env()
        self.assertEqual(tenant.auth_mode, "webhook")
        self.assertEqual(tenant.webhook_user_id, "7")
        self.assertEqual(tokens.get_tokens(), (None, None))

    def test_load_tenant_config_from_env_oauth(self):
        env = {
            "B24_DOMAIN": "portal.example",
            "B24_AUTH_MODE": "oauth",
            "B24_ACCESS_TOKEN": "access",
            "B24_REFRESH_TOKEN": "refresh",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            tenant, tokens = b24.load_tenant_config_from_env()
        self.assertEqual(tenant.auth_mode, "oauth")
        self.assertEqual(tokens.get_tokens(), ("access", "refresh"))

    def test_load_tenant_config_requires_domain(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                b24.load_tenant_config_from_env()

    def test_build_rate_limiter_from_env_off(self):
        with mock.patch.dict(os.environ, {"B24_RATE_LIMITER": "off"}, clear=True):
            limiter = b24.build_rate_limiter_from_env()
        self.assertIsInstance(limiter, b24.NoopRateLimiter)

    def test_plan_store_create_and_consume(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan_store = b24.PlanStore(pathlib.Path(tmp) / "plans.json", ttl_sec=120)
            plan = plan_store.create(
                tenant="portal.example",
                method="crm.lead.add",
                params={"fields": {"TITLE": "x"}},
                risk="write",
                allowlisted=True,
                packs=["core"],
            )
            consumed = plan_store.consume(plan["plan_id"], tenant="portal.example")
            self.assertEqual(consumed["method"], "crm.lead.add")
            with self.assertRaises(ValueError):
                plan_store.consume(plan["plan_id"], tenant="portal.example")

    def test_idempotency_store_masks_response_at_rest(self):
        # Cached responses are persisted under .runtime/; secrets must be masked at rest
        # (consistent with the DLQ), not stored in cleartext.
        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp) / "idem.json"
            store = b24.IdempotencyStore(f, ttl_sec=120)
            store.done("k", {"result": {"access_token": "SECRET123", "id": 5}})
            raw = f.read_text(encoding="utf-8")
            self.assertNotIn("SECRET123", raw)
            self.assertIn("***", raw)
            replay = store.check_replay("k")
            self.assertEqual(replay["result"]["id"], 5)

    def test_idempotency_store_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = b24.IdempotencyStore(pathlib.Path(tmp) / "idem.json", ttl_sec=120)
            key = store.key_for(
                tenant="portal.example",
                method="crm.lead.add",
                params={"fields": {"TITLE": "x"}},
                explicit_key="abc-123",
            )
            self.assertIsNone(store.check_replay(key))
            store.start(key)
            self.assertIsNone(store.check_replay(key))
            store.done(key, {"result": 42})
            self.assertEqual(store.check_replay(key), {"result": 42})
            store.clear(key)
            self.assertIsNone(store.check_replay(key))


class Bitrix24CallTests(unittest.TestCase):
    """Hermetic tests for the call() retry/refresh/error core (no real network)."""

    def _webhook_client(self, **kwargs):
        tenant = b24.TenantConfig(
            domain="example.test",
            auth_mode="webhook",
            webhook_user_id="1",
            webhook_code="abc",
        )
        return b24.Bitrix24Client(tenant, **kwargs)

    def _oauth_client(self, store, **kwargs):
        tenant = b24.TenantConfig(domain="https://portal.example", auth_mode="oauth")
        return b24.Bitrix24Client(tenant, token_store=store, **kwargs)

    def test_iter_list_follows_next_cursor(self):
        client = self._webhook_client()
        pages = [
            {"result": [{"ID": 1}, {"ID": 2}], "next": 2},
            {"result": [{"ID": 3}]},  # no "next" -> stop
        ]
        seen_starts = []

        def fake_call(method, params=None, **kwargs):
            seen_starts.append((params or {}).get("start"))
            return pages.pop(0)

        with mock.patch.object(client, "call", side_effect=fake_call):
            items = list(client.iter_list("crm.lead.list", {}))

        self.assertEqual([item["ID"] for item in items], [1, 2, 3])
        self.assertEqual(seen_starts, [0, 2])

    def test_iter_list_handles_crm_item_items_shape(self):
        # Universal crm.item.* nests rows under result.items (a dict), not a top-level list.
        # iter_list must yield those items across pages (a dict-shaped result.items yields 0
        # under naive list handling).
        client = self._webhook_client()
        pages = [
            {"result": {"items": [{"id": 1}, {"id": 2}]}, "next": 2},
            {"result": {"items": [{"id": 3}]}},  # no "next" -> stop
        ]

        def fake_call(method, params=None, **kwargs):
            return pages.pop(0)

        with mock.patch.object(client, "call", side_effect=fake_call):
            got = list(client.iter_list("crm.item.list", {"entityTypeId": 1}))
        self.assertEqual([i["id"] for i in got], [1, 2, 3])

    def test_write_audit_row_appends_parseable_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = pathlib.Path(tmp) / "audit.jsonl"
            b24.write_audit_row(audit, {"a": 1})
            b24.write_audit_row(audit, {"a": 2})
            rows = [json.loads(line) for line in audit.read_text().splitlines() if line.strip()]
            self.assertEqual([r["a"] for r in rows], [1, 2])

    def test_to_api_error_parses_v2_and_v3(self):
        client = self._webhook_client()
        v2 = client._to_api_error(status=400, body={"error": "QUERY_LIMIT_EXCEEDED", "error_description": "slow down"})
        self.assertEqual(v2.code, "QUERY_LIMIT_EXCEEDED")
        self.assertEqual(str(v2), "slow down")

        v3 = client._to_api_error(status=400, body={"error": {"code": "ACCESS_DENIED", "message": "nope"}})
        self.assertEqual(v3.code, "ACCESS_DENIED")
        self.assertEqual(str(v3), "nope")

        ok = client._to_api_error(status=200, body={"result": 1})
        self.assertEqual(ok.code, "")

    def test_call_retries_transient_then_succeeds(self):
        client = self._webhook_client(max_attempts=3)
        responses = [{"error": "QUERY_LIMIT_EXCEEDED"}, {"result": 42}]
        with mock.patch.object(client, "_post_json", side_effect=responses) as post, \
                mock.patch.object(b24.Bitrix24Client, "_backoff", lambda self, attempt: None):
            result = client.call("crm.lead.list", {})
        self.assertEqual(result, {"result": 42})
        self.assertEqual(post.call_count, 2)

    def test_call_does_not_retry_operation_time_limit(self):
        # Arrive as HTTP 503 so the generic status>=500 rule would (wrongly) retry it; the
        # code-based NON_RETRYABLE rule must stop after a single attempt.
        client = self._webhook_client(max_attempts=5)

        def raise_http_503(url, payload):
            body = io.BytesIO(json.dumps({"error": "OPERATION_TIME_LIMIT"}).encode())
            raise urllib.error.HTTPError("https://example.test/x", 503, "blocked", {}, body)

        with mock.patch.object(client, "_post_json", side_effect=raise_http_503) as post, \
                mock.patch.object(b24.Bitrix24Client, "_backoff", lambda self, attempt: None):
            with self.assertRaises(b24.BitrixAPIError) as cm:
                client.call("crm.lead.list", {})
        self.assertEqual(cm.exception.code, "OPERATION_TIME_LIMIT")
        self.assertEqual(post.call_count, 1)

    def test_call_does_not_retry_fatal(self):
        client = self._webhook_client(max_attempts=5)
        with mock.patch.object(client, "_post_json", return_value={"error": "ACCESS_DENIED"}) as post, \
                mock.patch.object(b24.Bitrix24Client, "_backoff", lambda self, attempt: None):
            with self.assertRaises(b24.BitrixAPIError) as cm:
                client.call("crm.lead.delete", {"id": 1})
        self.assertEqual(cm.exception.code, "ACCESS_DENIED")
        self.assertEqual(post.call_count, 1)

    def test_call_refreshes_oauth_token_once_then_retries(self):
        store = b24.TokenStore(access_token="old", refresh_token="r1")
        refresh_calls = []

        def refresh_cb(tenant, token_store):
            refresh_calls.append(1)
            token_store.set_tokens("new", "r2")
            return "new", "r2"

        client = self._oauth_client(store, refresh_callback=refresh_cb, max_attempts=3)
        captured = []

        def fake_post(url, payload):
            captured.append(dict(payload))
            if len(captured) == 1:
                return {"error": "expired_token"}
            return {"result": 7}

        with mock.patch.object(client, "_post_json", side_effect=fake_post), \
                mock.patch.object(b24.Bitrix24Client, "_backoff", lambda self, attempt: None):
            result = client.call("user.current", {})

        self.assertEqual(result, {"result": 7})
        self.assertEqual(len(refresh_calls), 1)
        self.assertEqual(captured[0]["auth"], "old")
        self.assertEqual(captured[1]["auth"], "new")

    def test_call_positional_list_params_webhook(self):
        # Order-sensitive methods (e.g. task.commentitem.add) must be passed as a
        # positional JSON array, not a named object. The client must send the array verbatim.
        client = self._webhook_client()
        captured = {}

        def fake_post(url, payload):
            captured["url"] = url
            captured["payload"] = payload
            return {"result": True}

        with mock.patch.object(client, "_post_json", side_effect=fake_post):
            client.call("task.commentitem.add", [123, {"POST_MESSAGE": "hi"}])

        self.assertEqual(captured["payload"], [123, {"POST_MESSAGE": "hi"}])
        # Webhook auth lives in the URL path, never injected into the positional array.
        self.assertNotIn("auth=", captured["url"])

    def test_call_positional_list_params_oauth_puts_auth_in_query(self):
        store = b24.TokenStore(access_token="tok")
        client = self._oauth_client(store)
        captured = {}

        def fake_post(url, payload):
            captured["url"] = url
            captured["payload"] = payload
            return {"result": True}

        with mock.patch.object(client, "_post_json", side_effect=fake_post):
            client.call("task.commentitem.add", [123, {"POST_MESSAGE": "hi"}])

        # The list must NOT be mutated with an 'auth' entry; auth goes to the query string.
        self.assertEqual(captured["payload"], [123, {"POST_MESSAGE": "hi"}])
        self.assertIn("auth=tok", captured["url"])

    def _run_loser_path(self, *, winner_rotates_token: bool) -> bool:
        """Drive _try_refresh_token down its loser branch with a concurrent lock holder
        that simulates a winner which either rotated the token or failed (left it unchanged).
        Returns what the loser path returned."""
        store = b24.TokenStore(access_token="old", refresh_token="r1")
        # refresh_callback must NOT be invoked on the loser path; make it loud if it is.
        client = self._oauth_client(
            store,
            refresh_callback=lambda t, s: (_ for _ in ()).throw(AssertionError("loser must not refresh")),
        )

        holder_has_lock = threading.Event()
        allow_release = threading.Event()

        def holder():
            client._refresh_lock.acquire()
            holder_has_lock.set()
            allow_release.wait(2.0)
            if winner_rotates_token:
                store.set_tokens("new", "r2")
            client._refresh_lock.release()

        t = threading.Thread(target=holder)
        t.start()
        self.assertTrue(holder_has_lock.wait(2.0))

        # Let the holder release shortly after the loser starts waiting on the lock.
        threading.Thread(target=lambda: (time.sleep(0.05), allow_release.set())).start()
        try:
            return client._try_refresh_token()
        finally:
            allow_release.set()
            t.join(2.0)

    def test_refresh_loser_returns_false_when_token_unchanged(self):
        # Winner's refresh failed -> token unchanged -> loser must NOT assume success.
        self.assertFalse(self._run_loser_path(winner_rotates_token=False))

    def test_refresh_loser_returns_true_when_token_rotated(self):
        # Winner rotated the token -> loser may safely proceed.
        self.assertTrue(self._run_loser_path(winner_rotates_token=True))


class OutputShapingTests(unittest.TestCase):
    """Opt-in output-token economy: shape_output trims what the agent has to read."""

    def test_full_is_indented_default(self):
        out = b24.shape_output({"result": [1, 2]}, mode="full")
        self.assertIn("\n", out)  # indent=2 multi-line (unchanged default)

    def test_compact_has_no_whitespace(self):
        out = b24.shape_output({"result": [1, 2]}, mode="compact")
        self.assertEqual(out, '{"result":[1,2]}')

    def test_summary_digests_a_list_result(self):
        resp = {"result": [{"id": 1}, {"id": 2}, {"id": 3}], "next": 50, "total": 240}
        digest = json.loads(b24.shape_output(resp, mode="summary"))
        self.assertEqual(digest["count"], 3)
        self.assertEqual(digest["ids"], [1, 2, 3])
        self.assertEqual(digest["next"], 50)
        self.assertEqual(digest["total"], 240)

    def test_summary_digests_crm_item_items_shape(self):
        resp = {"result": {"items": [{"id": 7}, {"id": 8}]}, "total": 2}
        digest = json.loads(b24.shape_output(resp, mode="summary"))
        self.assertEqual(digest["count"], 2)
        self.assertEqual(digest["ids"], [7, 8])

    def test_max_items_truncates_and_marks(self):
        out = json.loads(b24.shape_output({"result": [1, 2, 3, 4, 5]}, mode="compact", max_items=2))
        self.assertEqual(out["result"], [1, 2])
        self.assertEqual(out["_truncated"], {"shown": 2, "of": 5})

    def test_max_items_truncates_items_shape(self):
        resp = {"result": {"items": [{"id": 1}, {"id": 2}, {"id": 3}]}}
        out = json.loads(b24.shape_output(resp, mode="compact", max_items=1))
        self.assertEqual(out["result"]["items"], [{"id": 1}])
        self.assertEqual(out["_truncated"], {"shown": 1, "of": 3})

    def test_does_not_mutate_input(self):
        resp = {"result": [1, 2, 3]}
        b24.shape_output(resp, mode="compact", max_items=1)
        self.assertEqual(resp["result"], [1, 2, 3])  # original untouched


class _FakeResp:
    """Minimal context-manager stand-in for urllib.request.urlopen's return value."""

    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Bitrix24CoverageTests(unittest.TestCase):
    """Cover the previously-untested high-risk paths (rate limiter, OAuth refresh, network
    error branches, transport I/O, store edge cases)."""

    def _webhook_client(self, **kwargs):
        tenant = b24.TenantConfig(domain="example.test", auth_mode="webhook", webhook_user_id="1", webhook_code="abc")
        return b24.Bitrix24Client(tenant, **kwargs)

    # --- B1: FileRateLimiter token-bucket math ---
    def test_file_rate_limiter_depletes_and_waits(self):
        with tempfile.TemporaryDirectory() as tmp:
            rl = b24.FileRateLimiter(pathlib.Path(tmp) / "rl.json", rate_per_sec=1.0, burst=2.0)
            with mock.patch.object(b24.time, "time", return_value=1000.0):
                self.assertEqual(rl._reserve("d"), 0.0)   # 2 -> 1 token
                self.assertEqual(rl._reserve("d"), 0.0)   # 1 -> 0 token
                self.assertGreater(rl._reserve("d"), 0.0)  # empty -> must wait

    def test_file_rate_limiter_evicts_stale_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "rl.json"
            rl = b24.FileRateLimiter(path, rate_per_sec=2.0, burst=10.0, state_ttl_sec=60)
            path.write_text(json.dumps({"old": {"last": 100.0, "tokens": 5.0}}), encoding="utf-8")
            with mock.patch.object(b24.time, "time", return_value=10_000.0):
                rl._reserve("fresh")
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("old", state)
            self.assertIn("fresh", state)

    # --- B2: refresh_via_oauth_server ---
    def _oauth_env(self):
        return {"B24_CLIENT_ID": "cid", "B24_CLIENT_SECRET": "csecret"}

    def test_refresh_via_oauth_server_success(self):
        tenant = b24.TenantConfig(domain="portal.example", auth_mode="oauth")
        store = b24.TokenStore(refresh_token="r1")
        with mock.patch.dict(os.environ, self._oauth_env(), clear=False), \
                mock.patch("bitrix24_client.urllib.request.urlopen",
                           return_value=_FakeResp({"access_token": "newA", "refresh_token": "newR"})):
            access, refresh = b24.refresh_via_oauth_server(tenant, store)
        self.assertEqual((access, refresh), ("newA", "newR"))

    def test_refresh_via_oauth_server_invalid_grant_is_fatal(self):
        tenant = b24.TenantConfig(domain="portal.example", auth_mode="oauth")
        store = b24.TokenStore(refresh_token="dead")
        with mock.patch.dict(os.environ, self._oauth_env(), clear=False), \
                mock.patch("bitrix24_client.urllib.request.urlopen",
                           return_value=_FakeResp({"error": "invalid_grant", "error_description": "bad"})):
            with self.assertRaises(b24.BitrixAPIError) as cm:
                b24.refresh_via_oauth_server(tenant, store)
        self.assertEqual(cm.exception.code, "invalid_grant")
        self.assertTrue(cm.exception.fatal)

    def test_refresh_via_oauth_server_guards(self):
        tenant = b24.TenantConfig(domain="portal.example", auth_mode="oauth")
        with self.assertRaises(b24.BitrixAPIError) as cm:
            b24.refresh_via_oauth_server(tenant, b24.TokenStore(refresh_token=None))
        self.assertEqual(cm.exception.code, "MISSING_REFRESH_TOKEN")
        with mock.patch.dict(os.environ, {"B24_CLIENT_ID": "", "B24_CLIENT_SECRET": ""}, clear=False):
            with self.assertRaises(b24.BitrixAPIError) as cm2:
                b24.refresh_via_oauth_server(tenant, b24.TokenStore(refresh_token="r"))
        self.assertEqual(cm2.exception.code, "MISSING_CLIENT_CREDENTIALS")

    # --- B3: call() network branches ---
    def test_call_network_error_after_attempts(self):
        client = self._webhook_client(max_attempts=1)
        with mock.patch.object(client, "_post_json", side_effect=urllib.error.URLError("refused")), \
                mock.patch.object(b24.Bitrix24Client, "_backoff", lambda self, attempt: None):
            with self.assertRaises(b24.BitrixAPIError) as cm:
                client.call("user.current", {})
        self.assertEqual(cm.exception.code, "NETWORK_ERROR")

    def test_call_retries_url_error_then_succeeds(self):
        client = self._webhook_client(max_attempts=3)
        seq = [urllib.error.URLError("flap"), {"result": 1}]

        def fake(url, payload):
            v = seq.pop(0)
            if isinstance(v, Exception):
                raise v
            return v

        with mock.patch.object(client, "_post_json", side_effect=fake), \
                mock.patch.object(b24.Bitrix24Client, "_backoff", lambda self, attempt: None):
            self.assertEqual(client.call("user.current", {}), {"result": 1})

    def test_call_httperror_500_retries_then_succeeds(self):
        client = self._webhook_client(max_attempts=3)
        calls = {"n": 0}

        def fake(url, payload):
            calls["n"] += 1
            if calls["n"] == 1:
                raise urllib.error.HTTPError("u", 500, "err", {}, io.BytesIO(b"{}"))
            return {"result": 9}

        with warnings.catch_warnings(), \
                mock.patch.object(client, "_post_json", side_effect=fake), \
                mock.patch.object(b24.Bitrix24Client, "_backoff", lambda self, attempt: None):
            warnings.simplefilter("ignore", ResourceWarning)  # synthetic HTTPError fp
            self.assertEqual(client.call("user.current", {}), {"result": 9})

    # --- B4: transport I/O ---
    def test_post_json_parses_and_wraps(self):
        client = self._webhook_client()
        with mock.patch("bitrix24_client.urllib.request.urlopen", return_value=_FakeResp({"result": 1})):
            self.assertEqual(client._post_json("https://x/m", {}), {"result": 1})
        with mock.patch("bitrix24_client.urllib.request.urlopen", return_value=_FakeResp([1, 2])):
            self.assertEqual(client._post_json("https://x/m", {}), {"result": [1, 2]})

    def test_post_json_invalid_json_raises(self):
        class Garbage(_FakeResp):
            def read(self):
                return b"<<not json>>"

        client = self._webhook_client()
        with mock.patch("bitrix24_client.urllib.request.urlopen", return_value=Garbage(None)):
            with self.assertRaises(b24.BitrixAPIError) as cm:
                client._post_json("https://x/m", {})
        self.assertEqual(cm.exception.code, "INVALID_JSON")

    def test_read_http_error_falls_back_on_unreadable_body(self):
        class BadErr(urllib.error.HTTPError):
            def __init__(self):
                # A real file object as fp keeps .close() safe across Python versions
                # (fp=None makes 3.9's HTTPError.close() raise KeyError: 'file').
                super().__init__("u", 503, "err", {}, io.BytesIO(b""))

            def read(self):
                raise OSError("cannot read")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)  # synthetic HTTPError
            err = BadErr()
            code, body = b24.Bitrix24Client._read_http_error(err)
            err.close()
        self.assertEqual((code, body), (503, ""))

    # --- B5: store edge cases ---
    def test_plan_store_rejects_expired_tenant_mismatch_and_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = b24.PlanStore(pathlib.Path(tmp) / "p.json", ttl_sec=120)
            with self.assertRaises(ValueError):
                store.consume("nope", tenant="t")  # not found
            plan = store.create(tenant="t", method="crm.item.add", params={}, risk="write", allowlisted=True, packs=["core"])
            with self.assertRaises(ValueError):
                store.consume(plan["plan_id"], tenant="other")  # tenant mismatch
            store.consume(plan["plan_id"], tenant="t")
            with self.assertRaises(ValueError):
                store.consume(plan["plan_id"], tenant="t")  # double-execute

    def test_idempotency_key_for_explicit_and_business_fields(self):
        store = b24.IdempotencyStore(pathlib.Path("/tmp/never-written.json"))
        self.assertEqual(
            store.key_for(tenant="t", method="m", params={}, explicit_key="K"),
            "t|m|K",
        )
        self.assertIn("origin_id:42", store.key_for(tenant="t", method="m", params={"origin_id": 42}))

    def test_idempotency_check_replay_misses_expired_and_in_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = b24.IdempotencyStore(pathlib.Path(tmp) / "i.json", ttl_sec=120)
            store.start("k")
            self.assertIsNone(store.check_replay("k"))  # in_progress -> no replay
            store.done("k", {"result": 1})
            self.assertEqual(store.check_replay("k"), {"result": 1})
            store.clear("k")
            self.assertIsNone(store.check_replay("k"))


if __name__ == "__main__":
    unittest.main()
