"""Guard the SKILL.md frontmatter against the open Agent Skills standard's hard limits.

Cross-runtime portability (Claude, Codex, Cursor, Gemini, Copilot, OpenClaw) depends on:
  name        : <= 64 chars, lowercase/digits/hyphens only
  description : non-empty, <= 1024 chars, no XML tags
The description is the ONLY selection signal, so we also assert it is reasonably rich.
"""

import pathlib
import re
import unittest

SKILL = pathlib.Path(__file__).resolve().parents[1] / "skills" / "bitrix24-agent" / "SKILL.md"


def frontmatter():
    text = SKILL.read_text(encoding="utf-8")
    block = text.split("---", 2)[1]
    name = re.search(r"^name:\s*(.+)$", block, re.M).group(1).strip()
    desc = re.search(r"^description:\s*(.+)$", block, re.M).group(1).strip()
    return name, desc


class SkillMetadataTests(unittest.TestCase):
    def test_name_constraints(self):
        name, _ = frontmatter()
        self.assertLessEqual(len(name), 64)
        self.assertRegex(name, r"^[a-z0-9-]+$", "name must be lowercase/digits/hyphens only")

    def test_folder_matches_name(self):
        # The skill folder name MUST equal the `name` field, or some runtimes (e.g. Copilot)
        # silently fail to load the skill.
        name, _ = frontmatter()
        self.assertEqual(SKILL.parent.name, name)

    def test_version_is_semver(self):
        block = SKILL.read_text(encoding="utf-8").split("---", 2)[1]
        m = re.search(r'^\s*version:\s*"?(\d+\.\d+\.\d+)"?\s*$', block, re.M)
        self.assertIsNotNone(m, "frontmatter must declare metadata.version as semver MAJOR.MINOR.PATCH")

    def test_description_constraints(self):
        _, desc = frontmatter()
        self.assertTrue(desc, "description must be non-empty")
        self.assertLessEqual(len(desc), 1024, "description exceeds the 1024-char standard limit")
        self.assertNotIn("<", desc, "description must not contain XML/HTML tags")
        # The description is the only trigger signal; keep it trigger-phrase-rich.
        self.assertGreaterEqual(len(desc), 120, "description too thin to trigger reliably")


if __name__ == "__main__":
    unittest.main()
