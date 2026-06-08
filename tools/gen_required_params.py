#!/usr/bin/env python3
"""Generate the bundled required-params map for the runtime client's --preflight check.

DEV ONLY. Emits a compact {method: [required...]} map covering only the *catalog* methods
that have required parameters, written next to the client as required_params.json. Kept
small on purpose (the head); the discovered long tail simply isn't pre-flighted.
"""

from __future__ import annotations

import json
import pathlib

import verify_catalogs as vc

DATASET_PATH = pathlib.Path(__file__).resolve().parent / "api_metadata.json"
OUT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "skills" / "bitrix24-agent" / "scripts" / "required_params.json"
)


def main() -> None:
    dataset = {m["method"]: m for m in json.loads(DATASET_PATH.read_text(encoding="utf-8"))}
    catalog_methods = set()
    for path in sorted(vc.REFS.glob("catalog-*.md")):
        catalog_methods.update(vc.parse_catalog_methods(path.read_text(encoding="utf-8")))

    req_map = {}
    for method in sorted(catalog_methods):
        entry = dataset.get(method)
        if entry and entry.get("required"):
            req_map[method] = entry["required"]

    OUT_PATH.write_text(
        json.dumps(req_map, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(req_map)} methods with required params -> {OUT_PATH}")


if __name__ == "__main__":
    main()
