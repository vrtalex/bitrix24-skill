#!/usr/bin/env python3
"""Static token-footprint report for the skill's lean-load path.

DEV/CI ONLY. Measures the context cost (bytes and an approximate token count) of the
files an agent loads before acting: packs.md + one catalog. This is the input-token
half of the token budget; the output-token half (fewer doc-page opens, first-call
success) is measured live with an agent and is documented in tools/README.md.
"""

from __future__ import annotations

import pathlib

REFS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "bitrix24-agent" / "references"


def approx_tokens(text: str) -> int:
    # Rough heuristic (~4 chars/token); good enough to track relative footprint over time.
    return (len(text) + 3) // 4


def report() -> str:
    lines = ["file\tbytes\t~tokens"]
    packs = REFS / "packs.md"
    packs_text = packs.read_text(encoding="utf-8")
    lines.append(f"packs.md\t{len(packs_text)}\t{approx_tokens(packs_text)}")
    catalogs = sorted(REFS.glob("catalog-*.md"))
    worst = ("", 0)
    for c in catalogs:
        t = c.read_text(encoding="utf-8")
        lines.append(f"{c.name}\t{len(t)}\t{approx_tokens(t)}")
        if approx_tokens(t) > worst[1]:
            worst = (c.name, approx_tokens(t))
    lean_worst = approx_tokens(packs_text) + worst[1]
    lines.append("")
    lines.append(f"lean-load worst case (packs.md + {worst[0]}): ~{lean_worst} tokens")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
