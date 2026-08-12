#!/usr/bin/env python3
"""Validate the generated private review corpus and its integrity manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ITEM_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,199}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top level must be an object")
    return value


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    summary = load(root / "summary.json")
    index = load(root / "index.json")
    manifest = load(root / "manifest.json")
    corpus_id = summary.get("corpus", {}).get("id")
    if summary.get("corpus", {}).get("promotionStatus") != "blocked":
        errors.append("summary: promotion status must remain blocked")
    if index.get("corpusId") != corpus_id or manifest.get("corpusId") != corpus_id:
        errors.append("corpus ID differs across summary, index, and manifest")
    items = index.get("items")
    if not isinstance(items, list):
        errors.append("index: items must be a list")
        items = []
    ids: set[str] = set()
    unresolved = 0
    needs_attention = 0
    for position, item in enumerate(items):
        item_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(item_id, str) or not ITEM_ID.fullmatch(item_id):
            errors.append(f"index.items[{position}]: invalid item ID")
            continue
        if item_id in ids:
            errors.append(f"index: duplicate item ID {item_id}")
        ids.add(item_id)
        detail_path = root / "items" / f"{item_id}.json"
        if not detail_path.is_file():
            errors.append(f"index: missing detail {item_id}")
            continue
        detail = load(detail_path)
        if detail.get("id") != item_id or detail.get("corpusId") != corpus_id:
            errors.append(f"detail: inconsistent identity for {item_id}")
        if len(detail.get("unresolved", [])) != item.get("unresolvedCount"):
            errors.append(f"detail: unresolved count differs for {item_id}")
        unresolved += int(item.get("unresolvedCount", 0))
        needs_attention += item.get("machineAssessment") == "needs_attention"

    counts = summary.get("counts", {})
    if len(items) != int(counts.get("entries", 0)) + int(counts.get("passages", 0)):
        errors.append("summary: item counts do not equal index length")
    if unresolved != counts.get("unresolvedItems"):
        errors.append("summary: unresolved count does not equal index")
    if needs_attention != counts.get("needsAttention"):
        errors.append("summary: needs-attention count does not equal index")

    section_ids: set[str] = set()
    section_item_ids: list[str] = []
    for volume in summary.get("volumes", []):
        matching_sections = {
            item.get("sectionId")
            for item in items
            if item.get("volume") == volume.get("number")
        }
        if len(matching_sections) != volume.get("sectionCount"):
            errors.append(
                f"summary: section count differs for volume {volume.get('number')}"
            )
        if sum(item.get("volume") == volume.get("number") for item in items) != volume.get(
            "itemCount"
        ):
            errors.append(
                f"summary: item count differs for volume {volume.get('number')}"
            )
        section_ids.update(value for value in matching_sections if isinstance(value, str))

    for section_id in sorted(section_ids):
        section_path = root / "sections" / f"{section_id}.json"
        if not section_path.is_file():
            errors.append(f"index: missing section {section_id}")
            continue
        section = load(section_path)
        if section.get("id") != section_id or section.get("corpusId") != corpus_id:
            errors.append(f"section: inconsistent identity for {section_id}")
        for item in section.get("items", []):
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                section_item_ids.append(item["id"])

    if sorted(section_item_ids) != sorted(ids):
        errors.append("sections: items do not account for the index exactly once")
    if "khadijah" in json.dumps(summary, ensure_ascii=False).lower():
        errors.append("summary: research cohort must not be reader-facing taxonomy")

    manifest_paths: set[str] = set()
    for record in manifest.get("files", []):
        relative = record.get("path")
        digest = record.get("sha256")
        if not isinstance(relative, str) or relative.startswith(("/", "..")):
            errors.append("manifest: unsafe relative path")
            continue
        if relative in manifest_paths:
            errors.append(f"manifest: duplicate path {relative}")
        manifest_paths.add(relative)
        path = root / relative
        if not path.is_file():
            errors.append(f"manifest: missing file {relative}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if not isinstance(digest, str) or not SHA256.fullmatch(digest) or digest != actual:
            errors.append(f"manifest: hash mismatch {relative}")
        if record.get("bytes") != path.stat().st_size:
            errors.append(f"manifest: byte count mismatch {relative}")
    expected = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*.json")
        if path.name != "manifest.json"
    }
    if manifest_paths != expected:
        errors.append("manifest: file set differs from generated corpus")
    if manifest.get("objectCount") != len(manifest_paths):
        errors.append("manifest: object count differs from file set")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Review corpus integrity and blocked-promotion state are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
