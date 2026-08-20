#!/usr/bin/env python3
"""Shared validation, normalization, coverage and summary helpers."""

from __future__ import annotations

import copy
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


PLACEHOLDER_RE = re.compile(r"(?:\.\.\.|待补充|此处省略|TODO|TBD)", re.IGNORECASE)
SCENARIO_KEYS = {
    "main_flow", "interruption", "abnormal_navigation", "state_consistency",
    "duplicate_submit", "basic_function", "boundary", "invalid_input",
    "field_dependency", "stability",
}
SCENARIO_ALIASES = {
    "主流程": "main_flow", "流程中断": "interruption", "页面跳转异常": "abnormal_navigation",
    "异常跳转": "abnormal_navigation", "状态与数据一致性": "state_consistency",
    "重复提交并发防重": "duplicate_submit", "重复提交": "duplicate_submit",
    "基本功能": "basic_function", "边界值": "boundary", "异常输入": "invalid_input",
    "字段关联": "field_dependency", "字段依赖": "field_dependency", "稳定性": "stability",
}
CROSS_PAGE_KEYS = {"main_flow", "interruption", "abnormal_navigation", "state_consistency", "duplicate_submit"}
SINGLE_PAGE_KEYS = {"basic_function", "boundary", "invalid_input", "field_dependency", "stability"}
STANDARD_CROSS = CROSS_PAGE_KEYS
STANDARD_SINGLE = SINGLE_PAGE_KEYS - {"stability"}
DEFAULT_PROVENANCE_ASSUMPTION = "来源未显式标记，需人工确认。"
OPTIONAL_ARRAY_FIELDS = ("preconditions", "test_data", "assumptions", "tags")


def schema_path(name: str) -> Path:
    script_root = Path(__file__).resolve().parents[1]
    candidates = [script_root / "schema" / name, script_root / "references" / "schema" / name]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"schema not found: {name}")


def validate_schema(value: Any, name: str) -> None:
    try:
        from jsonschema import Draft7Validator
    except ImportError as exc:
        raise RuntimeError("jsonschema is required; install requirements.txt") from exc

    schema = json.loads(schema_path(name).read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if errors:
        error = errors[0]
        location = "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.path)
        raise ValueError(f"{name}{location}: {error.message}")


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    return value


def require_non_empty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value


def require_non_empty_array(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{path} must be a non-empty array")
    return value


def _signature_text(value: Any) -> str:
    return " ".join(str(value).split())


def clean_title(value: Any) -> str:
    title = str(value).replace("\x00", "").strip()
    title = " ".join(title.split())
    if not title:
        raise ValueError("topic title cannot be empty")
    if PLACEHOLDER_RE.search(title):
        raise ValueError(f"title contains placeholder content: {title}")
    return title


def scenario_key(scenario: dict[str, Any]) -> str | None:
    if scenario.get("key") in SCENARIO_KEYS:
        return scenario["key"]
    title = str(scenario.get("title", ""))
    for alias, key in SCENARIO_ALIASES.items():
        if alias in title:
            return key
    return None


def _manual_validate(tree: Any) -> dict[str, Any]:
    root = require_object(tree, "case_tree")
    require_non_empty_string(root.get("title"), "title")
    if "scenarios" in root:
        sheets = [{"title": root["title"], "scenarios": root["scenarios"]}]
    elif "sheets" in root:
        sheets = require_non_empty_array(root.get("sheets"), "sheets")
    else:
        raise ValueError("case_tree must contain scenarios or sheets")

    seen_ids: set[str] = set()
    seen_signatures: set[tuple[Any, ...]] = set()
    for sheet_index, sheet in enumerate(sheets):
        sheet_path = f"sheets[{sheet_index}]"
        if not isinstance(sheet, dict):
            raise ValueError(f"{sheet_path} must be an object")
        require_non_empty_string(sheet.get("title"), f"{sheet_path}.title")
        scenarios = require_non_empty_array(sheet.get("scenarios"), f"{sheet_path}.scenarios")
        for scenario_index, scenario in enumerate(scenarios):
            scenario_path = f"{sheet_path}.scenarios[{scenario_index}]"
            scenario = require_object(scenario, scenario_path)
            require_non_empty_string(scenario.get("title"), f"{scenario_path}.title")
            cases = require_non_empty_array(scenario.get("cases"), f"{scenario_path}.cases")
            for case_index, case in enumerate(cases):
                case_path = f"{scenario_path}.cases[{case_index}]"
                case = require_object(case, case_path)
                require_non_empty_string(case.get("title"), f"{case_path}.title")
                for field in OPTIONAL_ARRAY_FIELDS:
                    if field in case and not isinstance(case[field], list):
                        raise ValueError(f"{case_path}.{field} must be an array")
                steps = require_non_empty_array(case.get("steps"), f"{case_path}.steps")
                normalized_steps: list[str] = []
                for step_index, step in enumerate(steps):
                    if isinstance(step, str):
                        normalized_steps.append(require_non_empty_string(step, f"{case_path}.steps[{step_index}]"))
                    elif isinstance(step, dict):
                        normalized_steps.append(require_non_empty_string(step.get("action"), f"{case_path}.steps[{step_index}].action"))
                    else:
                        raise ValueError(f"{case_path}.steps[{step_index}] must be a string or object")
                expected = require_non_empty_string(case.get("expected"), f"{case_path}.expected")
                if PLACEHOLDER_RE.search(case["title"]) or any(PLACEHOLDER_RE.search(s) for s in normalized_steps) or PLACEHOLDER_RE.search(expected):
                    raise ValueError(f"{case_path} contains placeholder content")
                case_id = case.get("id")
                if case_id:
                    if case_id in seen_ids:
                        raise ValueError(f"duplicate case id: {case_id}")
                    seen_ids.add(case_id)
                scenario_identity = scenario_key(scenario) or " ".join(str(scenario["title"]).split())
                normalized_preconditions = tuple(_signature_text(value) for value in case.get("preconditions", []))
                stable_test_data = json.dumps(
                    case.get("test_data", []), ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                stable_steps = tuple(
                    _signature_text(step)
                    if isinstance(step, str)
                    else json.dumps(
                        {
                            **step,
                            "action": _signature_text(step.get("action")),
                            **(
                                {"expected": _signature_text(step["expected"])}
                                if "expected" in step
                                else {}
                            ),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    for step in steps
                )
                signature = (
                    scenario_identity,
                    normalized_preconditions,
                    stable_test_data,
                    stable_steps,
                    _signature_text(expected),
                )
                if signature in seen_signatures:
                    raise ValueError(f"duplicate case intent: {case_path}")
                seen_signatures.add(signature)
    return root


def validate_case_tree(tree: Any) -> dict[str, Any]:
    root = _manual_validate(tree)
    validate_schema(root, "case_tree.schema.json")
    return root


def _module_name(tree: dict[str, Any]) -> str:
    raw = str(tree.get("module") or tree.get("title") or "CASE")
    value = re.sub(r"[^A-Za-z0-9]+", "-", raw).strip("-").upper()
    return value or "CASE"


def normalize_case_tree(tree: dict[str, Any]) -> dict[str, Any]:
    validate_case_tree(tree)
    result = copy.deepcopy(tree)
    if "sheets" not in result:
        result["sheets"] = [{"title": result["title"], "scenarios": result.pop("scenarios")}]
    result.setdefault("coverage_level", "standard")
    result.setdefault("layout", "detailed")
    result.setdefault("style", "professional")
    result.setdefault("target_xmind_version", "modern-json")
    module = _module_name(result)
    focus = set(result.get("focus_scenarios", []))
    case_counter = 1
    for sheet in result["sheets"]:
        for scenario in sheet["scenarios"]:
            scenario["key"] = scenario_key(scenario)
            if focus and scenario["key"] not in focus:
                scenario["_excluded"] = True
                continue
            scenario["_excluded"] = False
            for case in scenario["cases"]:
                case.setdefault("id", f"TC-{module}-{case_counter:03d}")
                if "source" not in case:
                    case["source"] = "inferred"
                    case["confidence"] = "low"
                    assumptions = list(case.get("assumptions", []))
                    if DEFAULT_PROVENANCE_ASSUMPTION not in assumptions:
                        assumptions.append(DEFAULT_PROVENANCE_ASSUMPTION)
                    case["assumptions"] = assumptions
                    case["_provenance_defaulted"] = True
                else:
                    case.setdefault("confidence", "high" if case["source"] != "inferred" else "medium")
                case.setdefault("preconditions", [])
                case.setdefault("test_data", [])
                case.setdefault("tags", [])
                case.setdefault("assumptions", [])
                case_counter += 1
    if focus and not any(
        not scenario.get("_excluded") and scenario.get("cases")
        for sheet in result["sheets"]
        for scenario in sheet["scenarios"]
    ):
        raise ValueError("focus_scenarios excludes all available scenarios")
    return result


def active_sheets(tree: dict[str, Any]) -> list[dict[str, Any]]:
    return _strip_internal_metadata(_active_sheets_internal(tree))


def _active_sheets_internal(tree: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {**sheet, "scenarios": [s for s in sheet["scenarios"] if not s.get("_excluded")]}
        for sheet in tree["sheets"]
    ]


def _strip_internal_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_internal_metadata(item)
            for key, item in value.items()
            if not key.startswith("_")
        }
    if isinstance(value, list):
        return [_strip_internal_metadata(item) for item in value]
    return value


def expected_scenario_keys(tree: dict[str, Any]) -> set[str]:
    mode = tree.get("test_mode")
    if not mode:
        keys = {scenario_key(s) for sheet in tree["sheets"] for s in sheet["scenarios"]}
        mode = "cross_page" if keys & CROSS_PAGE_KEYS else "single_page"
    coverage_level = tree.get("coverage_level", "standard")
    if coverage_level == "minimal":
        expected = {"main_flow" if mode == "cross_page" else "basic_function"}
    elif coverage_level == "full":
        expected = set(CROSS_PAGE_KEYS if mode == "cross_page" else SINGLE_PAGE_KEYS)
    elif tree.get("focus_scenarios"):
        expected = set(tree["focus_scenarios"])
    elif mode == "cross_page":
        expected = set(STANDARD_CROSS)
    else:
        expected = set(STANDARD_SINGLE)
    return expected


def summarize(tree: dict[str, Any]) -> dict[str, Any]:
    internal_sheets = _active_sheets_internal(tree)
    scenarios = [s for sheet in internal_sheets for s in sheet["scenarios"]]
    cases = [case for scenario in scenarios for case in scenario["cases"]]
    scenario_counts = Counter(s.get("title", "未命名场景") for s in scenarios for _ in s["cases"])
    source_counts = Counter(case.get("source", "described") for case in cases)
    priority_counts = Counter(case.get("priority", "P2") for case in cases)
    present_keys = {scenario_key(s) for s in scenarios}
    missing = sorted(expected_scenario_keys(tree) - present_keys)
    warnings = [f"coverage scenario missing: {key}" for key in missing]
    mode = tree.get("test_mode")
    if not mode:
        mode = "cross_page" if present_keys & CROSS_PAGE_KEYS else "single_page"
    coverage_level = tree.get("coverage_level", "standard")
    if coverage_level == "minimal" and mode == "cross_page":
        if not present_keys & {"interruption", "abnormal_navigation"}:
            warnings.append(
                "minimal cross_page requires main_flow and at least one of interruption or abnormal_navigation"
            )
    elif coverage_level == "minimal" and mode == "single_page":
        if not present_keys & {"boundary", "invalid_input"}:
            warnings.append(
                "minimal single_page requires basic_function and at least one of boundary or invalid_input"
            )
    elif coverage_level == "full":
        warnings.append("full coverage branch completeness requires manual review")
    defaulted_cases = [case for case in cases if case.get("_provenance_defaulted")]
    if defaulted_cases:
        details = ", ".join(f"{case.get('id', '<unassigned>')} ({case['title']})" for case in defaulted_cases)
        warnings.append(
            f"provenance defaulted for {len(defaulted_cases)} case(s): {details}; "
            "source inferred with low confidence; manual confirmation required"
        )
    assumptions = [a for case in cases for a in case.get("assumptions", [])]
    return {
        "total_count": len(cases),
        "sheet_count": len(internal_sheets),
        "scenario_breakdown": dict(scenario_counts),
        "source_breakdown": dict(source_counts),
        "priority_breakdown": dict(priority_counts),
        "warnings": warnings,
        "assumptions": sorted(set(assumptions)),
    }


def step_text(step: Any) -> str:
    return step if isinstance(step, str) else str(step["action"])
