from __future__ import annotations

import json
from pathlib import Path

import pytest

from validate_input import main, validate_input_data


def test_validate_input_reports_sources_and_defaults() -> None:
    value = {
        "requirements": ["支持上传"],
        "coverage_level": "standard",
    }

    report = validate_input_data(value)

    assert report["input_sources"] == ["requirements"]
    assert report["coverage_level"] == "standard"
    assert report["target_xmind_version"] == "modern-json"
    assert value == {"requirements": ["支持上传"], "coverage_level": "standard"}


def test_validate_input_reports_all_present_sources_in_schema_order() -> None:
    report = validate_input_data(
        {
            "screenshots": [{"page_name": "Upload", "image_data": "data"}],
            "page_description": "Upload page",
            "requirements": "Must accept files",
            "flow_description": "Upload then review",
        }
    )

    assert report["input_sources"] == [
        "screenshots",
        "page_description",
        "requirements",
        "flow_description",
    ]


def test_validate_input_rejects_invalid_input() -> None:
    with pytest.raises(ValueError, match="input.schema.json"):
        validate_input_data({"coverage_level": "standard"})


def test_validate_input_cli_supports_human_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "input.json"
    path.write_text(json.dumps({"requirements": ["Upload"]}), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["validate_input.py", str(path)])

    assert main() == 0
    output = capsys.readouterr().out
    assert "OK:" in output
    assert "requirements" in output
    assert "modern-json" in output


def test_validate_input_cli_supports_json_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "input.json"
    path.write_text(json.dumps({"page_description": "Upload"}), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["validate_input.py", str(path), "--json"])

    assert main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["input_sources"] == ["page_description"]
    assert report["target_xmind_version"] == "modern-json"
