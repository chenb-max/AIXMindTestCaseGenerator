#!/usr/bin/env python3
"""Create modern, legacy or hybrid XMind files from a test case tree."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from case_tree import (
    active_sheets,
    clean_title,
    normalize_case_tree,
    step_text,
    summarize,
    validate_schema,
)


VERSION = "2.0.0"
CONTENT_NS = "urn:xmind:xmap:xmlns:content:2.0"
MANIFEST_NS = "urn:xmind:xmap:xmlns:manifest:1.0"
META_NS = "urn:xmind:xmap:xmlns:meta:2.0"
STYLE_NS = "urn:xmind:xmap:xmlns:style:2.0"
COMMENTS_NS = "urn:xmind:xmap:xmlns:comments:2.0"
FO_NS = "http://www.w3.org/1999/XSL/Format"
SVG_NS = "http://www.w3.org/2000/svg"
XHTML_NS = "http://www.w3.org/1999/xhtml"
XLINK_NS = "http://www.w3.org/1999/xlink"
SCENARIO_COLORS = {
    "main_flow": "#D9EAD3",
    "interruption": "#FFF2CC",
    "abnormal_navigation": "#F4CCCC",
    "state_consistency": "#CFE2F3",
    "duplicate_submit": "#D9D2E9",
    "basic_function": "#D9EAD3",
    "boundary": "#FCE5CD",
    "invalid_input": "#F4CCCC",
    "field_dependency": "#CFE2F3",
    "stability": "#D9D2E9",
}


def topic_style(topic_id: str, fill: str | None = None, bold: bool = False) -> dict[str, Any] | None:
    properties: dict[str, str] = {}
    if fill:
        properties.update({"fill-pattern": "solid", "svg:fill": fill})
    if bold:
        properties["fo:font-weight"] = "bold"
    if not properties:
        return None
    return {"id": f"style-{topic_id}", "properties": properties}


def topic(
    topic_id: str,
    title: str,
    children: list[dict[str, Any]] | None = None,
    *,
    fill: str | None = None,
    bold: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {"id": topic_id, "class": "topic", "title": clean_title(title)}
    if children:
        result["children"] = {"attached": children}
    style = topic_style(topic_id, fill, bold)
    if style:
        result["style"] = style
    return result


def list_topic(topic_id: str, title: str, values: list[str]) -> dict[str, Any] | None:
    if not values:
        return None
    children = [topic(f"{topic_id}-{index}", value) for index, value in enumerate(values, start=1)]
    return topic(topic_id, title, children, bold=True)


def format_test_data(value: Any) -> str:
    if isinstance(value, dict):
        return f"{value['name']}：{value['value']}"
    return str(value)


def detailed_case_topic(sheet_index: int, scenario_index: int, case_index: int, case: dict[str, Any]) -> dict[str, Any]:
    base = f"s{sheet_index}-case-{scenario_index}-{case_index}"
    children: list[dict[str, Any]] = []
    preconditions = list_topic(f"{base}-preconditions", "前置条件", case.get("preconditions", []))
    if preconditions:
        children.append(preconditions)
    test_data = list_topic(
        f"{base}-data", "测试数据", [format_test_data(value) for value in case.get("test_data", [])]
    )
    if test_data:
        children.append(test_data)

    step_children: list[dict[str, Any]] = []
    for step_index, step in enumerate(case["steps"], start=1):
        expected_children = []
        if isinstance(step, dict) and step.get("expected"):
            expected_children.append(topic(f"{base}-step-{step_index}-expected", f"步骤预期：{step['expected']}"))
        step_children.append(
            topic(f"{base}-step-{step_index}", f"{step_index}. {step_text(step)}", expected_children)
        )
    children.append(topic(f"{base}-steps", "操作步骤", step_children, bold=True))
    children.append(topic(f"{base}-expected", f"预期结果：{case['expected']}", bold=True))

    metadata = [
        f"用例编号：{case['id']}",
        f"优先级：{case.get('priority', 'P2')}",
        f"来源：{case.get('source', 'described')}",
        f"置信度：{case.get('confidence', 'high')}",
    ]
    if case.get("tags"):
        metadata.append(f"标签：{', '.join(case['tags'])}")
    if case.get("notes"):
        metadata.append(f"备注：{case['notes']}")
    metadata_topic = list_topic(f"{base}-metadata", "用例信息", metadata)
    if metadata_topic:
        children.append(metadata_topic)
    assumptions = list_topic(f"{base}-assumptions", "假设", case.get("assumptions", []))
    if assumptions:
        children.append(assumptions)
    return topic(base, f"{case['id']} {case['title']}", children)


def compact_case_topic(sheet_index: int, scenario_index: int, case_index: int, case: dict[str, Any]) -> dict[str, Any]:
    base = f"s{sheet_index}-case-{scenario_index}-{case_index}"
    children = [
        topic(f"{base}-step-{step_index}", f"操作步骤：{step_text(step)}")
        for step_index, step in enumerate(case["steps"], start=1)
    ]
    children.append(topic(f"{base}-expected", f"预期结果：{case['expected']}"))
    return topic(base, f"{case['id']} {case['title']}", children)


def build_content(case_tree: dict[str, Any], *, layout: str | None = None, style: str | None = None) -> list[dict[str, Any]]:
    tree = normalize_case_tree(case_tree)
    return _build_content_from_normalized(tree, layout=layout, style=style)


def _build_content_from_normalized(
    tree: dict[str, Any], *, layout: str | None = None, style: str | None = None
) -> list[dict[str, Any]]:
    layout = layout or tree["layout"]
    style = style or tree["style"]
    content: list[dict[str, Any]] = []
    for sheet_index, sheet in enumerate(active_sheets(tree), start=1):
        scenario_topics: list[dict[str, Any]] = []
        for scenario_index, scenario in enumerate(sheet["scenarios"], start=1):
            builder = detailed_case_topic if layout == "detailed" else compact_case_topic
            case_topics = [
                builder(sheet_index, scenario_index, case_index, case)
                for case_index, case in enumerate(scenario["cases"], start=1)
            ]
            fill = SCENARIO_COLORS.get(scenario.get("key")) if style == "professional" else None
            scenario_topics.append(
                topic(f"s{sheet_index}-scenario-{scenario_index}", scenario["title"], case_topics, fill=fill, bold=True)
            )
        root_id = f"s{sheet_index}-root"
        root = topic(root_id, sheet["title"], scenario_topics, fill="#4F81BD" if style == "professional" else None, bold=True)
        root["structureClass"] = "org.xmind.ui.map.clockwise"
        content.append({
            "id": f"sheet-{sheet_index}",
            "class": "sheet",
            "title": clean_title(sheet["title"]),
            "rootTopic": root,
        })
    return content


def _temporary_path(destination: Path, suffix: str) -> Path:
    handle = tempfile.NamedTemporaryFile(
        prefix=f".{destination.name}.tmp.",
        suffix=suffix,
        dir=destination.parent,
        delete=False,
    )
    handle.close()
    return Path(handle.name)


def _backup_existing(path: Path) -> Path:
    backup = _temporary_path(path, ".bak")
    try:
        shutil.copy2(path, backup)
        return backup
    except OSError:
        try:
            backup.unlink()
        except FileNotFoundError:
            pass
        raise


def _reject_existing(path: Path | None, overwrite: bool) -> None:
    if path is not None and path.exists() and not overwrite:
        raise FileExistsError(f"destination already exists: {path}; use --force to replace it")


def _same_path(first: Path, second: Path) -> bool:
    return os.path.normcase(str(first.resolve())) == os.path.normcase(str(second.resolve()))


def _xml_topic(parent: ET.Element, node: dict[str, Any], timestamp: str) -> None:
    attrs = {"id": node["id"], "timestamp": timestamp}
    if node.get("structureClass"):
        attrs["structure-class"] = node["structureClass"]
    element = ET.SubElement(parent, f"{{{CONTENT_NS}}}topic", attrs)
    ET.SubElement(element, f"{{{CONTENT_NS}}}title").text = node["title"]
    attached = node.get("children", {}).get("attached", [])
    if attached:
        children = ET.SubElement(element, f"{{{CONTENT_NS}}}children")
        topics = ET.SubElement(children, f"{{{CONTENT_NS}}}topics", {"type": "attached"})
        for child in attached:
            _xml_topic(topics, child, timestamp)


def legacy_xml_files(content: list[dict[str, Any]], created: int) -> dict[str, bytes]:
    ET.register_namespace("", CONTENT_NS)
    timestamp = str(created)
    root = ET.Element(f"{{{CONTENT_NS}}}xmap-content", {
        "version": "2.0",
        "timestamp": timestamp,
        "xmlns:fo": FO_NS,
        "xmlns:svg": SVG_NS,
        "xmlns:xhtml": XHTML_NS,
        "xmlns:xlink": XLINK_NS,
    })
    for sheet in content:
        sheet_element = ET.SubElement(root, f"{{{CONTENT_NS}}}sheet", {"id": sheet["id"], "timestamp": timestamp})
        _xml_topic(sheet_element, sheet["rootTopic"], timestamp)
        ET.SubElement(sheet_element, f"{{{CONTENT_NS}}}title").text = sheet["title"]
    content_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    ET.register_namespace("", MANIFEST_NS)
    manifest = ET.Element(f"{{{MANIFEST_NS}}}manifest")
    for name, media in [
        ("content.xml", "text/xml"), ("styles.xml", "text/xml"),
        ("comments.xml", "text/xml"), ("meta.xml", "text/xml"), ("META-INF/", ""),
    ]:
        ET.SubElement(manifest, f"{{{MANIFEST_NS}}}file-entry", {"full-path": name, "media-type": media})

    ET.register_namespace("", META_NS)
    meta = ET.Element(f"{{{META_NS}}}meta")
    ET.SubElement(meta, f"{{{META_NS}}}Creator").text = "xmind-testcase skill"
    ET.SubElement(meta, f"{{{META_NS}}}Create-Date").text = timestamp

    ET.register_namespace("", STYLE_NS)
    styles = ET.Element(f"{{{STYLE_NS}}}xmap-styles", {
        "version": "2.0", "xmlns:fo": FO_NS, "xmlns:svg": SVG_NS,
    })
    styles_xml = ET.tostring(styles, encoding="utf-8", xml_declaration=True)
    ET.register_namespace("", COMMENTS_NS)
    comments = ET.Element(f"{{{COMMENTS_NS}}}comments", {"version": "2.0"})
    return {
        "content.xml": content_xml,
        "META-INF/manifest.xml": ET.tostring(manifest, encoding="utf-8", xml_declaration=True),
        "meta.xml": ET.tostring(meta, encoding="utf-8", xml_declaration=True),
        "styles.xml": styles_xml,
        "comments.xml": ET.tostring(comments, encoding="utf-8", xml_declaration=True),
    }


def create_xmind(
    case_tree_path: Path,
    output_path: Path,
    *,
    target: str | None = None,
    layout: str | None = None,
    summary_path: Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    case_tree_path = Path(case_tree_path)
    output_path = Path(output_path)
    summary_path = Path(summary_path) if summary_path is not None else None
    if summary_path is not None and _same_path(output_path, summary_path):
        raise ValueError("output_path and summary_path resolve to the same path")
    raw_tree = json.loads(case_tree_path.read_text(encoding="utf-8"))
    tree = normalize_case_tree(raw_tree)
    _reject_existing(output_path, overwrite)
    _reject_existing(summary_path, overwrite)
    target = target or tree["target_xmind_version"]
    if target not in {"modern-json", "legacy-xml", "hybrid"}:
        raise ValueError(f"unsupported target_xmind_version: {target}")
    content = _build_content_from_normalized(tree, layout=layout)
    created = int(time.time() * 1000)
    modern_files: dict[str, bytes] = {}
    if target in {"modern-json", "hybrid"}:
        manifest_entries: dict[str, dict[str, Any]] = {"content.json": {}, "metadata.json": {}}
        if target == "hybrid":
            manifest_entries.update({"content.xml": {}, "styles.xml": {}, "meta.xml": {}, "comments.xml": {}})
        modern_files = {
            "content.json": json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8"),
            "manifest.json": json.dumps({"file-entries": manifest_entries}, ensure_ascii=False, indent=2).encode("utf-8"),
            "metadata.json": json.dumps({
                "dataStructureVersion": "2",
                "creator": {"name": "xmind-testcase skill", "version": VERSION},
                "schemaVersion": "1.0",
                "created": created,
            }, ensure_ascii=False, indent=2).encode("utf-8"),
        }
    legacy_files = legacy_xml_files(content, created) if target in {"legacy-xml", "hybrid"} else {}

    from validate_xmind import validate_report
    temporary_xmind: Path | None = None
    temporary_summary: Path | None = None
    backup_xmind: Path | None = None
    backup_summary: Path | None = None
    installed_xmind = False
    installed_summary = False
    committed = False
    rollback_errors: list[tuple[Path, OSError]] = []
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if summary_path is not None:
            summary_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_xmind = _temporary_path(output_path, ".xmind")
        with zipfile.ZipFile(temporary_xmind, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in {**modern_files, **legacy_files}.items():
                archive.writestr(name, data)

        validation = validate_report(temporary_xmind)
        stats = summarize(tree)
        result = {
            "xmind_file_path": str(output_path),
            "target_format": target,
            "test_case_summary": {
                "total_count": stats["total_count"],
                "sheet_count": stats["sheet_count"],
                "scenario_breakdown": stats["scenario_breakdown"],
                "source_breakdown": stats["source_breakdown"],
                "priority_breakdown": stats["priority_breakdown"],
            },
            "warnings": stats["warnings"] + validation.get("warnings", []),
            "assumptions": stats["assumptions"],
            "validation": {"case_tree": "passed", "xmind": "passed"},
        }
        validate_schema(result, "output.schema.json")
        if summary_path:
            temporary_summary = _temporary_path(summary_path, ".json")
            temporary_summary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        # Move old destinations aside only after every new artifact has passed validation.
        # This lets a failure during the second replacement restore the original pair.
        if output_path.exists():
            backup_xmind = _backup_existing(output_path)
        if summary_path is not None and summary_path.exists():
            backup_summary = _backup_existing(summary_path)

        os.replace(temporary_xmind, output_path)
        temporary_xmind = None
        installed_xmind = True
        if summary_path and temporary_summary:
            os.replace(temporary_summary, summary_path)
            temporary_summary = None
            installed_summary = True
        committed = True
        return result
    finally:
        if not committed:
            if installed_summary and summary_path is not None:
                try:
                    summary_path.unlink()
                except FileNotFoundError:
                    pass
            if installed_xmind:
                try:
                    output_path.unlink()
                except FileNotFoundError:
                    pass
            if installed_xmind and backup_xmind is not None and backup_xmind.exists():
                try:
                    if output_path.exists():
                        output_path.unlink()
                    os.replace(backup_xmind, output_path)
                    backup_xmind = None
                except OSError as exc:
                    rollback_errors.append((backup_xmind, exc))
            if installed_summary and backup_summary is not None and backup_summary.exists():
                try:
                    if summary_path is not None and summary_path.exists():
                        summary_path.unlink()
                    if summary_path is not None:
                        os.replace(backup_summary, summary_path)
                        backup_summary = None
                except OSError as exc:
                    rollback_errors.append((backup_summary, exc))
        for temporary in (temporary_xmind, temporary_summary):
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass
        failed_backups = {path for path, _ in rollback_errors}
        for backup in (backup_xmind, backup_summary):
            if backup is not None:
                if backup in failed_backups:
                    continue
                try:
                    backup.unlink()
                except FileNotFoundError:
                    pass
        if rollback_errors:
            names = ", ".join(str(path) for path, _ in rollback_errors)
            raise RuntimeError(f"rollback failed; backup(s) preserved for recovery: {names}") from rollback_errors[0][1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an XMind file from a test case tree JSON file.")
    parser.add_argument("case_tree", type=Path, help="Path to case tree JSON")
    parser.add_argument("output", type=Path, help="Output .xmind path")
    parser.add_argument("--target", choices=["modern-json", "legacy-xml", "hybrid"])
    parser.add_argument("--layout", choices=["compact", "detailed"])
    parser.add_argument("--summary", type=Path, help="Optional JSON summary output path")
    parser.add_argument("--force", action="store_true", help="Replace existing output and summary files")
    args = parser.parse_args()
    if args.output.suffix.lower() != ".xmind":
        parser.error("output path must end with .xmind")
    result = create_xmind(
        args.case_tree,
        args.output,
        target=args.target,
        layout=args.layout,
        summary_path=args.summary,
        overwrite=args.force,
    )
    print(f"created {args.output}")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
