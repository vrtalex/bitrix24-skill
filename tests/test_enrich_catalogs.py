import pathlib
import sys
import unittest


TOOLS_DIR = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import enrich_catalogs as en  # noqa: E402


BASE = "https://github.com/bitrix24/b24restdocs/blob/main/api-reference/"

DATASET = {
    "crm.item.update": {"scope": ["crm"], "required": ["entityTypeId", "fields"], "deprecated": False, "replacement": None, "doc_path": "crm/universal/crm-item-update.md"},
    "crm.lead.update": {"scope": ["crm"], "required": ["id"], "deprecated": True, "replacement": "crm.item.update", "doc_path": "crm/leads/crm-lead-update.md"},
}


class EnrichRowTests(unittest.TestCase):
    def test_enriches_current_method_with_scope_required_and_canonical_url(self):
        out = en.enrich_row("| `crm.item.update` | write | https://stale |", DATASET)
        self.assertEqual(
            out,
            f"| `crm.item.update` | write | crm | entityTypeId,fields |  | {BASE}crm/universal/crm-item-update.md |",
        )

    def test_marks_deprecated_with_replacement(self):
        out = en.enrich_row("| `crm.lead.update` | write | https://stale |", DATASET)
        self.assertEqual(
            out,
            f"| `crm.lead.update` | write | crm | id | → crm.item.update | {BASE}crm/leads/crm-lead-update.md |",
        )

    def test_system_method_absent_from_dataset_keeps_existing_url(self):
        out = en.enrich_row("| `batch` | mixed | https://settings/batch.md |", DATASET)
        self.assertEqual(out, "| `batch` | mixed | - |  |  | https://settings/batch.md |")

    def test_idempotent_on_already_enriched_row(self):
        enriched = f"| `crm.item.update` | write | crm | entityTypeId,fields |  | {BASE}crm/universal/crm-item-update.md |"
        self.assertEqual(en.enrich_row(enriched, DATASET), enriched)

    def test_non_row_passes_through(self):
        self.assertEqual(en.enrich_row("Some note line", DATASET), "Some note line")
        self.assertEqual(en.enrich_row("", DATASET), "")


if __name__ == "__main__":
    unittest.main()
