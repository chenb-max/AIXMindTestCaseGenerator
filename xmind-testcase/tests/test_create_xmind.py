from __future__ import annotations

import json
from pathlib import Path

import pytest

import create_xmind as create_module
from create_xmind import create_xmind
from validate_xmind import validate_report


def _case(title: str, suffix: str = "") -> dict:
    return {
        "id": "TC-UPLOAD-002" if suffix else "TC-UPLOAD-001",
        "title": title,
        "source": "described",
        "confidence": "high",
        "priority": "P1",
        "steps": [{"action": "Submit", "expected": "Request accepted"}],
        "expected": "Request accepted",
    }


def _tree(*, target: str = "modern-json", layout: str = "detailed", sheets: int = 1) -> dict:
    result = {
        "title": "Upload",
        "target_xmind_version": target,
        "layout": layout,
        "style": "professional",
        "scenarios": [
            {"key": "main_flow", "title": "Main flow", "cases": [_case("Upload file")]},
        ],
    }
    if sheets > 1:
        result.pop("scenarios")
        result["sheets"] = [
            {"title": "Upload", "scenarios": result["scenarios"] if "scenarios" in result else [
                {"key": "main_flow", "title": "Main flow", "cases": [_case("Upload file")]},
            ]},
            {"title": "Review", "scenarios": [
                {"key": "state_consistency", "title": "State consistency", "cases": [_case("Review file", "-2")]},
            ]},
        ]
    return result


@pytest.fixture
def case_tree_file(tmp_path: Path) -> Path:
    path = tmp_path / "case-tree.json"
    path.write_text(json.dumps(_tree()), encoding="utf-8")
    return path


def test_existing_output_requires_overwrite(tmp_path: Path, case_tree_file: Path) -> None:
    output = tmp_path / "cases.xmind"
    output.write_bytes(b"original")

    with pytest.raises(FileExistsError, match="--force"):
        create_xmind(case_tree_file, output)

    assert output.read_bytes() == b"original"


def test_overwrite_replaces_only_after_validation(tmp_path: Path, case_tree_file: Path) -> None:
    output = tmp_path / "cases.xmind"
    output.write_bytes(b"original")

    result = create_xmind(case_tree_file, output, overwrite=True)

    assert result["validation"] == {"case_tree": "passed", "xmind": "passed"}
    assert validate_report(output)["case_count"] == 1
    assert output.read_bytes() != b"original"


def test_invalid_tree_does_not_create_destination_directory(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text(json.dumps({"title": "Invalid", "scenarios": []}), encoding="utf-8")
    output = tmp_path / "not-created" / "cases.xmind"

    with pytest.raises(ValueError):
        create_xmind(source, output)

    assert not output.parent.exists()


def test_focus_validation_preserves_existing_output(tmp_path: Path) -> None:
    source = tmp_path / "focused.json"
    tree = _tree()
    tree["focus_scenarios"] = ["boundary"]
    source.write_text(json.dumps(tree), encoding="utf-8")
    output = tmp_path / "cases.xmind"
    output.write_bytes(b"original")

    with pytest.raises(ValueError, match="focus_scenarios excludes all"):
        create_xmind(source, output, overwrite=True)

    assert output.read_bytes() == b"original"
    assert not list(tmp_path.glob(".*.tmp.*"))


def test_failed_validation_preserves_existing_output_and_cleans_temp_files(
    tmp_path: Path, case_tree_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "cases.xmind"
    output.write_bytes(b"original")

    def fail_validation(path: Path) -> dict:
        raise ValueError("invalid temporary archive")

    monkeypatch.setattr("validate_xmind.validate_report", fail_validation)
    with pytest.raises(ValueError, match="invalid temporary archive"):
        create_xmind(case_tree_file, output, overwrite=True)

    assert output.read_bytes() == b"original"
    assert not list(tmp_path.glob(".*.tmp.*"))


def test_summary_replace_failure_rolls_back_xmind_and_summary(
    tmp_path: Path, case_tree_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "cases.xmind"
    summary = tmp_path / "cases.summary.json"
    output.write_bytes(b"original xmind")
    summary.write_bytes(b"original summary")
    original_replace = create_module.os.replace

    def fail_summary_replace(source: str | Path, destination: str | Path) -> None:
        if Path(destination).resolve() == summary.resolve() and Path(source).suffix == ".json":
            raise OSError("simulated summary replacement failure")
        original_replace(source, destination)

    monkeypatch.setattr(create_module.os, "replace", fail_summary_replace)
    with pytest.raises(OSError, match="simulated summary replacement failure"):
        create_xmind(case_tree_file, output, summary_path=summary, overwrite=True)

    assert output.read_bytes() == b"original xmind"
    assert summary.read_bytes() == b"original summary"
    assert not list(tmp_path.glob(".*.tmp.*"))


def test_rollback_failure_preserves_recovery_backup(
    tmp_path: Path, case_tree_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "cases.xmind"
    summary = tmp_path / "cases.summary.json"
    output.write_bytes(b"original xmind")
    summary.write_bytes(b"original summary")
    original_replace = create_module.os.replace

    def fail_summary_and_xmind_restore(source: str | Path, destination: str | Path) -> None:
        if Path(destination).resolve() == summary.resolve() and Path(source).suffix == ".json":
            raise OSError("simulated summary replacement failure")
        if Path(destination).resolve() == output.resolve() and Path(source).suffix == ".bak":
            raise OSError("simulated XMind rollback failure")
        original_replace(source, destination)

    monkeypatch.setattr(create_module.os, "replace", fail_summary_and_xmind_restore)
    with pytest.raises(RuntimeError, match="rollback failed.*backup"):
        create_xmind(case_tree_file, output, summary_path=summary, overwrite=True)

    assert summary.read_bytes() == b"original summary"
    assert list(tmp_path.glob(".*cases.xmind.tmp.*.bak"))


def test_summary_requires_overwrite_and_preserves_existing_bytes(
    tmp_path: Path, case_tree_file: Path
) -> None:
    output = tmp_path / "cases.xmind"
    summary = tmp_path / "cases.summary.json"
    summary.write_bytes(b"original summary")

    with pytest.raises(FileExistsError, match="--force"):
        create_xmind(case_tree_file, output, summary_path=summary)

    assert not output.exists()
    assert summary.read_bytes() == b"original summary"


def test_output_and_summary_same_path_are_rejected(tmp_path: Path, case_tree_file: Path) -> None:
    output = tmp_path / "cases.xmind"

    with pytest.raises(ValueError, match="same path"):
        create_xmind(case_tree_file, output, summary_path=output)

    assert not output.exists()


@pytest.mark.parametrize("target", ["modern-json", "legacy-xml", "hybrid"])
@pytest.mark.parametrize("layout", ["compact", "detailed"])
def test_supported_targets_and_layouts(
    tmp_path: Path, target: str, layout: str
) -> None:
    source = tmp_path / f"{target}-{layout}.json"
    source.write_text(json.dumps(_tree(target=target, layout=layout)), encoding="utf-8")
    output = tmp_path / f"{target}-{layout}.xmind"

    result = create_xmind(source, output)

    assert result["target_format"] == target
    assert result["test_case_summary"]["total_count"] == 1
    assert validate_report(output)["target_format"] == target


def test_multi_sheet_summary_and_cleanup(tmp_path: Path) -> None:
    source = tmp_path / "multi.json"
    source.write_text(json.dumps(_tree(sheets=2)), encoding="utf-8")
    output = tmp_path / "multi.xmind"
    summary = tmp_path / "multi.summary.json"

    result = create_xmind(source, output, summary_path=summary)

    assert result["test_case_summary"]["sheet_count"] == 2
    assert result["test_case_summary"]["total_count"] == 2
    assert json.loads(summary.read_text(encoding="utf-8")) == result
    assert not list(tmp_path.glob(".*.tmp.*"))


def test_cli_force_passes_overwrite(monkeypatch: pytest.MonkeyPatch, case_tree_file: Path, tmp_path: Path) -> None:
    output = tmp_path / "cli.xmind"
    calls: list[bool] = []

    def fake_create(*args, **kwargs):
        calls.append(kwargs["overwrite"])
        return {"validation": {"case_tree": "passed", "xmind": "passed"}}

    monkeypatch.setattr(create_module, "create_xmind", fake_create)
    monkeypatch.setattr(
        "sys.argv", ["create_xmind.py", str(case_tree_file), str(output), "--force"]
    )

    assert create_module.main() == 0
    assert calls == [True]
