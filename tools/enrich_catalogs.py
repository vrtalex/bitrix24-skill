#!/usr/bin/env python3
"""Enrich reference catalogs with Scope / Required / Deprecated columns from the docs.

DEV ONLY. Idempotent: re-normalizes each catalog table to the canonical 6-column form
(`Method | Risk | Scope | Required | Deprecated | Docs`), looking up scope, required
parameters, and deprecation from tools/api_metadata.json. Only language-neutral
identifiers/flags are written. The result is reviewed by a human before commit.
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Dict, List, Optional

REFS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "bitrix24-agent" / "references"
DATASET_PATH = pathlib.Path(__file__).resolve().parent / "api_metadata.json"

DOC_BASE = "https://github.com/bitrix24/b24restdocs/blob/main/api-reference/"
HEADER = "| Method | Risk | Scope | Required | Deprecated | Docs |"
SEPARATOR = "|---|---|---|---|---|---|"
HEADER_RE = re.compile(r"^\|\s*Method\s*\|\s*Risk\b")
SEPARATOR_RE = re.compile(r"^\|[\s\-:|]+\|\s*$")
ROW_RE = re.compile(r"^\|\s*`[^`]+`\s*\|")


def _cells(line: str) -> List[str]:
    # Split a markdown table row into trimmed cell values (drop the outer empty cells).
    parts = [c.strip() for c in line.split("|")]
    return parts[1:-1] if len(parts) >= 2 else parts


def enrich_row(line: str, dataset: Dict[str, Any]) -> str:
    if not ROW_RE.match(line):
        return line
    cells = _cells(line)
    method = cells[0].strip("`")
    risk = cells[1]
    docs = cells[-1]  # last cell is always the docs URL (works for 3- or 6-column input)
    entry: Optional[Dict[str, Any]] = dataset.get(method)
    if entry:
        scope = ",".join(entry.get("scope") or []) or "-"
        required = ",".join(entry.get("required") or [])
        deprecated = f"→ {entry['replacement']}" if entry.get("deprecated") else ""
        # Regenerate the canonical docs URL from the doc path so stale links are corrected.
        if entry.get("doc_path"):
            docs = DOC_BASE + entry["doc_path"]
    else:
        # Methods absent from the dataset (e.g. batch, lives outside api-reference) keep their URL.
        scope, required, deprecated = "-", "", ""
    return f"| `{method}` | {risk} | {scope} | {required} | {deprecated} | {docs} |"


def enrich_text(text: str, dataset: Dict[str, Any]) -> str:
    out: List[str] = []
    skip_separator = False
    for line in text.splitlines():
        if skip_separator and SEPARATOR_RE.match(line):
            skip_separator = False
            continue
        if HEADER_RE.match(line):
            out.append(HEADER)
            out.append(SEPARATOR)
            skip_separator = True  # drop the original separator line that follows
            continue
        out.append(enrich_row(line, dataset))
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def main() -> None:
    dataset = {m["method"]: m for m in json.loads(DATASET_PATH.read_text(encoding="utf-8"))}
    changed = 0
    for path in sorted(REFS.glob("catalog-*.md")):
        original = path.read_text(encoding="utf-8")
        enriched = enrich_text(original, dataset)
        if enriched != original:
            path.write_text(enriched, encoding="utf-8")
            changed += 1
            print(f"enriched {path.name}")
    print(f"done; {changed} catalog(s) updated")


if __name__ == "__main__":
    main()
