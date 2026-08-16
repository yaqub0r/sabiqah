#!/usr/bin/env python3
"""Ingest an Al-Isabah distribution into Sabiqah's immutable reader corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from rebuild_al_isabah_public_corpus import (
    normalize_search_text,
    render_arabic_poetry,
)
from verify_al_isabah_distribution import CompatibilityError, verify_distribution
from verify_al_isabah_legacy_binding import (
    LegacyBindingError,
    verify_legacy_binding,
)


ROOT = Path(__file__).resolve().parents[1]
HONORIFIC_REGISTRY = (
    ROOT / "packages" / "release-model" / "src" / "honorifics.registry.json"
)
SCHEMA_VERSION = "5.0.0"
LEGACY_SCHEMA_VERSION = "4.0.0"


@dataclass(frozen=True)
class LegacyBindingInputs:
    binding: Path
    pointer: Path
    legacy_release_metadata: Path
    legacy_tag_ref: Path
    approval_issue: Path
    approval_comment: Path
    activation_run: Path


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


def membership(item_ids: Iterable[str]) -> dict[str, Any]:
    ordered = sorted(item_ids)
    return {
        "itemCount": len(ordered),
        "itemIdsSha256": digest_bytes(canonical_json(ordered)),
        "itemIds": ordered,
    }


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
        "sourceRepository": binding["sourceRepository"],
        "sourceCommit": binding["sourceCommit"],
        "sourceArtifactSha256": source["artifactSha256"],
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
        "sourceRepository": binding["sourceRepository"],
        "sourceCommit": binding["sourceCommit"],
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
    cohort_id: str,
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
                "cohortId": cohort_id,
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
            "cohortId": cohort_id,
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
        "cohortId": item["cohortId"],
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


def cohort_from_binding(
    cohort_id: str,
    binding: dict[str, Any],
    item_ids: Iterable[str],
    manifest: dict[str, Any],
    supersedes: list[dict[str, Any]],
) -> dict[str, Any]:
    cohort = {
        "id": cohort_id,
        "kind": "distribution-v2",
        "source": {
            "authorityId": binding["sourceAuthorityId"],
            "producerAuthorityId": binding["producerAuthorityId"],
            "repository": binding["sourceRepository"],
            "commit": binding["sourceCommit"],
            "artifactSha256": binding["sourceArtifactSha256"],
        },
        "rights": {
            "arabicSource": {
                "license": binding["sourceLicense"],
                "attribution": binding["sourceAttribution"],
            },
            "englishTranslation": {
                "license": binding["englishLicense"],
                "attribution": binding["englishAttribution"],
            },
            "matrix": binding["rightsMatrix"],
            "excludedMaterial": binding["excludedMaterial"],
        },
        "state": {
            "publicationStatus": "public-working",
            "promotionStatus": "blocked",
            "completeness": "partial-release",
        },
        "membership": membership(item_ids),
        "upstream": {
            "distributionId": manifest["distributionId"],
            "releaseTag": binding["tag"],
            "assetName": binding["asset"],
            "assetSha256": binding["sha256"],
        },
    }
    if supersedes:
        cohort["supersedes"] = supersedes
    return cohort


def migrate_legacy_cohort(
    base_summary: dict[str, Any],
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    corpus = base_summary.get("corpus", {})
    rights = corpus.get("rights")
    required = (
        corpus.get("id"), corpus.get("sourceAuthorityId"),
        corpus.get("sourceRepository"), corpus.get("sourceCommit"),
        corpus.get("sourceArtifactSha256"), rights,
    )
    if any(value in (None, "", {}) for value in required):
        raise IngestionError("legacy corpus lacks verified source or rights metadata")
    cohort_id = f"legacy:{corpus['id']}"
    producer_authorities = {
        item.get("source", {}).get("producerAuthorityId") for item in items
        if item.get("source", {}).get("producerAuthorityId")
    }
    if len(producer_authorities) > 1:
        raise IngestionError("legacy corpus has contradictory producer authorities")
    for item in items:
        source = item.get("source", {})
        provenance = item.get("provenance", {})
        if (
            source.get("authorityId") != corpus["sourceAuthorityId"]
            or source.get("license") != corpus.get("license")
            or source.get("attribution") != rights.get("arabicSource", {}).get("attribution")
            or source.get("englishRights") != rights.get("englishTranslation")
            or source.get("rightsMatrix") != rights.get("matrix")
            or provenance.get("sourceArtifactSha256") != corpus["sourceArtifactSha256"]
        ):
            raise IngestionError("legacy record cannot be rebound to corpus metadata")
        item["schemaVersion"] = SCHEMA_VERSION
        item["cohortId"] = cohort_id
        source.update({
            "sourceRepository": corpus["sourceRepository"],
            "sourceCommit": corpus["sourceCommit"],
            "sourceArtifactSha256": corpus["sourceArtifactSha256"],
        })
        provenance.update({
            "sourceRepository": corpus["sourceRepository"],
            "sourceCommit": corpus["sourceCommit"],
        })
    source = {
        "authorityId": corpus["sourceAuthorityId"],
        "repository": corpus["sourceRepository"],
        "commit": corpus["sourceCommit"],
        "artifactSha256": corpus["sourceArtifactSha256"],
    }
    if producer_authorities:
        source["producerAuthorityId"] = next(iter(producer_authorities))
    return [{
        "id": cohort_id,
        "kind": "legacy-schema-4",
        "source": source,
        "rights": rights,
        "state": {
            "publicationStatus": corpus.get("publicationStatus", "public-working"),
            "promotionStatus": corpus.get("promotionStatus"),
            "completeness": "carried-forward",
        },
        "membership": membership(item["id"] for item in items),
        "upstream": {"corpusId": corpus["id"], "schemaVersion": LEGACY_SCHEMA_VERSION},
    }]


def migrate_attested_legacy_cohorts(
    items: list[dict[str, Any]], cohorts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_member: dict[str, dict[str, Any]] = {}
    for cohort in cohorts:
        for item_id in cohort["membership"]["itemIds"]:
            if item_id in by_member:
                raise IngestionError("legacy binding cohort membership overlaps")
            by_member[item_id] = cohort
    if set(by_member) != {item["id"] for item in items}:
        raise IngestionError("legacy binding leaves records unassigned or unknown")
    for item in items:
        cohort = by_member[item["id"]]
        source_binding = cohort["source"]
        rights = cohort["rights"]
        source = item.setdefault("source", {})
        provenance = item.setdefault("provenance", {})
        item["schemaVersion"] = SCHEMA_VERSION
        item["cohortId"] = cohort["id"]
        source.update({
            "authorityId": source_binding["authorityId"],
            "producerAuthorityId": source_binding["producerAuthorityId"],
            "sourceRepository": source_binding["repository"],
            "sourceCommit": source_binding["commit"],
            "sourceArtifactSha256": source_binding["artifactSha256"],
            "license": rights["arabicSource"]["license"],
            "attribution": rights["arabicSource"]["attribution"],
            "englishRights": rights["englishTranslation"],
            "rightsMatrix": rights["matrix"],
        })
        provenance.update({
            "sourceAuthorityId": source_binding["authorityId"],
            "producerAuthorityId": source_binding["producerAuthorityId"],
            "sourceRepository": source_binding["repository"],
            "sourceCommit": source_binding["commit"],
            "sourceArtifactSha256": source_binding["artifactSha256"],
        })
    return json.loads(json.dumps(cohorts))


def carried_cohorts(
    base_summary: dict[str, Any],
    items: list[dict[str, Any]],
    attested_cohorts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    version = str(base_summary.get("schemaVersion", ""))
    if version == LEGACY_SCHEMA_VERSION:
        if attested_cohorts is not None:
            return migrate_attested_legacy_cohorts(items, attested_cohorts)
        return migrate_legacy_cohort(base_summary, items)
    if version != SCHEMA_VERSION:
        raise IngestionError("base corpus has an unsupported major schema version")
    cohorts = base_summary.get("corpus", {}).get("cohorts")
    if not isinstance(cohorts, list) or not cohorts:
        raise IngestionError("base corpus cohort metadata is missing")
    by_id = {cohort.get("id"): cohort for cohort in cohorts if isinstance(cohort, dict)}
    members: dict[str, list[str]] = defaultdict(list)
    for item in items:
        cohort_id = item.get("cohortId")
        if cohort_id not in by_id:
            raise IngestionError("base corpus contains an unknown item cohort")
        cohort = by_id[cohort_id]
        source_binding = cohort.get("source", {})
        rights_binding = cohort.get("rights", {})
        source = item.get("source", {})
        provenance = item.get("provenance", {})
        if (
            source.get("authorityId") != source_binding.get("authorityId")
            or source.get("producerAuthorityId") != source_binding.get("producerAuthorityId")
            or source.get("sourceRepository") != source_binding.get("repository")
            or source.get("sourceCommit") != source_binding.get("commit")
            or source.get("sourceArtifactSha256") != source_binding.get("artifactSha256")
            or provenance.get("sourceRepository") != source_binding.get("repository")
            or provenance.get("sourceCommit") != source_binding.get("commit")
            or provenance.get("sourceArtifactSha256") != source_binding.get("artifactSha256")
            or source.get("license") != rights_binding.get("arabicSource", {}).get("license")
            or source.get("attribution") != rights_binding.get("arabicSource", {}).get("attribution")
            or source.get("englishRights") != rights_binding.get("englishTranslation")
            or source.get("rightsMatrix") != rights_binding.get("matrix")
        ):
            raise IngestionError("base record cannot be rebound to cohort metadata")
        members[cohort_id].append(item["id"])
    result = []
    for cohort_id, cohort_value in sorted(by_id.items()):
        if not isinstance(cohort_id, str):
            raise IngestionError("base corpus contains an invalid cohort ID")
        cohort = json.loads(json.dumps(cohort_value))
        cohort["membership"] = membership(members.get(cohort_id, []))
        result.append(cohort)
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
    legacy_binding: LegacyBindingInputs | None = None,
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
    attested_cohorts = None
    legacy_binding_record = None
    if base_summary.get("schemaVersion") != LEGACY_SCHEMA_VERSION and legacy_binding is not None:
        raise IngestionError("legacy binding cannot be reused for this base schema")
    if base_summary.get("schemaVersion") == LEGACY_SCHEMA_VERSION and legacy_binding is not None:
        try:
            attested_cohorts, legacy_binding_record = verify_legacy_binding(
                legacy_binding.binding,
                base,
                legacy_binding.pointer,
                legacy_binding.legacy_release_metadata,
                legacy_binding.legacy_tag_ref,
                rights_matrix,
                source_authority,
                ROOT / "CONTENT-LICENSE.md",
                ROOT / "NOTICE.md",
                ROOT / "docs" / "attribution" / "al-isabah.md",
                legacy_binding.approval_issue,
                legacy_binding.approval_comment,
                legacy_binding.activation_run,
                distribution / "manifest.json",
                release_metadata,
                tag_ref,
                SCHEMA_VERSION,
            )
        except LegacyBindingError as error:
            raise IngestionError(str(error)) from error
    distribution_commit = manifest["repository"]["commit"]
    corpus_id = "pending-content-addressed-corpus"
    incoming_ids = {record["id"] for record in records}
    items = []
    for listed in base_index.get("items", []):
        item = load(base / "items" / f"{listed['id']}.json")
        item["corpusId"] = corpus_id
        items.append(item)
    cohorts = carried_cohorts(base_summary, items, attested_cohorts)
    replaced_members: dict[str, list[str]] = defaultdict(list)
    for item in items:
        if item["id"] in incoming_ids:
            replaced_members[item["cohortId"]].append(item["id"])
    items = [item for item in items if item["id"] not in incoming_ids]
    remaining_by_cohort: dict[str, list[str]] = defaultdict(list)
    for item in items:
        remaining_by_cohort[item["cohortId"]].append(item["id"])
    for cohort in cohorts:
        cohort["membership"] = membership(remaining_by_cohort.get(cohort["id"], []))
    new_cohort_id = f"distribution:{distribution_commit[:12]}"
    prior_current_cohort = next(
        (cohort for cohort in cohorts if cohort["id"] == new_cohort_id), None
    )
    cohorts = [cohort for cohort in cohorts if cohort["id"] != new_cohort_id]
    by_character, by_expanded = registry_indexes()
    for record in records:
        items.extend(direct_item(record, corpus_id, by_character, by_expanded, binding, new_cohort_id))
    new_item_ids = [item["id"] for item in items if item["cohortId"] == new_cohort_id]
    supersedes = [
        {"cohortId": cohort_id, **membership(item_ids)}
        for cohort_id, item_ids in sorted(replaced_members.items())
        if cohort_id != new_cohort_id
    ]
    for supersession in (prior_current_cohort or {}).get("supersedes", []):
        if supersession not in supersedes:
            supersedes.append(supersession)
    supersedes.sort(key=lambda value: (value["cohortId"], value["itemIdsSha256"]))
    cohorts.append(cohort_from_binding(new_cohort_id, binding, new_item_ids, manifest, supersedes))
    ids = [item["id"] for item in items]
    if len(ids) != len(set(ids)):
        raise IngestionError("combined corpus contains duplicate stable item IDs")
    fingerprint_items = []
    for item in sorted(items, key=lambda value: value["id"]):
        fingerprint_item = json.loads(json.dumps(item))
        fingerprint_item.pop("corpusId", None)
        fingerprint_items.append(fingerprint_item)
    candidate_fingerprint = digest_bytes(canonical_json({
        "schemaVersion": SCHEMA_VERSION,
        "distributionManifestSha256": digest_file(distribution / "manifest.json"),
        "legacyBinding": legacy_binding_record,
        "cohorts": cohorts,
        "items": fingerprint_items,
    }))
    corpus_id = f"al-isabah-public-openiti-mixed-{candidate_fingerprint}"
    for item in items:
        item["corpusId"] = corpus_id
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
        source_count = max(
            len(matching_entries),
            int(base_volume.get(volume_number, {}).get("sourceItemCount", 0)),
        )
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
            "generatedAt": manifest["generatedAt"],
            "promotionStatus": "blocked",
            "publicationStatus": "public-working",
            "cohorts": cohorts,
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
        "cohorts": [{"id": cohort["id"], **cohort["membership"]} for cohort in cohorts],
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
    if legacy_binding_record is not None:
        corpus_manifest["legacyBindings"] = [legacy_binding_record]
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
    if legacy_binding_record is not None:
        activation["legacyBinding"] = legacy_binding_record
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
    parser.add_argument("--legacy-binding", type=Path)
    parser.add_argument("--legacy-pointer", type=Path)
    parser.add_argument("--legacy-release-metadata", type=Path)
    parser.add_argument("--legacy-tag-ref", type=Path)
    parser.add_argument("--legacy-approval-issue", type=Path)
    parser.add_argument("--legacy-approval-comment", type=Path)
    parser.add_argument("--legacy-activation-run", type=Path)
    args = parser.parse_args()
    legacy_values = [
        args.legacy_binding, args.legacy_pointer, args.legacy_release_metadata,
        args.legacy_tag_ref, args.legacy_approval_issue, args.legacy_approval_comment,
        args.legacy_activation_run,
    ]
    if any(legacy_values) and not all(legacy_values):
        parser.error("all legacy binding evidence arguments are required together")
    legacy_binding = LegacyBindingInputs(*(
        value.resolve() for value in legacy_values
    )) if all(legacy_values) else None
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
        legacy_binding,
    )
    print(f"Built {activation['corpusId']} from {activation['distributionId']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
