from __future__ import annotations

import pytest

from case_tree import active_sheets, expected_scenario_keys, normalize_case_tree, summarize, validate_case_tree


def make_tree(*, cases=None, **root_overrides):
    case_list = cases or [
        {
            "title": "Upload a valid file",
            "steps": ["Choose a file", "Submit"],
            "expected": "Upload succeeds",
        }
    ]
    tree = {
        "title": "Upload",
        "module": "UPLOAD",
        "test_mode": "cross_page",
        "scenarios": [{"key": "main_flow", "title": "Main flow", "cases": case_list}],
    }
    tree.update(root_overrides)
    return tree


def test_missing_provenance_defaults_to_inferred_low_with_assumption_and_warning():
    normalized = normalize_case_tree(make_tree())

    case = normalized["sheets"][0]["scenarios"][0]["cases"][0]
    assert case["source"] == "inferred"
    assert case["confidence"] == "low"
    assert case["assumptions"] == ["来源未显式标记，需人工确认。"]

    summary = summarize(normalized)
    assert summary["source_breakdown"] == {"inferred": 1}
    assert any(
        "provenance" in warning
        and "inferred" in warning
        and case["id"] in warning
        and case["title"] in warning
        for warning in summary["warnings"]
    )


def test_explicit_provenance_is_preserved():
    tree = make_tree(
        cases=[
            {
                "title": "Upload a valid file",
                "steps": ["Choose a file", "Submit"],
                "expected": "Upload succeeds",
                "source": "visible",
                "confidence": "high",
                "assumptions": ["Observed in the screenshot"],
            }
        ]
    )

    normalized = normalize_case_tree(tree)
    case = normalized["sheets"][0]["scenarios"][0]["cases"][0]
    assert case["source"] == "visible"
    assert case["confidence"] == "high"
    assert case["assumptions"] == ["Observed in the screenshot"]


def test_missing_source_adds_default_assumption_without_discarding_existing_assumptions():
    tree = make_tree(
        cases=[
            {
                "title": "Upload a valid file",
                "steps": ["Choose a file", "Submit"],
                "expected": "Upload succeeds",
                "assumptions": ["The upload endpoint is available"],
            }
        ]
    )

    normalized = normalize_case_tree(tree)
    assumptions = normalized["sheets"][0]["scenarios"][0]["cases"][0]["assumptions"]
    assert assumptions == ["The upload endpoint is available", "来源未显式标记，需人工确认。"]


def test_explicit_inferred_without_assumptions_fails_schema_validation():
    tree = make_tree(
        cases=[
            {
                "title": "Upload a valid file",
                "steps": ["Choose a file", "Submit"],
                "expected": "Upload succeeds",
                "source": "inferred",
            }
        ]
    )

    with pytest.raises(ValueError, match="assumptions"):
        validate_case_tree(tree)


@pytest.mark.parametrize(
    "field, first, second",
    [
        ("preconditions", ["logged in"], ["admin account"]),
        ("test_data", [{"name": "file", "value": "a.txt"}], [{"name": "file", "value": "b.txt"}]),
        ("steps", [{"action": "Submit", "expected": "Success"}], [{"action": "Submit", "expected": "Error"}]),
    ],
)
def test_duplicate_intent_signature_includes_case_dimensions(field, first, second):
    common = {
        "title": "Different case title",
        "steps": ["Choose a file", "Submit"],
        "expected": "Upload succeeds",
    }
    first_case = {**common, field: first}
    second_case = {**common, field: second}

    normalized = normalize_case_tree(make_tree(cases=[first_case, second_case]))
    assert len(normalized["sheets"][0]["scenarios"][0]["cases"]) == 2


def test_identical_behavior_and_data_is_rejected_as_duplicate_intent():
    first = {
        "title": "First title",
        "preconditions": ["logged in"],
        "test_data": [{"name": "file", "value": "a.txt"}],
        "steps": [{"action": "Choose a file", "expected": "File selected"}, "Submit"],
        "expected": "Upload succeeds",
    }
    second = {
        **first,
        "title": "Second title",
        "test_data": [{"value": "a.txt", "name": "file"}],
    }

    with pytest.raises(ValueError, match="duplicate case intent"):
        validate_case_tree(make_tree(cases=[first, second]))


def test_duplicate_signature_collapses_whitespace_in_all_behavior_fields():
    first = {
        "title": "First title",
        "steps": [
            " Choose   a file ",
            {"action": " Submit  now ", "expected": " Success   shown "},
        ],
        "expected": " Upload   succeeds ",
    }
    second = {
        "title": "Second title",
        "steps": [
            "Choose a file",
            {"action": "Submit now", "expected": "Success shown"},
        ],
        "expected": "Upload succeeds",
    }

    with pytest.raises(ValueError, match="duplicate case intent"):
        validate_case_tree(make_tree(cases=[first, second]))


def test_same_behavior_in_different_scenarios_is_allowed():
    case = {
        "title": "Same behavior in another scenario",
        "steps": ["Choose a file", "Submit"],
        "expected": "Upload succeeds",
    }
    tree = make_tree(cases=[case])
    tree["scenarios"].append({"key": "interruption", "title": "Interruption", "cases": [case.copy()]})

    validate_case_tree(tree)


def test_same_behavior_with_different_final_expected_is_allowed():
    first = {
        "title": "Upload succeeds",
        "steps": ["Choose a file", "Submit"],
        "expected": "Upload succeeds",
    }
    second = {**first, "title": "Upload is rejected", "expected": "Upload is rejected"}

    validate_case_tree(make_tree(cases=[first, second]))


def test_focus_filtering_fails_when_no_active_cases_remain():
    with pytest.raises(ValueError, match="focus_scenarios excludes all available scenarios"):
        normalize_case_tree(make_tree(focus_scenarios=["interruption"]))


def test_missing_focused_category_warns_when_another_focused_category_remains():
    normalized = normalize_case_tree(make_tree(focus_scenarios=["main_flow", "interruption"]))
    summary = summarize(normalized)

    assert summary["total_count"] == 1
    assert any("interruption" in warning for warning in summary["warnings"])


def test_minimal_cross_page_requires_main_flow_and_core_exception_coverage():
    summary = summarize(normalize_case_tree(make_tree(coverage_level="minimal")))
    assert any("interruption" in warning and "abnormal_navigation" in warning for warning in summary["warnings"])

    tree = make_tree(
        coverage_level="minimal",
        cases=[
            {
                "title": "Upload interrupted",
                "steps": ["Cancel upload"],
                "expected": "Upload is cancelled",
            }
        ],
    )
    tree["scenarios"].append(
        {"key": "abnormal_navigation", "title": "Abnormal navigation", "cases": tree["scenarios"][0]["cases"]}
    )
    summary = summarize(normalize_case_tree(tree))
    assert not any("interruption" in warning and "abnormal_navigation" in warning for warning in summary["warnings"])


def test_minimal_cross_page_warns_when_main_flow_is_missing():
    tree = {
        "title": "Upload",
        "test_mode": "cross_page",
        "coverage_level": "minimal",
        "scenarios": [
            {
                "key": "interruption",
                "title": "Interruption",
                "cases": [
                    {"title": "Cancel upload", "steps": ["Cancel"], "expected": "Upload is cancelled"}
                ],
            }
        ],
    }

    summary = summarize(normalize_case_tree(tree))
    assert "coverage scenario missing: main_flow" in summary["warnings"]


def test_minimal_single_page_requires_basic_function_and_boundary_or_invalid_input():
    tree = make_tree(test_mode="single_page", coverage_level="minimal")
    tree["scenarios"][0]["key"] = "basic_function"
    summary = summarize(normalize_case_tree(tree))
    assert any("boundary" in warning and "invalid_input" in warning for warning in summary["warnings"])

    tree["scenarios"].append(
        {"key": "boundary", "title": "Boundary", "cases": tree["scenarios"][0]["cases"]}
    )
    summary = summarize(normalize_case_tree(tree))
    assert not any("boundary" in warning and "invalid_input" in warning for warning in summary["warnings"])


def test_minimal_single_page_warns_when_basic_function_is_missing():
    tree = {
        "title": "Upload",
        "test_mode": "single_page",
        "coverage_level": "minimal",
        "scenarios": [
            {
                "key": "boundary",
                "title": "Boundary",
                "cases": [
                    {"title": "Empty file", "steps": ["Submit"], "expected": "Validation is shown"}
                ],
            }
        ],
    }

    summary = summarize(normalize_case_tree(tree))
    assert "coverage scenario missing: basic_function" in summary["warnings"]


def test_focus_only_changes_standard_expected_scenarios():
    cross_tree = make_tree(
        coverage_level="minimal",
        focus_scenarios=["interruption"],
        cases=[
            {"title": "Main flow", "steps": ["Submit"], "expected": "Success"},
        ],
    )
    cross_tree["scenarios"].append(
        {
            "key": "interruption",
            "title": "Interruption",
            "cases": [{"title": "Cancel", "steps": ["Cancel"], "expected": "Cancelled"}],
        }
    )
    minimal_cross_summary = summarize(normalize_case_tree(cross_tree))
    assert "coverage scenario missing: main_flow" in minimal_cross_summary["warnings"]

    full_tree = make_tree(coverage_level="full", focus_scenarios=["main_flow"])
    full_summary = summarize(normalize_case_tree(full_tree))
    assert "coverage scenario missing: interruption" in full_summary["warnings"]


def test_focus_only_changes_standard_single_page_expected_scenarios():
    tree = make_tree(
        test_mode="single_page",
        coverage_level="minimal",
        focus_scenarios=["boundary"],
    )
    tree["scenarios"][0]["key"] = "basic_function"
    tree["scenarios"].append(
        {
            "key": "boundary",
            "title": "Boundary",
            "cases": [{"title": "Boundary", "steps": ["Submit"], "expected": "Validation"}],
        }
    )
    summary = summarize(normalize_case_tree(tree))
    assert "coverage scenario missing: basic_function" in summary["warnings"]


@pytest.mark.parametrize("field", ["preconditions", "test_data", "assumptions", "tags"])
@pytest.mark.parametrize("malformed", [None, "not-an-array"])
def test_malformed_optional_arrays_raise_path_specific_value_error(field, malformed):
    tree = make_tree(
        cases=[
            {
                "title": "Malformed optional field",
                "steps": ["Submit"],
                "expected": "Success",
                field: malformed,
            }
        ]
    )

    with pytest.raises(ValueError, match=field) as error:
        validate_case_tree(tree)
    assert field in str(error.value)


def test_active_sheets_strip_internal_normalization_metadata():
    normalized = normalize_case_tree(make_tree())
    active = active_sheets(normalized)
    scenario = active[0]["scenarios"][0]
    case = scenario["cases"][0]

    assert "_excluded" not in scenario
    assert "_provenance_defaulted" not in case


def test_full_coverage_warns_that_branch_completeness_requires_manual_review():
    summary = summarize(normalize_case_tree(make_tree(coverage_level="full")))
    assert any("branch completeness" in warning and "manual review" in warning for warning in summary["warnings"])


def test_standard_behavior_still_reports_missing_scenarios():
    summary = summarize(normalize_case_tree(make_tree(coverage_level="standard")))
    assert any("interruption" in warning for warning in summary["warnings"])
    assert any("duplicate_submit" in warning for warning in summary["warnings"])


def test_standard_cross_page_expected_scenario_set_is_exact():
    tree = make_tree(coverage_level="standard")
    normalized = normalize_case_tree(tree)

    assert expected_scenario_keys(normalized) == {
        "main_flow",
        "interruption",
        "abnormal_navigation",
        "state_consistency",
        "duplicate_submit",
    }


def test_standard_single_page_expected_scenario_set_is_exact():
    tree = make_tree(test_mode="single_page", coverage_level="standard")
    tree["scenarios"][0]["key"] = "basic_function"
    normalized = normalize_case_tree(tree)

    assert expected_scenario_keys(normalized) == {
        "basic_function",
        "boundary",
        "invalid_input",
        "field_dependency",
    }
