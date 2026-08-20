#!/usr/bin/env python3
"""Validate structured input JSON and report the selected generation options."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from case_tree import validate_schema


INPUT_SOURCES = ("screenshots", "page_description", "requirements", "flow_description")


def validate_input_data(value: Any) -> dict[str, Any]:
    """Validate *value* and return a non-mutating report with documented defaults."""

    validate_schema(value, "input.schema.json")
    normalized = copy.deepcopy(value)
    report: dict[str, Any] = {
        "input_sources": [name for name in INPUT_SOURCES if name in normalized],
        "coverage_level": normalized.get("coverage_level", "standard"),
        "target_xmind_version": normalized.get("target_xmind_version", "modern-json"),
    }
    for field in ("test_mode", "focus_scenarios", "language", "flow_name", "module_name", "output_path"):
        if field in normalized:
            report[field] = normalized[field]
    if "language" not in report:
        report["language"] = "zh-CN"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate structured XMind testcase input JSON.")
    parser.add_argument("input_json", type=Path)
    parser.add_argument("--json", action="store_true", help="Print machine-readable validation result")
    args = parser.parse_args()
    value = json.loads(args.input_json.read_text(encoding="utf-8"))
    report = validate_input_data(value)
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        sources = ", ".join(report["input_sources"])
        print(
            f"OK: {args.input_json} sources={sources} "
            f"coverage={report['coverage_level']} target={report['target_xmind_version']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
