import pathlib
import sys
import unittest


TOOLS_DIR = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import verify_catalogs as vc  # noqa: E402


DATASET = {
    "crm.lead.add": {"method": "crm.lead.add", "deprecated": True, "replacement": "crm.item.add"},
    "crm.item.add": {"method": "crm.item.add", "deprecated": False, "replacement": None},
}


class VerifyCatalogsTests(unittest.TestCase):
    def test_parse_catalog_methods(self):
        text = (
            "# Catalog: core\n\n"
            "| Method | Risk | Docs |\n|---|---|---|\n"
            "| `crm.item.add` | write | https://x |\n"
            "| `batch` | mixed | https://y |\n"
            "Event docs: not a row\n"
        )
        self.assertEqual(vc.parse_catalog_methods(text), ["crm.item.add", "batch"])

    def test_verify_flags_unknown_method(self):
        report = vc.verify(["crm.item.add", "sonet_group.list"], DATASET)
        self.assertEqual(report["unknown"], ["sonet_group.list"])

    def test_verify_allows_system_methods(self):
        report = vc.verify(["batch", "methods", "events", "scope"], DATASET)
        self.assertEqual(report["unknown"], [])

    def test_verify_flags_deprecated_with_replacement(self):
        report = vc.verify(["crm.lead.add"], DATASET)
        self.assertEqual(report["deprecated"], [("crm.lead.add", "crm.item.add")])


if __name__ == "__main__":
    unittest.main()
