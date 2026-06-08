"""Characterization + structural tests for the reference catalogs.

These lock the catalog table contract so later enrichment (added columns, new rows,
deprecation annotations) is a deliberate, reviewed change rather than silent drift.
The Python client does NOT parse these files at runtime; they are read by the agent.
"""

import pathlib
import re
import unittest


REFS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "bitrix24-agent" / "references"
CATALOGS = sorted(REFS.glob("catalog-*.md"))

ALLOWED_RISK = {"read", "write", "destructive", "mixed"}
# Method ids are dotted segments; segments may be camelCase (e.g. landing.site.getList,
# tasks.api.scrum.kanban.getStages) or contain underscores (sonet_group.create).
METHOD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*$")
# A catalog method row: | `method` | risk | <docs url> |  (extra columns allowed after).
ROW_RE = re.compile(r"^\|\s*`(?P<method>[^`]+)`\s*\|\s*(?P<risk>[a-z]+)\s*\|")


def iter_catalog_rows(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if m:
            yield m.group("method"), m.group("risk"), line


class CatalogStructureTests(unittest.TestCase):
    def test_catalogs_exist(self):
        self.assertGreaterEqual(len(CATALOGS), 12, "expected at least 12 capability-pack catalogs")

    def test_every_catalog_has_a_header_and_rows(self):
        for path in CATALOGS:
            with self.subTest(catalog=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertRegex(text, r"^#\s*Catalog:", "missing '# Catalog:' title")
                self.assertIn(
                    "| Method | Risk | Scope | Required | Deprecated | Docs |",
                    text,
                    "missing canonical enriched table header",
                )
                rows = list(iter_catalog_rows(path))
                self.assertGreater(len(rows), 0, "catalog has no method rows")

    def test_rows_are_well_formed(self):
        for path in CATALOGS:
            for method, risk, line in iter_catalog_rows(path):
                with self.subTest(catalog=path.name, method=method):
                    self.assertRegex(method, METHOD_RE, f"malformed method id: {method}")
                    self.assertIn(risk, ALLOWED_RISK, f"risk '{risk}' not in {ALLOWED_RISK}")
                    self.assertIn(
                        "https://github.com/bitrix24/b24restdocs",
                        line,
                        "row missing official docs URL",
                    )

    def test_total_method_coverage_sanity(self):
        total = sum(len(list(iter_catalog_rows(p))) for p in CATALOGS)
        # Sanity floor only (exact count grows as the head is enriched); guards accidental loss.
        self.assertGreaterEqual(total, 120, f"catalog coverage dropped unexpectedly to {total}")


if __name__ == "__main__":
    unittest.main()
