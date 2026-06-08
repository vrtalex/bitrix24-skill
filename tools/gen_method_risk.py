#!/usr/bin/env python3
"""Generate the bundled per-method risk map for the client's risk gate.

DEV ONLY. Emits {lowercased_method: 'read'|'write'|'destructive'} from the catalog Risk
column, written next to the client as method_risk.json. This makes the write/destructive
confirmation gates match the curated catalogs exactly (the name regex misses verbs like
defer/setOwner/send). 'batch'/'mixed' are excluded (the client classifies batch by recursion).
"""

from __future__ import annotations

import json
import pathlib
import re

REFS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "bitrix24-agent" / "references"
OUT = pathlib.Path(__file__).resolve().parents[1] / "skills" / "bitrix24-agent" / "scripts" / "method_risk.json"
ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([a-z]+)\s*\|")


def main() -> None:
    risk_map = {}
    for path in sorted(REFS.glob("catalog-*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            m = ROW.match(line)
            if not m:
                continue
            method, risk = m.group(1).lower(), m.group(2)
            if risk in ("read", "write", "destructive"):
                risk_map[method] = risk  # 'mixed' (batch) intentionally excluded
    OUT.write_text(
        json.dumps(risk_map, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(risk_map)} method risks -> {OUT}")


if __name__ == "__main__":
    main()
