#!/usr/bin/env python3
"""Anti-drift check: verify reference catalogs against the official API metadata.

DEV/CI ONLY. Flags catalog methods that do not exist in the official docs (drift /
typos / wrong casing) and catalog methods that the docs mark deprecated (with their
replacement). Reads tools/api_metadata.json produced by extract_api_metadata.py.
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Dict, List, Tuple

# Bare system methods that are documented outside api-reference/ (no per-method page).
SYSTEM_METHODS = {"batch", "methods", "events", "scope"}

ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|")

REFS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "bitrix24-agent" / "references"
DATASET_PATH = pathlib.Path(__file__).resolve().parent / "api_metadata.json"


def parse_catalog_methods(text: str) -> List[str]:
    methods: List[str] = []
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if m:
            methods.append(m.group(1))
    return methods


def verify(catalog_methods: List[str], dataset: Dict[str, Any]) -> Dict[str, Any]:
    unknown: List[str] = []
    deprecated: List[Tuple[str, Any]] = []
    for method in catalog_methods:
        if method in dataset:
            entry = dataset[method]
            if entry.get("deprecated"):
                deprecated.append((method, entry.get("replacement")))
        elif method not in SYSTEM_METHODS:
            unknown.append(method)
    return {"unknown": unknown, "deprecated": deprecated}


def _load_dataset() -> Dict[str, Any]:
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    return {m["method"]: m for m in data}


def main() -> None:
    dataset = _load_dataset()
    all_unknown: List[Tuple[str, str]] = []
    all_deprecated: List[Tuple[str, str, Any]] = []
    for path in sorted(REFS.glob("catalog-*.md")):
        report = verify(parse_catalog_methods(path.read_text(encoding="utf-8")), dataset)
        all_unknown += [(path.name, m) for m in report["unknown"]]
        all_deprecated += [(path.name, m, repl) for m, repl in report["deprecated"]]

    if all_deprecated:
        print("DEPRECATED methods in catalogs (migrate to the replacement):")
        for cat, method, repl in all_deprecated:
            print(f"  [{cat}] {method} -> {repl or '(see docs)'}")
    if all_unknown:
        print("UNKNOWN methods (not found in official docs — typo/casing/nonexistent):")
        for cat, method in all_unknown:
            print(f"  [{cat}] {method}")

    if not all_unknown and not all_deprecated:
        print("All catalog methods exist and are current. ✓")

    # Unknown methods are hard errors (a nonexistent method can never succeed).
    # Deprecated methods are warnings until migrated (Phase 3).
    raise SystemExit(1 if all_unknown else 0)


if __name__ == "__main__":
    main()
