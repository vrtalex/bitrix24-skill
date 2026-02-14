import os
import pathlib
import sys
import time
import unittest


SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "skills" / "bitrix24-agent" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import bitrix24_client as b24  # noqa: E402


@unittest.skipUnless(os.getenv("B24_RUN_INTEGRATION") == "1", "Set B24_RUN_INTEGRATION=1 to run live portal tests")
class Bitrix24IntegrationSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tenant, token_store = b24.load_tenant_config_from_env()
        cls.client = b24.Bitrix24Client(tenant, token_store=token_store)

    def test_user_current(self):
        response = self.client.call("user.current", params={})
        self.assertIn("result", response)
        self.assertIsInstance(response["result"], dict)

    def test_method_get(self):
        response = self.client.call("method.get", params={"name": "user.get"})
        self.assertIn("result", response)
        self.assertIsInstance(response["result"], dict)
        self.assertIn("isExisting", response["result"])
        self.assertIn("isAvailable", response["result"])

    def test_crm_lead_list(self):
        response = self.client.call(
            "crm.lead.list",
            params={"select": ["ID", "TITLE"], "start": 0},
        )
        self.assertIn("result", response)
        self.assertIsInstance(response["result"], list)

    @unittest.skipUnless(os.getenv("B24_SMOKE_WRITE") == "1", "Set B24_SMOKE_WRITE=1 to run write smoke flow")
    def test_crm_lead_add_and_update(self):
        marker = f"SKILL_SMOKE_{int(time.time())}"
        create_resp = self.client.call(
            "crm.lead.add",
            params={"fields": {"TITLE": marker, "NAME": "Smoke"}},
        )
        lead_id = create_resp.get("result")
        self.assertTrue(lead_id)

        update_resp = self.client.call(
            "crm.lead.update",
            params={"id": lead_id, "fields": {"COMMENTS": "updated-by-smoke"}},
        )
        self.assertTrue(update_resp.get("result"))


if __name__ == "__main__":
    unittest.main()

