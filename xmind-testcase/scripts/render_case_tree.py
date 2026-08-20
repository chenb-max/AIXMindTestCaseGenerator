#!/usr/bin/env python3
"""Render a case tree as a deterministic plain-text tree."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from case_tree import active_sheets, normalize_case_tree, step_text


def render(tree: dict) -> str:
    normalized = normalize_case_tree(tree)
    lines = [normalized["title"]]
    sheets = active_sheets(normalized)
    for sheet_index, sheet in enumerate(sheets):
        if len(sheets) > 1:
            lines.append(f"├─ Sheet：{sheet['title']}")
            prefix = "│  "
        else:
            prefix = ""
        for scenario_index, scenario in enumerate(sheet["scenarios"]):
            scenario_last = scenario_index == len(sheet["scenarios"]) - 1
            scenario_branch = "└─" if scenario_last else "├─"
            lines.append(f"{prefix}{scenario_branch} {scenario['title']}")
            case_prefix = prefix + ("   " if scenario_last else "│  ")
            for case_index, case in enumerate(scenario["cases"]):
                case_last = case_index == len(scenario["cases"]) - 1
                case_branch = "└─" if case_last else "├─"
                lines.append(f"{case_prefix}{case_branch} {case['id']} {case['title']}")
                detail_prefix = case_prefix + ("   " if case_last else "│  ")
                for step_index, step in enumerate(case["steps"], start=1):
                    lines.append(f"{detail_prefix}├─ 操作步骤 {step_index}：{step_text(step)}")
                lines.append(f"{detail_prefix}└─ 预期结果：{case['expected']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render case tree JSON as text.")
    parser.add_argument("case_tree", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    tree = json.loads(args.case_tree.read_text(encoding="utf-8"))
    args.output.write_text(render(tree), encoding="utf-8", newline="\n")
    print(f"rendered {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
