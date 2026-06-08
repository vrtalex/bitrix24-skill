"""Hermetic CLI tests for bitrix24_client.main().

These exercise the governance pipeline (validation, allowlist, risk gates, plans,
exit codes) end-to-end via subprocess, without any network call: every scenario
exits before client.call() is reached (--list-packs / --plan-only / a rejected gate).
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


CLIENT = pathlib.Path(__file__).resolve().parents[1] / "skills" / "bitrix24-agent" / "scripts" / "bitrix24_client.py"


def run_cli(args, env_extra=None):
    env = {
        "B24_DOMAIN": "portal.example",
        "B24_AUTH_MODE": "webhook",
        "B24_WEBHOOK_USER_ID": "1",
        "B24_WEBHOOK_CODE": "secret",
        "B24_RATE_LIMITER": "off",
        "PATH": os.environ.get("PATH", ""),
    }
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(CLIENT), *args],
        capture_output=True,
        text=True,
        env=env,
    )


class CliTests(unittest.TestCase):
    def test_list_packs_exits_zero_with_packs(self):
        result = run_cli(["--list-packs"])
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("available_packs", payload)
        self.assertIn("core", payload["available_packs"])

    def test_write_without_confirm_is_rejected_exit_2(self):
        result = run_cli(["crm.lead.add", "--params", '{"fields":{"TITLE":"x"}}', "--packs", "core"])
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("--confirm-write", result.stderr)

    def test_destructive_without_confirm_is_rejected_exit_2(self):
        result = run_cli(["crm.lead.delete", "--params", '{"id":1}', "--packs", "core"])
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("--confirm-destructive", result.stderr)

    def test_method_outside_allowlist_rejected_exit_2(self):
        # landing.* is not in the default `core` pack.
        result = run_cli(["landing.site.getlist", "--params", "{}", "--packs", "core"])
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("allowlist", result.stderr)

    def test_plan_only_creates_plan_exit_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan_file = pathlib.Path(tmp) / "plans.json"
            result = run_cli([
                "crm.lead.add",
                "--params", '{"fields":{"TITLE":"x"}}',
                "--packs", "core",
                "--plan-only",
                "--plan-file", str(plan_file),
            ])
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("plan", payload)
            self.assertTrue(payload["plan"]["plan_id"])
            self.assertEqual(payload["plan"]["risk"], "write")

    def test_plan_only_accepts_positional_array_params(self):
        # Order-sensitive method passed as a positional JSON array must flow through
        # governance (validation/allowlist/risk/plan) without crashing on dict assumptions.
        with tempfile.TemporaryDirectory() as tmp:
            plan_file = pathlib.Path(tmp) / "plans.json"
            result = run_cli([
                "task.commentitem.add",
                "--params", '[123, {"POST_MESSAGE": "hi"}]',
                "--packs", "core",
                "--plan-only",
                "--plan-file", str(plan_file),
            ])
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["plan"]["method"], "task.commentitem.add")
            self.assertEqual(payload["plan"]["params"], [123, {"POST_MESSAGE": "hi"}])

    def test_batch_with_array_params_rejected_cleanly_exit_2(self):
        # A positional array is invalid for batch; the CLI must reject it with a clean
        # validation exit (2), not crash with a traceback.
        result = run_cli(["batch", "--params", "[1,2,3]", "--packs", "core"])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_preflight_blocks_missing_required_exit_2(self):
        # crm.item.add requires entityTypeId,fields; --preflight catches the omission locally.
        result = run_cli(["crm.item.add", "--params", "{}", "--packs", "core", "--preflight"])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("missing required params", result.stderr)
        self.assertIn("entityTypeId", result.stderr)

    def test_preflight_passes_when_required_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan_file = pathlib.Path(tmp) / "plans.json"
            result = run_cli([
                "crm.item.add",
                "--params", '{"entityTypeId":1,"fields":{"TITLE":"x"}}',
                "--packs", "core", "--preflight", "--plan-only",
                "--plan-file", str(plan_file),
            ])
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_preflight_skips_methods_without_required_map(self):
        # user.current has no required params (absent from the map) -> not blocked.
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli([
                "user.current", "--params", "{}", "--packs", "core", "--preflight", "--plan-only",
                "--plan-file", str(pathlib.Path(tmp) / "p.json"),
            ])
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_preflight_does_not_block_missing_required(self):
        # Default (no --preflight): missing required is NOT blocked locally (opt-in only).
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli([
                "crm.item.add", "--params", "{}", "--packs", "core", "--plan-only",
                "--plan-file", str(pathlib.Path(tmp) / "p.json"),
            ])
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_method_case_is_preserved_for_v2_namespaces(self):
        # v2/v3 method names are case-sensitive; the CLI must NOT lowercase them
        # (imbot.v2.bot.list -> method-not-found, imbot.v2.Bot.list -> found).
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli([
                "imbot.v2.Bot.list", "--params", "{}", "--packs", "bots",
                "--plan-only", "--plan-file", str(pathlib.Path(tmp) / "p.json"),
            ])
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["plan"]["method"], "imbot.v2.Bot.list")

    def test_bad_params_json_exit_1(self):
        result = run_cli(["user.current", "--params", "{not json}"])
        self.assertEqual(result.returncode, 1, result.stdout)


if __name__ == "__main__":
    unittest.main()
