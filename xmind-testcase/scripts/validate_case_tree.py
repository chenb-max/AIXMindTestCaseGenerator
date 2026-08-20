#!/usr/bin/env python3
"""Validate and summarize a test case tree JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from case_tree import normalize_case_tree, summarize


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a case tree JSON file.")
    parser.add_argument("case_tree", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    value = json.loads(args.case_tree.read_text(encoding="utf-8"))
    tree = normalize_case_tree(value)
    result = summarize(tree)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(
            f"OK: {args.case_tree} cases={result['total_count']} "
            f"sheets={result['sheet_count']} warnings={len(result['warnings'])}"
        )
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
