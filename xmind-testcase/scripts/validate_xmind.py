#!/usr/bin/env python3
"""Validate modern JSON, legacy XML and hybrid XMind packages."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from case_tree import validate_schema


MODERN_REQUIRED = {"content.json", "manifest.json", "metadata.json"}
LEGACY_REQUIRED = {"content.xml", "styles.xml", "comments.xml"}
CASE_ID_RE = re.compile(r"^s\d+-case-\d+-\d+$")


def walk_topics(node: dict[str, Any], ids: set[str], counters: dict[str, int]) -> None:
    if not isinstance(node, dict):
        raise ValueError("topic must be an object")
    node_id = node.get("id")
    if not isinstance(node_id, str) or not node_id:
        raise ValueError("topic id is required")
    if node_id in ids:
        raise ValueError(f"duplicate topic id: {node_id}")
    ids.add(node_id)
    topic_class = node.get("class")
    if topic_class is not None and topic_class != "topic":
        raise ValueError(f"invalid topic class for {node_id}: {topic_class}")
    title = node.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"title is required for {node_id}")
    counters["topics"] += 1
    if CASE_ID_RE.fullmatch(node_id):
        counters["cases"] += 1

    children = node.get("children")
    if children is None:
        return
    if not isinstance(children, dict):
        raise ValueError(f"children must be an object for {node_id}")
    attached = children.get("attached", [])
    if not isinstance(attached, list):
        raise ValueError(f"children.attached must be an array for {node_id}")
    for child in attached:
        walk_topics(child, ids, counters)


def validate_modern(archive: zipfile.ZipFile, names: set[str]) -> dict[str, Any]:
    missing = MODERN_REQUIRED - names
    if missing:
        raise ValueError(f"missing modern XMind files: {', '.join(sorted(missing))}")
    content = json.loads(archive.read("content.json").decode("utf-8"))
    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    metadata = json.loads(archive.read("metadata.json").decode("utf-8"))
    validate_schema(content, "xmind.schema.json")

    entries = manifest.get("file-entries")
    if not isinstance(entries, dict):
        raise ValueError("manifest.json file-entries must be an object")
    for required in {"content.json", "metadata.json"}:
        if required not in entries:
            raise ValueError(f"manifest.json does not declare {required}")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("creator"), dict):
        raise ValueError("metadata.json creator must be an object")
    if "schemaVersion" in metadata and not isinstance(metadata["schemaVersion"], str):
        raise ValueError("metadata.json schemaVersion must be a string when present")

    ids: set[str] = set()
    counters = {"sheets": 0, "topics": 0, "cases": 0}
    for sheet in content:
        sheet_id = sheet["id"]
        if sheet_id in ids:
            raise ValueError(f"duplicate sheet/topic id: {sheet_id}")
        ids.add(sheet_id)
        counters["sheets"] += 1
        walk_topics(sheet["rootTopic"], ids, counters)
    return counters


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def validate_legacy(archive: zipfile.ZipFile, names: set[str], path: Path) -> dict[str, Any]:
    missing = LEGACY_REQUIRED - names
    if missing:
        raise ValueError(f"missing legacy XMind files: {', '.join(sorted(missing))}")
    content_root = ET.fromstring(archive.read("content.xml"))
    ET.fromstring(archive.read("styles.xml"))
    ET.fromstring(archive.read("comments.xml"))
    if "META-INF/manifest.xml" in names:
        ET.fromstring(archive.read("META-INF/manifest.xml"))
    if "meta.xml" in names:
        ET.fromstring(archive.read("meta.xml"))

    ids: set[str] = set()
    counters = {"sheets": 0, "topics": 0, "cases": 0}
    for element in content_root.iter():
        name = _local_name(element.tag)
        if name not in {"sheet", "topic"}:
            continue
        node_id = element.get("id")
        if not node_id:
            raise ValueError(f"legacy {name} id is required")
        if node_id in ids:
            raise ValueError(f"duplicate legacy id: {node_id}")
        ids.add(node_id)
        if name == "sheet":
            counters["sheets"] += 1
        else:
            counters["topics"] += 1
            if CASE_ID_RE.fullmatch(node_id):
                counters["cases"] += 1
            title = next((child for child in element if _local_name(child.tag) == "title"), None)
            if title is None or not "".join(title.itertext()).strip():
                raise ValueError(f"legacy topic title is required for {node_id}")
    if not counters["sheets"] or not counters["topics"]:
        raise ValueError("legacy content.xml must contain sheets and topics")

    try:
        import xmind
    except ImportError as exc:
        raise RuntimeError("xmind==1.2.0 is required to validate legacy XML compatibility") from exc
    workbook = xmind.load(str(path))
    sdk_sheets = workbook.getSheets()
    if len(sdk_sheets) != counters["sheets"]:
        raise ValueError("XMind 8 SDK parsed a different sheet count")
    for sheet in sdk_sheets:
        if not sheet.getTitle() or not sheet.getRootTopic().getTitle():
            raise ValueError("XMind 8 SDK could not parse sheet and root topic titles")
    return counters


def validate_report(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".xmind":
        raise ValueError("XMind file path must end with .xmind")
    with zipfile.ZipFile(path) as archive:
        names_list = archive.namelist()
        if len(names_list) != len(set(names_list)):
            raise ValueError("XMind archive contains duplicate file names")
        names = set(names_list)
        has_modern = "content.json" in names
        # Modern XMind exports may retain a compatibility content.xml warning.
        # Treat XML as a legacy representation only when its complete package exists.
        has_legacy = LEGACY_REQUIRED.issubset(names)
        if not has_modern and not has_legacy:
            raise ValueError("XMind archive contains neither modern JSON nor legacy XML content")
        modern = validate_modern(archive, names) if has_modern else None
        legacy = validate_legacy(archive, names, path) if has_legacy else None

    target_format = "hybrid" if modern and legacy else "modern-json" if modern else "legacy-xml"
    primary = modern or legacy or {"sheets": 0, "topics": 0, "cases": 0}
    warnings: list[str] = []
    if modern and legacy and modern != legacy:
        warnings.append("modern and legacy representations have different node counts")
    return {
        "target_format": target_format,
        "sheet_count": primary["sheets"],
        "topic_count": primary["topics"],
        "case_count": primary["cases"],
        "warnings": warnings,
    }


def validate(path: Path) -> int:
    return validate_report(path)["topic_count"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an XMind .xmind file.")
    parser.add_argument("xmind_file", type=Path, help="Path to .xmind file")
    parser.add_argument("--json", action="store_true", help="Print machine-readable validation result")
    args = parser.parse_args()
    report = validate_report(args.xmind_file)
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(
            f"OK: {args.xmind_file} format={report['target_format']} "
            f"sheets={report['sheet_count']} topics={report['topic_count']} cases={report['case_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
