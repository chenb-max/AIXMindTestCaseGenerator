from __future__ import annotations

import json
import re
from pathlib import Path

from case_tree import normalize_case_tree, summarize, validate_case_tree
from create_xmind import create_xmind
from render_case_tree import render
from validate_xmind import validate_report


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _walk_cases(tree: dict):
    sheets = tree.get("sheets") or [{"title": tree["title"], "scenarios": tree["scenarios"]}]
    for sheet in sheets:
        for scenario in sheet["scenarios"]:
            for case in scenario["cases"]:
                yield case


def test_checked_in_case_tree_has_explicit_provenance_and_priorities() -> None:
    tree = json.loads((EXAMPLES / "case_tree_example.json").read_text(encoding="utf-8"))
    normalized = normalize_case_tree(tree)

    for case in _walk_cases(tree):
        assert case["source"] in {"visible", "described", "inferred"}
        assert case["confidence"] in {"high", "medium", "low"}
        assert case["priority"] in {"P0", "P1", "P2", "P3"}
        if case["source"] == "inferred":
            assert case.get("assumptions")
    assert not summarize(normalized)["warnings"]


def test_multi_sheet_example_exercises_structured_fields() -> None:
    path = EXAMPLES / "multi-sheet-case-tree.json"
    assert path.exists()
    tree = json.loads(path.read_text(encoding="utf-8"))
    validate_case_tree(tree)
    assert len(tree["sheets"]) >= 2
    cases = list(_walk_cases(tree))
    assert any(case.get("preconditions") for case in cases)
    assert any(case.get("test_data") for case in cases)
    assert any(any(isinstance(step, dict) and step.get("expected") for step in case["steps"]) for case in cases)
    assert any(case.get("tags") and case.get("notes") for case in cases)
    assert any(case["source"] == "inferred" and case.get("assumptions") for case in cases)


def test_checked_in_modern_artifacts_match_fresh_generation(tmp_path: Path) -> None:
    tree_path = EXAMPLES / "case_tree_example.json"
    output = tmp_path / "file-upload-flow.xmind"
    summary_path = tmp_path / "file-upload-flow.summary.json"
    generated = create_xmind(tree_path, output, summary_path=summary_path)
    checked_summary = json.loads((EXAMPLES / "file-upload-flow.summary.json").read_text(encoding="utf-8"))

    assert {key: generated[key] for key in generated if key != "xmind_file_path"} == {
        key: checked_summary[key] for key in checked_summary if key != "xmind_file_path"
    }
    assert validate_report(output)["case_count"] == checked_summary["test_case_summary"]["total_count"]
    assert render(json.loads(tree_path.read_text(encoding="utf-8"))) == (
        EXAMPLES / "output_example.xmind.txt"
    ).read_text(encoding="utf-8")


def test_skill_description_has_activation_boundary() -> None:
    skill = (EXAMPLES.parent / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"^description:\s*(.+)$", skill, re.MULTILINE)
    assert match, "SKILL.md frontmatter must contain a description"
    description = match.group(1).strip()
    lowered = description.lower()
    assert description.startswith("Use when")
    assert "xmind" in lowered
    assert "test case" in lowered
    assert "generic mind map" in lowered
    assert len(description) < 500
