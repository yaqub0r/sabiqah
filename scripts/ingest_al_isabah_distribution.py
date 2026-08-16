#!/usr/bin/env python3
"""Ingest an Al-Isabah distribution into Sabiqah's immutable reader corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from rebuild_al_isabah_public_corpus import (
    normalize_search_text,
    render_arabic_poetry,
)
from verify_al_isabah_distribution import CompatibilityError, verify_distribution


ROOT = Path(__file__).resolve().parents[1]
HONORIFIC_REGISTRY = (
    ROOT / "packages" / "release-model" / "src" / "honorifics.registry.json"
)
SCHEMA_VERSION = "4.0.0"


class IngestionError(RuntimeError):
    """Raised when an upstream distribution cannot safely advance the corpus."""


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IngestionError(f"{path}: top level must be an object")
    return value


def registry_indexes() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    registry = load(HONORIFIC_REGISTRY)
    by_character = {}
    by_expanded = {}
    for entry in registry["entries"]:
        character = entry.get("compactCharacter")
        if character:
            by_character[character] = entry
        by_expanded[entry["expandedArabic"]] = entry
        for alias in entry.get("arabicAliases", []):
            by_expanded[alias] = entry
    return by_character, by_expanded


def matched_formula(
    formula: dict[str, Any],
    by_character: dict[str, dict[str, Any]],
    by_expanded: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    target = str(formula.get("targetRealization", ""))
    return by_character.get(target) or by_expanded.get(
        str(formula.get("expandedArabic", ""))
    )


def compact_arabic(
    value: str,
    formulas: Iterable[dict[str, Any]],
    by_character: dict[str, dict[str, Any]],
    by_expanded: dict[str, dict[str, Any]],
) -> str:
    result = value
    for formula in formulas:
        registry = matched_formula(formula, by_character, by_expanded)
        if registry is None or registry.get("fontSupport") != "supported":
            continue
        observed = str(formula.get("observedArabic", ""))
        if observed:
            result = result.replace(observed, registry["compactCharacter"])
    return render_arabic_poetry(result)


def normalize_english_presentation(
    value: str, by_character: dict[str, dict[str, Any]]
) -> str:
    supported = [
        character
        for character, entry in by_character.items()
        if entry.get("fontSupport") == "supported"
    ]
    if not supported:
        return value
    glyphs = "|".join(re.escape(character) for character in sorted(supported))
    value = re.sub(rf",\s*({glyphs})", r" \1", value)
    return re.sub(rf"—\s*({glyphs})\s*—", r" \1 ", value)


def honorifics_for(
    formulas: Iterable[dict[str, Any]],
    segment_id: str,
    by_character: dict[str, dict[str, Any]],
    by_expanded: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    for formula in formulas:
        registry = matched_formula(formula, by_character, by_expanded)
        if registry is None:
            continue
        base = {
            "semanticId": registry["id"],
            "semanticClass": registry["semanticClass"],
            "field": "segment",
            "segmentId": segment_id,
            "renderedForm": registry.get("compactCharacter")
            if registry.get("fontSupport") == "supported"
            else registry["expandedArabic"],
            "expandedArabic": formula["expandedArabic"],
            "accessibleText": formula["accessibleEnglish"],
            "formulaRole": "formulaic",
            "referent": {
                "kind": registry["referent"]["kind"],
                "scope": formula.get("referentScope") or registry["referent"]["scope"],
                "context": "",
                "status": "machine-inferred",
            },
            "agreement": registry["agreement"],
            "familyIncluded": registry["familyIncluded"],
        }
        result.append(
            {
                **base,
                "id": f"{formula['formulaId']}-ar",
                "language": "ar",
                "observedForm": formula["observedArabic"],
            }
        )
        result.append(
            {
                **base,
                "id": f"{formula['formulaId']}-en",
                "language": "en",
                "observedForm": formula["targetRealization"],
            }
        )
    return result


def page_objects(pages: Iterable[dict[str, int]], source_url: str) -> list[dict[str, Any]]:
    return [
        {
            "volume": int(page["volume"]),
            "printedPage": int(page["page"]),
            "readerPage": None,
            "providerPage": source_url,
        }
        for page in pages
    ]


def workflow_stages(record: dict[str, Any]) -> list[dict[str, Any]]:
    state = "complete" if record["machineAssessment"] == "passed" else "needs_attention"
    return [
        {"stage": "source_alignment", "state": "complete", "summary": "Bound to the exact approved source unit."},
        {"stage": "blind_translation", "state": "complete", "summary": "Blind translation completed in Al-Isabah."},
        {"stage": "critique", "state": "complete", "summary": "Independent critique completed in Al-Isabah."},
        {"stage": "adjudication", "state": "complete", "summary": "Adjudicated public-working English is present."},
        {"stage": "machine_validation", "state": state, "summary": "Validated by the repository-owned distribution contract."},
        {"stage": "human_review", "state": "pending", "summary": "Human scholarly review remains separate."},
    ]


def source_url(source: dict[str, Any], binding: dict[str, Any]) -> str:
    return f"{binding['sourceRepository']}/blob/{binding['sourceCommit']}/{binding['sourcePath']}"


def source_metadata(
    source: dict[str, Any], entry_number: int, display_arabic: str, title_score: float,
    binding: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    display_hash = digest_bytes(" ".join(display_arabic.split()).encode("utf-8"))
    metadata = {
        "authorityId": binding["sourceAuthorityId"],
        "producerAuthorityId": binding["producerAuthorityId"],
        "entryNumber": entry_number,
        "pages": [],
        "sourceTextSha256": display_hash,
        "sourceExactTextSha256": source["exactTextSha256"],
        "sourceUrl": source_url(source, binding),
        "license": binding["sourceLicense"],
        "attribution": binding["sourceAttribution"],
        "englishRights": {
            "license": binding["englishLicense"],
            "attribution": binding["englishAttribution"],
        },
        "rightsMatrix": binding["rightsMatrix"],
        "alignment": {
            "method": "al-isabah-public-distribution-v2",
            "titleScore": title_score,
            "bodyScore": 1.0,
        },
    }
    provenance = {
        "sourceAuthorityId": binding["sourceAuthorityId"],
        "producerAuthorityId": binding["producerAuthorityId"],
        "sourceArtifactSha256": source["artifactSha256"],
        "sourceTextSha256": display_hash,
        "sourceExactTextSha256": source["exactTextSha256"],
    }
    return metadata, provenance


def unresolved(values: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "category": str(value.get("category") or "other"),
            "explanation": str(value.get("explanation") or "Unresolved finding."),
            "priority": str(value.get("priority") or "review"),
        }
        for value in values
    ]


def direct_item(
    record: dict[str, Any],
    corpus_id: str,
    by_character: dict[str, dict[str, Any]],
    by_expanded: dict[str, dict[str, Any]],
    binding: dict[str, Any],
) -> list[dict[str, Any]]:
    formulas_by_record: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for formula in record.get("formulas", []):
        formulas_by_record[formula["recordId"]].append(formula)
    result = []
    first_page = record.get("pages", [{}])[0].get("page") if record.get("pages") else None
    preceding = record.get("precedingMaterial", [])
    for offset, passage in enumerate(preceding):
        formulas = formulas_by_record.get(passage["id"], [])
        segment_id = f"{passage['id']}-body"
        arabic = compact_arabic(passage["arabic"], formulas, by_character, by_expanded)
        english = normalize_english_presentation(passage["english"], by_character)
        heading = passage.get("heading", {})
        title_ar = heading.get("arabic") or "نص تمهيدي"
        title_en = heading.get("english") or (
            "Front matter" if passage["kind"] == "front_matter" else "Structural passage"
        )
        display_arabic = " ".join((title_ar, arabic)).strip()
        source, provenance = source_metadata(
            {**record["source"], "exactTextSha256": passage["sourceSha256"]},
            record["printedEntryNumber"],
            display_arabic,
            1.0 if heading.get("arabic") and heading.get("english") else 0.5,
            binding,
        )
        source["pages"] = [
            f"V{page['volume']:02d}P{page['page']:03d}" for page in passage.get("pages", [])
        ]
        result.append(
            {
                "schemaVersion": SCHEMA_VERSION,
                "corpusId": corpus_id,
                "id": passage["id"],
                "kind": "passage",
                "sequence": record["sourceOrdinal"] * 100 - len(preceding) + offset,
                "printedEntryNumber": None,
                "sourceEntryNumber": record["printedEntryNumber"],
                "volume": record["volume"],
                "title": {
                    "en": normalize_english_presentation(title_en, by_character),
                    "ar": title_ar,
                },
                "relationship": f"Source structure before entry {record['printedEntryNumber']}",
                "translationState": "translated",
                "machineAssessment": "needs_attention" if passage["unresolved"] else "passed",
                "humanReview": passage["humanReview"],
                "publicEligibility": "eligible",
                "segments": [{
                    "id": segment_id,
                    "arabic": arabic,
                    "english": english,
                    "pages": page_objects(passage.get("pages", []), source_url(record["source"], binding)),
                    "machineState": "translated",
                }],
                "names": [],
                "unresolved": unresolved(passage["unresolved"]),
                "honorificPolicyVersion": "1.0.0",
                "honorifics": honorifics_for(formulas, segment_id, by_character, by_expanded),
                "workflowStages": workflow_stages(record),
                "source": source,
                "provenance": provenance,
                "_navigationPage": first_page,
            }
        )
    formulas = formulas_by_record.get(record["id"], [])
    segment_id = f"{record['id']}-body"
    arabic_title = compact_arabic(record["title"]["arabic"], formulas, by_character, by_expanded)
    arabic_body = compact_arabic(record["arabic"], formulas, by_character, by_expanded)
    display_arabic = " ".join((arabic_title, arabic_body)).strip()
    source, provenance = source_metadata(
        record["source"],
        record["printedEntryNumber"],
        display_arabic,
        1.0 if record["title"]["state"] == "ready" else 0.5,
        binding,
    )
    source["pages"] = [
        f"V{page['volume']:02d}P{page['page']:03d}" for page in record.get("pages", [])
    ]
    result.append(
        {
            "schemaVersion": SCHEMA_VERSION,
            "corpusId": corpus_id,
            "id": record["id"],
            "kind": "entry",
            "sequence": record["sourceOrdinal"] * 100,
            "printedEntryNumber": record["printedEntryNumber"],
            "sourceEntryNumber": record["printedEntryNumber"],
            "volume": record["volume"],
            "title": {
                "en": normalize_english_presentation(
                    record["title"]["english"], by_character
                ),
                "ar": arabic_title,
            },
            "translationState": "translated",
            "machineAssessment": record["machineAssessment"],
            "humanReview": record["humanReview"],
            "publicEligibility": "eligible",
            "segments": [{
                "id": segment_id,
                "arabic": arabic_body,
                "english": normalize_english_presentation(
                    record["english"], by_character
                ),
                "pages": page_objects(record.get("pages", []), source_url(record["source"], binding)),
                "machineState": "translated",
            }],
            "names": [
                {"arabic": name["arabic"], "english": name["english"], "kind": name["kind"]}
                for name in record.get("names", [])
            ],
            "unresolved": unresolved(record.get("unresolved", [])),
            "honorificPolicyVersion": "1.0.0",
            "honorifics": honorifics_for(formulas, segment_id, by_character, by_expanded),
            "decisions": [{
                "issue": "entry-title-projection",
                "resolution": record["title"]["method"],
                "basis": f"Al-Isabah title projection state: {record['title']['state']}",
            }],
            "workflowStages": workflow_stages(record),
            "source": source,
            "provenance": provenance,
            "_navigationPage": first_page,
        }
    )
    return result


def item_page(item: dict[str, Any]) -> int | None:
    explicit = item.pop("_navigationPage", None)
    pages = [
        page["printedPage"]
        for segment in item.get("segments", [])
        for page in segment.get("pages", [])
        if page.get("printedPage") is not None
    ]
    return min(pages) if pages else explicit


def list_item(item: dict[str, Any], section_id: str, page: int | None) -> dict[str, Any]:
    result = {
        "id": item["id"],
        "kind": item["kind"],
        "sequence": item["sequence"],
        "printedEntryNumber": item["printedEntryNumber"],
        "sourceEntryNumber": item.get("sourceEntryNumber"),
        "volume": item["volume"],
        "printedPageStart": page,
        "printedPageEnd": page,
        "sectionId": section_id,
        "titleEn": item["title"]["en"],
        "titleAr": item["title"]["ar"],
        "translationState": item["translationState"],
        "machineAssessment": item["machineAssessment"],
        "humanReview": item["humanReview"],
        "unresolvedCount": len(item["unresolved"]),
        "publicEligibility": "eligible",
        **({"relationship": item["relationship"]} if item.get("relationship") else {}),
    }
    result["searchText"] = normalize_search_text(
        "\n".join(
            [item["title"]["en"], item["title"]["ar"]]
            + [
                f"{segment['english']}\n{segment['arabic']}"
                for segment in item["segments"]
            ]
        )
    )
    return result


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def build_sections(items: list[dict[str, Any]], corpus_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[tuple[int, int], list[tuple[dict[str, Any], int | None]]] = defaultdict(list)
    for item in items:
        page = item_page(item)
        bucket = ((page - 1) // 25) * 25 + 1 if page and page > 0 else 1
        groups[(item["volume"], bucket)].append((item, page))
    sections = []
    indexed = []
    by_volume: dict[int, list[tuple[int, list[tuple[dict[str, Any], int | None]]]]] = defaultdict(list)
    for (volume, start), values in groups.items():
        values.sort(key=lambda pair: (pair[0]["sequence"], pair[0]["id"]))
        by_volume[volume].append((start, values))
    for volume, volume_groups in sorted(by_volume.items()):
        volume_groups.sort(key=lambda pair: pair[0])
        section_ids = [f"volume-{volume:02d}-pages-{start:04d}-{start + 24:04d}" for start, _ in volume_groups]
        for position, ((start, values), section_id) in enumerate(zip(volume_groups, section_ids), 1):
            for item, page in values:
                indexed.append(list_item(item, section_id, page))
            sections.append({
                "schemaVersion": SCHEMA_VERSION,
                "corpusId": corpus_id,
                "id": section_id,
                "volume": volume,
                "label": f"Pages {start}–{start + 24}",
                "availability": "complete_translation",
                "position": position,
                "totalSections": len(volume_groups),
                "printedPageStart": start,
                "printedPageEnd": start + 24,
                "previousSectionId": section_ids[position - 2] if position > 1 else None,
                "nextSectionId": section_ids[position] if position < len(section_ids) else None,
                "items": [item for item, _ in values],
            })
    indexed.sort(key=lambda item: (item["volume"], item["sequence"], item["id"]))
    return sections, indexed


def ingest(
    distribution: Path, base: Path, output: Path, activated_at: str,
    archive: Path, release_metadata: Path, tag_ref: Path,
    rights_matrix: Path, source_authority: Path,
) -> dict[str, Any]:
    if output.exists():
        raise IngestionError(f"output already exists: {output}")
    try:
        manifest, records, binding = verify_distribution(
            distribution, archive, release_metadata, tag_ref, rights_matrix, source_authority
        )
    except CompatibilityError as error:
        raise IngestionError(str(error)) from error
    base_summary = load(base / "summary.json")
    base_index = load(base / "index.json")
    base_quarantine = load(base / "quarantine.json")
    base_exclusions = load(base / "exclusions.json")
    distribution_commit = manifest["repository"]["commit"]
    corpus_id = f"al-isabah-public-openiti-5835c18-book-{distribution_commit[:12]}"
    replaced_volumes = {int(record["volume"]) for record in records}
    items = []
    for listed in base_index.get("items", []):
        if int(listed["volume"]) in replaced_volumes:
            continue
        item = load(base / "items" / f"{listed['id']}.json")
        item["corpusId"] = corpus_id
        items.append(item)
    by_character, by_expanded = registry_indexes()
    for record in records:
        items.extend(direct_item(record, corpus_id, by_character, by_expanded, binding))
    ids = [item["id"] for item in items]
    if len(ids) != len(set(ids)):
        raise IngestionError("combined corpus contains duplicate stable item IDs")
    sections, index_items = build_sections(items, corpus_id)
    details = {item["id"]: item for item in items}
    for item in items:
        write_json(output / "items" / f"{item['id']}.json", item)
    for section in sections:
        write_json(output / "sections" / f"{section['id']}.json", section)
    volumes = []
    base_volume = {int(volume["number"]): volume for volume in base_summary["volumes"]}
    for volume_number in sorted(set(base_volume) | {item["volume"] for item in items}):
        matching = [item for item in index_items if item["volume"] == volume_number]
        matching_entries = [item for item in matching if item["kind"] == "entry"]
        matching_passages = [item for item in matching if item["kind"] == "passage"]
        section_count = len({item["sectionId"] for item in matching})
        pages = [item["printedPageStart"] for item in matching if item["printedPageStart"] is not None]
        if volume_number in replaced_volumes:
            source_count = len(matching_entries)
        else:
            source_count = int(base_volume[volume_number].get("sourceItemCount", len(matching_entries)))
        if not matching_entries:
            availability = "not_translated"
        elif len(matching_entries) >= source_count:
            availability = "complete_translation"
        else:
            availability = "selected_passages"
        volumes.append({
            "id": f"volume-{volume_number:02d}",
            "number": volume_number,
            "label": f"Volume {volume_number}",
            "availability": availability,
            "sourceItemCount": source_count,
            "itemCount": len(matching_entries),
            "passageCount": len(matching_passages),
            "sectionCount": section_count,
            "firstPrintedPage": min(pages) if pages else None,
            "lastPrintedPage": max(pages) if pages else None,
            "description": "Complete public-working translation coverage." if availability == "complete_translation" else base_volume.get(volume_number, {}).get("description", "No publicly consumable working translations are available yet."),
        })
    quarantine_records = base_quarantine.get("records", [])
    exclusion_records = base_exclusions.get("records", [])
    counts = {
        "sourceInventory": len(items) + len(quarantine_records),
        "entries": sum(item["kind"] == "entry" for item in items),
        "passages": sum(item["kind"] == "passage" for item in items),
        "translated": sum(item["translationState"] == "translated" for item in items),
        "needsAttention": sum(item["machineAssessment"] == "needs_attention" for item in items),
        "unresolvedItems": sum(len(item["unresolved"]) for item in items),
        "humanReviewed": sum(item["humanReview"] in {"reviewed", "verified"} for item in items),
        "quarantined": len(quarantine_records),
    }
    summary = {
        "schemaVersion": SCHEMA_VERSION,
        "work": base_summary["work"],
        "corpus": {
            "id": corpus_id,
            "sourceRepository": binding["sourceRepository"],
            "sourceCommit": binding["sourceCommit"],
            "generatedAt": manifest["generatedAt"],
            "promotionStatus": "blocked",
            "sourceAuthorityId": binding["sourceAuthorityId"],
            "sourceArtifactSha256": binding["sourceArtifactSha256"],
            "publicationStatus": "public-working",
            "license": binding["sourceLicense"],
            "rights": {
                "arabicSource": {"license": binding["sourceLicense"], "attribution": binding["sourceAttribution"]},
                "englishTranslation": {"license": binding["englishLicense"], "attribution": binding["englishAttribution"]},
                "matrix": binding["rightsMatrix"],
                "excludedMaterial": binding["excludedMaterial"],
            },
        },
        "counts": counts,
        "exclusions": base_exclusions["counts"],
        "volumes": volumes,
    }
    index = {"schemaVersion": SCHEMA_VERSION, "corpusId": corpus_id, "items": index_items}
    quarantine = {**base_quarantine, "corpusId": corpus_id, "sourceInventoryCount": counts["sourceInventory"], "publicItemCount": len(items), "quarantinedCount": len(quarantine_records)}
    exclusions = {**base_exclusions, "corpusId": corpus_id}
    write_json(output / "summary.json", summary)
    write_json(output / "index.json", index)
    write_json(output / "quarantine.json", quarantine)
    write_json(output / "exclusions.json", exclusions)
    files = []
    for path in sorted(output.rglob("*.json")):
        relative = path.relative_to(output).as_posix()
        files.append({"path": relative, "sha256": digest_file(path), "bytes": path.stat().st_size})
    corpus_manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "corpusId": corpus_id,
        "sourceAuthorityId": binding["sourceAuthorityId"],
        "distribution": {
            "id": manifest["distributionId"],
            "repository": manifest["repository"]["url"],
            "commit": distribution_commit,
            "manifestSha256": digest_file(distribution / "manifest.json"),
            "releaseTag": binding["tag"],
            "assetName": binding["asset"],
            "assetSha256": binding["sha256"],
            "rightsMatrix": binding["rightsMatrix"],
        },
        "objectCount": len(files),
        "files": files,
    }
    write_json(output / "manifest.json", corpus_manifest)
    activation = {
        "schemaVersion": "1.0.0",
        "corpusId": corpus_id,
        "prefix": f"public-corpora/al-isabah/{corpus_id}",
        "distributionId": manifest["distributionId"],
        "distributionCommit": distribution_commit,
        "distributionManifestSha256": digest_file(distribution / "manifest.json"),
        "activatedAt": activated_at,
        "rollback": {
            "strategy": "restore-verified-pointer",
            "previousCorpusId": base_summary["corpus"]["id"],
            "previousPrefix": f"public-corpora/al-isabah/{base_summary['corpus']['id']}",
        },
    }
    write_json(output.parent / "activation.json", activation)
    return activation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--distribution", required=True, type=Path)
    parser.add_argument("--base-corpus", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--activated-at", required=True)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--release-metadata", required=True, type=Path)
    parser.add_argument("--tag-ref", required=True, type=Path)
    parser.add_argument("--rights-matrix", required=True, type=Path)
    parser.add_argument("--source-authority", required=True, type=Path)
    args = parser.parse_args()
    activation = ingest(
        args.distribution.resolve(),
        args.base_corpus.resolve(),
        args.output.resolve(),
        args.activated_at,
        args.archive.resolve(),
        args.release_metadata.resolve(),
        args.tag_ref.resolve(),
        args.rights_matrix.resolve(),
        args.source_authority.resolve(),
    )
    print(f"Built {activation['corpusId']} from {activation['distributionId']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
