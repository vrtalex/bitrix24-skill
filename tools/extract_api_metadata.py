#!/usr/bin/env python3
"""Extract language-neutral API metadata from the official Bitrix24 REST docs.

DEV/CI ONLY — not imported by the runtime skill. Emits, per method, only identifiers
and flags (method id, scope codes, required-parameter names, deprecated flag +
replacement, doc path) — never documentation prose. The output is a *proposal* a human
reviews before it enriches the catalogs or gates CI (see tools/README.md).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
from typing import Any, Dict, List, Optional

H1_RE = re.compile(r"^#\s+(.*)$", re.MULTILINE)
DOTTED_METHOD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+")
SCOPE_LINE_RE = re.compile(r"^>\s*Scope:(.*)$", re.MULTILINE)
BACKTICK_TOKEN_RE = re.compile(r"`([A-Za-z0-9_]+)`")
# Matches the deprecation note on the universal (English) docs at apidocs.bitrix24.com:
# a "DEPRECATED" tag and/or the sentence "The development of this method has been halted."
DEPRECATED_RE = re.compile(r"DEPRECATED|development of this method has been halted", re.IGNORECASE)
LINK_METHOD_RE = re.compile(r"\[([A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+)\]")
# A parameter row: the param name is the FIRST bold cell of a `||`-led table row.
# A trailing '*' inside the bold marks the parameter as required (e.g. **id*** -> required).
PARAM_ROW_RE = re.compile(r"^\|\|\s*\*\*([A-Za-z_][A-Za-z0-9_]*)(\*?)\*\*")

# Column-header / non-parameter words to ignore if they appear in the name position.
HEADER_WORDS = {"Name", "Description", "Type", "Parameter", "Value", "Title"}
EXCLUDED_STEMS = {"index"}


def _first_h1(text: str) -> str:
    m = H1_RE.search(text)
    return m.group(1).strip() if m else ""


def _method_id(h1: str, doc_path: str) -> Optional[str]:
    dotted = DOTTED_METHOD_RE.findall(h1)
    if dotted:
        return dotted[-1]  # method id is conventionally the last token of the H1
    stem = pathlib.PurePosixPath(doc_path).stem
    if stem not in EXCLUDED_STEMS and re.fullmatch(r"[a-z][a-z0-9_]*", stem):
        return stem  # bare single-token system method (e.g. methods, scope, events)
    return None


def _scopes(text: str) -> List[str]:
    m = SCOPE_LINE_RE.search(text)
    if not m:
        return []
    seen: List[str] = []
    for tok in BACKTICK_TOKEN_RE.findall(m.group(1)):
        if tok not in seen:
            seen.append(tok)
    return seen


def _required_params(text: str) -> List[str]:
    # Only the top-level params table: everything before the first level-3 (###) heading,
    # which is where per-field detail tables live.
    cutoff = text.find("\n### ")
    region = text if cutoff == -1 else text[:cutoff]
    required: List[str] = []
    for line in region.splitlines():
        m = PARAM_ROW_RE.match(line)
        if not m:
            continue
        name, marker = m.group(1), m.group(2)
        if name in HEADER_WORDS:
            continue
        if marker == "*" and name not in required:
            required.append(name)
    return required


def _deprecation(text: str) -> tuple[bool, Optional[str]]:
    # Only the method header (before the first level-2 heading) carries a method-level
    # DEPRECATED note. "deprecated" mentioned deeper (in field tables or code examples)
    # refers to a field/SDK detail, not the method itself.
    cutoff = text.find("\n## ")
    header = text if cutoff == -1 else text[:cutoff]
    m = DEPRECATED_RE.search(header)
    if not m:
        return False, None
    link = LINK_METHOD_RE.search(header, m.start())
    return True, (link.group(1) if link else None)


def extract_method(text: str, doc_path: str) -> Optional[Dict[str, Any]]:
    """Return method metadata, or None if the doc is not a single-method reference."""
    h1 = _first_h1(text)
    method = _method_id(h1, doc_path)
    if method is None:
        return None
    scopes = _scopes(text)
    if "." not in method and not scopes:
        # A bare single token only counts as a method if it carries a scope line.
        return None
    deprecated, replacement = _deprecation(text)
    return {
        "method": method,
        "scope": scopes,
        "required": _required_params(text),
        "deprecated": deprecated,
        "replacement": replacement,
        "doc_path": doc_path,
    }


def extract_all(docs_root: pathlib.Path) -> List[Dict[str, Any]]:
    by_method: Dict[str, Dict[str, Any]] = {}
    for path in sorted(docs_root.rglob("*.md")):
        rel = path.relative_to(docs_root).as_posix()
        if "/_includes/" in f"/{rel}" or rel.endswith("/index.md") or rel == "index.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        meta = extract_method(text, rel)
        if meta is not None:
            by_method[meta["method"]] = meta
    return [by_method[k] for k in sorted(by_method)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Bitrix24 API metadata from docs")
    parser.add_argument("--docs", required=True, help="Path to the api-reference docs root")
    parser.add_argument("--out", required=True, help="Output JSON path")
    args = parser.parse_args()

    docs_root = pathlib.Path(args.docs)
    methods = extract_all(docs_root)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(methods, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Extracted {len(methods)} methods -> {out_path}")


if __name__ == "__main__":
    main()
