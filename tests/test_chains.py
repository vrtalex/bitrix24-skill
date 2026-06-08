"""Anti-drift: every method referenced in a chains-*.md recipe must exist in some catalog.

Chains compose catalogued methods; a chain citing an uncatalogued/typo'd method is the
doc-drift class earlier audits flagged. Method-like tokens are extracted conservatively:
backticked, dotted, starting lowercase, with NO all-caps segment (so field/param paths
like fields.UF_CRM_TASK or EXTRA.SEMANTICS are not mistaken for methods).
"""

import pathlib
import re
import unittest

REFS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "bitrix24-agent" / "references"
CATALOG_ROW = re.compile(r"^\|\s*`([^`]+)`")
BACKTICK = re.compile(r"`([^`]+)`")
METHOD_TOKEN = re.compile(r"^[a-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+$")
ALLCAPS_SEG = re.compile(r"^[A-Z][A-Z0-9_]*$")

# Method-like tokens that legitimately are NOT catalogued (system methods without per-method
# docs). Empty for now; add here only with justification.
KNOWN_NON_CATALOG: set = set()


def catalog_methods() -> set:
    methods = set()
    for path in REFS.glob("catalog-*.md"):
        for line in path.read_text(encoding="utf-8").splitlines():
            m = CATALOG_ROW.match(line)
            if m:
                methods.add(m.group(1).lower())
    return methods


def chain_method_tokens(text: str):
    for tok in BACKTICK.findall(text):
        if not METHOD_TOKEN.match(tok):
            continue
        if any(ALLCAPS_SEG.match(seg) for seg in tok.split(".")):
            continue  # param/field path (e.g. fields.UF_CRM_TASK), not a method
        yield tok


class ChainsConsistencyTests(unittest.TestCase):
    def test_chains_exist(self):
        self.assertGreaterEqual(len(list(REFS.glob("chains-*.md"))), 12)

    def test_chains_only_reference_catalogued_methods(self):
        catalog = catalog_methods()
        for path in sorted(REFS.glob("chains-*.md")):
            text = path.read_text(encoding="utf-8")
            for tok in chain_method_tokens(text):
                with self.subTest(chain=path.name, method=tok):
                    self.assertTrue(
                        tok.lower() in catalog or tok in KNOWN_NON_CATALOG,
                        f"{path.name} references `{tok}` which is not in any catalog",
                    )


if __name__ == "__main__":
    unittest.main()
