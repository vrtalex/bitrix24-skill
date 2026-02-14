import os
import pathlib
import sys
import unittest
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
        packs = b24.parse_pack_list("core,comms,core")
        self.assertEqual(packs, ["core", "comms"])
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

    def test_classify_method_risk_simple_and_batch(self):
        self.assertEqual(b24.classify_method_risk("crm.lead.list"), "read")
        self.assertEqual(b24.classify_method_risk("crm.lead.add"), "write")
        self.assertEqual(b24.classify_method_risk("crm.lead.delete"), "destructive")
        batch_params = {"cmd": {"a": "crm.lead.list", "b": "crm.lead.delete?id=1"}}
        self.assertEqual(b24.classify_method_risk("batch", params=batch_params), "destructive")

    def test_validate_method_and_params_batch_too_many_commands(self):
        commands = {f"cmd{i}": "crm.lead.list" for i in range(51)}
        with self.assertRaises(ValueError):
            b24.validate_method_and_params("batch", {"cmd": commands})

    def test_validate_method_and_params_method_pattern(self):
        with self.assertRaises(ValueError):
            b24.validate_method_and_params("crm.lead.add;", {})

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


if __name__ == "__main__":
    unittest.main()
