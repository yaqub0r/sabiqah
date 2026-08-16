#!/usr/bin/env python3
"""Validate a public Al-Isabah working corpus and its quarantine accounting."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from rebuild_al_isabah_public_corpus import (
    FORBIDDEN_PUBLIC_PATTERNS,
    HONORIFIC_BY_CHARACTER,
    HONORIFIC_ENTRIES,
    HONORIFIC_POLICY_VERSION,
    LICENSE_SPDX,
    LICENSE_URL,
    SCHEMA_VERSION,
    SOURCE_AUTHORITY_ID,
    SOURCE_ARABIC_APPARATUS_REPLACEMENTS,
    SOURCE_COMMIT,
    SOURCE_HEADINGS_BEFORE,
    SOURCE_REPOSITORY,
    SOURCE_SHA256,
    SOURCE_URL,
    honorific_display,
    honorific_semantic_key,
    load_entry_title_profile,
    normalize_search_text,
)


ITEM_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,199}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
COHORT_SCHEMA_VERSION = "5.0.0"
HONORIFIC_CODEPOINT_RANGES = re.compile(
    r"[\uFBC3-\uFBD2\uFD40-\uFD4F\uFDC8-\uFDCF\uFDFD-\uFDFF\U00010ED1-\U00010ED8]"
)
HONORIFIC_ENTRY_BY_ID = {entry["id"]: entry for entry in HONORIFIC_ENTRIES}
MISATTACHED_COMPACT_HONORIFIC = re.compile(
    r",[\t ]*(?:"
    + "|".join(
        re.escape(character)
        for character in sorted(HONORIFIC_BY_CHARACTER, key=len, reverse=True)
    )
    + r")|—[\t ]*(?:"
    + "|".join(
        re.escape(character)
        for character in sorted(HONORIFIC_BY_CHARACTER, key=len, reverse=True)
    )
    + r")[\t ]*—"
)
EMBEDDED_ENTRY_HEADING = re.compile(r"(?m)^\s*\d+\s*[.\-—]\s*\S")
DANGLING_DASH_BOUNDARY = re.compile(r"—[ \t]*\n\s*\n[ \t]*(?=\S)")
STRUCTURAL_HEADING_IN_PROSE = re.compile(
    r"(?mi)^(?:THE LETTER\b.*|(?:THE\s+)?(?:SECOND\s+AND\s+THIRD\s+SECTIONS|SECOND,\s+THIRD,\s+AND\s+FOURTH\s+SECTIONS|SECTION\s+(?:ONE|TWO|THREE|FOUR)|FOURTH\s+SECTION)|NO ONE WAS MENTIONED IN (?:EITHER|ANY) OF THEM\.?)\s*$"
)
RAW_METER_LABEL = re.compile(
    r"\[(?:al-)?(?:rajaz|tawil|basit)(?: meter)?\]|\[al-[A-Za-z-]+ meter\]",
    re.I,
)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top level must be an object")
    return value


def canonical_ids_hash(item_ids: list[str]) -> str:
    encoded = (json.dumps(sorted(item_ids), ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_membership(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"itemCount", "itemIdsSha256", "itemIds"}:
        errors.append(f"{label}: membership metadata is missing or unknown")
        return []
    item_ids = value.get("itemIds")
    if not isinstance(item_ids, list) or any(
        not isinstance(item_id, str) or not ITEM_ID.fullmatch(item_id) for item_id in item_ids
    ):
        errors.append(f"{label}: membership item IDs are invalid")
        return []
    if item_ids != sorted(item_ids) or len(item_ids) != len(set(item_ids)):
        errors.append(f"{label}: membership item IDs must be sorted and unique")
    if value.get("itemCount") != len(item_ids):
        errors.append(f"{label}: membership count mismatch")
    if value.get("itemIdsSha256") != canonical_ids_hash(item_ids):
        errors.append(f"{label}: membership hash mismatch")
    return item_ids


def cohort_map(summary: dict[str, Any], errors: list[str]) -> dict[str, dict[str, Any]]:
    corpus = summary.get("corpus", {})
    forbidden_global = {
        "sourceRepository", "sourceCommit", "sourceAuthorityId",
        "sourceArtifactSha256", "license", "rights",
    }
    if forbidden_global & set(corpus):
        errors.append("summary: schema 5 corpus makes a false corpus-wide source or rights claim")
    cohorts = corpus.get("cohorts")
    if not isinstance(cohorts, list) or not cohorts:
        errors.append("summary: cohort metadata is missing")
        return {}
    result: dict[str, dict[str, Any]] = {}
    assigned: set[str] = set()
    for position, cohort in enumerate(cohorts):
        label = f"summary.corpus.cohorts[{position}]"
        if not isinstance(cohort, dict):
            errors.append(f"{label}: cohort must be an object")
            continue
        expected = {"id", "kind", "source", "rights", "state", "membership", "upstream"}
        if "supersedes" in cohort:
            expected.add("supersedes")
        if set(cohort) != expected:
            errors.append(f"{label}: cohort contains missing or unknown metadata")
        cohort_id = cohort.get("id")
        if not isinstance(cohort_id, str) or not ITEM_ID.fullmatch(cohort_id) or cohort_id in result:
            errors.append(f"{label}: cohort ID is invalid or duplicated")
            continue
        if cohort.get("kind") not in {"legacy-schema-4", "distribution-v2"}:
            errors.append(f"{label}: cohort kind is unknown")
        source = cohort.get("source")
        source_required = {"authorityId", "repository", "commit", "artifactSha256"}
        if isinstance(source, dict) and "producerAuthorityId" in source:
            source_required.add("producerAuthorityId")
        if not isinstance(source, dict) or set(source) != source_required:
            errors.append(f"{label}: source binding is incomplete or unknown")
        elif (
            not ITEM_ID.fullmatch(str(source.get("authorityId", "")))
            or not re.fullmatch(r"https://[^\s]+", str(source.get("repository", "")))
            or not re.fullmatch(r"[a-f0-9]{40}", str(source.get("commit", "")))
            or not SHA256.fullmatch(str(source.get("artifactSha256", "")))
        ):
            errors.append(f"{label}: source binding is invalid")
        elif source.get("producerAuthorityId") is not None and not ITEM_ID.fullmatch(
            str(source.get("producerAuthorityId"))
        ):
            errors.append(f"{label}: producer authority is invalid")
        rights = cohort.get("rights")
        if not isinstance(rights, dict) or set(rights) != {
            "arabicSource", "englishTranslation", "matrix", "excludedMaterial"
        }:
            errors.append(f"{label}: rights binding is incomplete or unknown")
        else:
            arabic_value = rights.get("arabicSource", {})
            english_value = rights.get("englishTranslation", {})
            arabic = arabic_value if isinstance(arabic_value, dict) else {}
            english = english_value if isinstance(english_value, dict) else {}
            if set(arabic) != {"license", "attribution"} or not arabic.get("attribution"):
                errors.append(f"{label}: Arabic rights are incomplete")
            if set(english) != {"license", "attribution"} or not english.get("attribution"):
                errors.append(f"{label}: English rights are incomplete")
            if arabic.get("attribution") == english.get("attribution"):
                errors.append(f"{label}: Arabic and English rights are collapsed")
            if not rights.get("excludedMaterial"):
                errors.append(f"{label}: rights exclusions are missing")
            for language, value in (("Arabic", arabic), ("English", english)):
                license_value = value.get("license", {}) if isinstance(value, dict) else {}
                if not isinstance(license_value, dict) or set(license_value) != {"spdx", "url"} or not all(license_value.values()):
                    errors.append(f"{label}: {language} license is incomplete or unknown")
            matrix = rights.get("matrix", {})
            if not isinstance(matrix, dict) or set(matrix) != {
                "id", "schema", "decision", "reviewedOn", "followUp"
            } or matrix.get("schema") != "al-isabah.book-rights-matrix.v1" or matrix.get("decision") != "approved-under-cc-by-nc-sa-4.0" or matrix.get("followUp") != "required-on-change":
                errors.append(f"{label}: rights matrix is incomplete, unknown, or unsafe")
        state = cohort.get("state")
        if not isinstance(state, dict) or set(state) != {
            "publicationStatus", "promotionStatus", "completeness"
        } or state.get("publicationStatus") != "public-working" or state.get("promotionStatus") != "blocked" or state.get("completeness") not in {"carried-forward", "partial-release"}:
            errors.append(f"{label}: publication, completeness, or promotion state is unsafe")
        member_ids = validate_membership(cohort.get("membership"), label, errors)
        overlap = assigned.intersection(member_ids)
        if overlap:
            errors.append(f"{label}: cohort membership overlaps another cohort")
        assigned.update(member_ids)
        supersedes = cohort.get("supersedes", [])
        if not isinstance(supersedes, list):
            errors.append(f"{label}: supersession metadata is invalid")
        else:
            for supersession in supersedes:
                if not isinstance(supersession, dict) or set(supersession) != {
                    "cohortId", "itemCount", "itemIdsSha256", "itemIds"
                }:
                    errors.append(f"{label}: supersession metadata is incomplete or unknown")
                    continue
                validate_membership(
                    {key: supersession[key] for key in ("itemCount", "itemIdsSha256", "itemIds")},
                    f"{label}.supersedes",
                    errors,
                )
        upstream = cohort.get("upstream")
        if cohort.get("kind") == "legacy-schema-4":
            if not isinstance(upstream, dict) or set(upstream) != {"corpusId", "schemaVersion"} or upstream.get("schemaVersion") != SCHEMA_VERSION:
                errors.append(f"{label}: legacy upstream binding is incomplete or unknown")
        elif cohort.get("kind") == "distribution-v2":
            if not isinstance(upstream, dict) or set(upstream) != {
                "distributionId", "releaseTag", "assetName", "assetSha256"
            } or not all(upstream.values()) or not SHA256.fullmatch(str(upstream.get("assetSha256", ""))):
                errors.append(f"{label}: distribution upstream binding is incomplete or unknown")
        result[cohort_id] = cohort
    return result


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    title_decisions = load_entry_title_profile()
    summary = load(root / "summary.json")
    index = load(root / "index.json")
    quarantine = load(root / "quarantine.json")
    exclusions = load(root / "exclusions.json")
    manifest = load(root / "manifest.json")
    distribution = manifest.get("distribution", {})
    distribution_v2 = bool(distribution.get("releaseTag"))
    corpus = summary.get("corpus", {})
    corpus_id = corpus.get("id")
    schema_version = summary.get("schemaVersion")
    if schema_version not in {SCHEMA_VERSION, COHORT_SCHEMA_VERSION}:
        errors.append("summary: unsupported schema version")
    if index.get("schemaVersion") != schema_version:
        errors.append("index: schema version differs from summary")
    if manifest.get("schemaVersion") != schema_version:
        errors.append("manifest: schema version differs from summary")
    if not isinstance(corpus_id, str) or not ITEM_ID.fullmatch(corpus_id):
        errors.append("summary: corpus ID is invalid")
    if corpus.get("publicationStatus") != "public-working":
        errors.append("summary: corpus must be explicitly public-working")
    if corpus.get("promotionStatus") != "blocked":
        errors.append("summary: canonical promotion must remain blocked")
    cohorts = cohort_map(summary, errors) if schema_version == COHORT_SCHEMA_VERSION else {}
    if schema_version == COHORT_SCHEMA_VERSION:
        current_distribution_cohorts = [
            cohort for cohort in cohorts.values()
            if cohort.get("kind") == "distribution-v2"
            and cohort.get("upstream", {}).get("distributionId") == distribution.get("id")
        ]
        if len(current_distribution_cohorts) != 1:
            errors.append("summary: current verified distribution cohort is missing or ambiguous")
        else:
            current = current_distribution_cohorts[0]
            upstream = current["upstream"]
            if (
                upstream.get("releaseTag") != distribution.get("releaseTag")
                or upstream.get("assetName") != distribution.get("assetName")
                or upstream.get("assetSha256") != distribution.get("assetSha256")
                or current.get("rights", {}).get("matrix") != distribution.get("rightsMatrix")
            ):
                errors.append("summary: distribution cohort differs from verified manifest binding")
    if schema_version == SCHEMA_VERSION:
        if corpus.get("sourceAuthorityId") != SOURCE_AUTHORITY_ID:
            errors.append("summary: wrong source authority")
        if corpus.get("sourceRepository") != SOURCE_REPOSITORY:
            errors.append("summary: wrong source repository")
        if corpus.get("sourceCommit") != SOURCE_COMMIT:
            errors.append("summary: wrong source commit")
        if corpus.get("sourceArtifactSha256") != SOURCE_SHA256:
            errors.append("summary: wrong source artifact hash")
        if corpus.get("license", {}).get("spdx") != LICENSE_SPDX:
            errors.append("summary: source license is missing or incorrect")
        if corpus.get("license", {}).get("url") != LICENSE_URL:
            errors.append("summary: source license URL is missing or incorrect")
    corpus_rights = corpus.get("rights", {})
    if distribution_v2 and schema_version == SCHEMA_VERSION:
        arabic_rights = corpus_rights.get("arabicSource", {})
        english_rights = corpus_rights.get("englishTranslation", {})
        if arabic_rights.get("license") != corpus.get("license") or not arabic_rights.get("attribution"):
            errors.append("summary: Arabic source rights are incomplete")
        if english_rights.get("license") != corpus.get("license") or not english_rights.get("attribution"):
            errors.append("summary: independently authored English rights are incomplete")
        if arabic_rights.get("attribution") == english_rights.get("attribution"):
            errors.append("summary: Arabic and English attribution were collapsed")
        if corpus_rights.get("matrix") != distribution.get("rightsMatrix"):
            errors.append("summary: rights matrix differs from the verified distribution")
        if not corpus_rights.get("excludedMaterial"):
            errors.append("summary: rights exclusions are missing")
    if any(
        value.get("corpusId") != corpus_id
        for value in (index, quarantine, exclusions, manifest)
    ):
        errors.append("corpus ID differs across public artifacts")

    items = index.get("items")
    if not isinstance(items, list):
        errors.append("index: items must be a list")
        items = []
    ids: set[str] = set()
    unresolved = 0
    needs_attention = 0
    translated = 0
    entry_count = 0
    passage_count = 0
    human_reviewed = 0
    for position, item in enumerate(items):
        item_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(item_id, str) or not ITEM_ID.fullmatch(item_id):
            errors.append(f"index.items[{position}]: invalid item ID")
            continue
        if item_id in ids:
            errors.append(f"index: duplicate item ID {item_id}")
        ids.add(item_id)
        if item.get("publicEligibility") != "eligible":
            errors.append(f"index: {item_id} is not public-eligible")
        detail_path = root / "items" / f"{item_id}.json"
        if not detail_path.is_file():
            errors.append(f"index: missing detail {item_id}")
            continue
        detail = load(detail_path)
        if detail.get("id") != item_id or detail.get("corpusId") != corpus_id:
            errors.append(f"detail: inconsistent identity for {item_id}")
        if detail.get("schemaVersion") != schema_version:
            errors.append(f"detail: wrong schema version for {item_id}")
        if detail.get("kind") not in {"entry", "passage"} or detail.get(
            "publicEligibility"
        ) != "eligible":
            errors.append(f"detail: {item_id} is not an eligible public record")
        entry_count += detail.get("kind") == "entry"
        passage_count += detail.get("kind") == "passage"
        human_reviewed += detail.get("humanReview") in {"reviewed", "verified"}
        source = detail.get("source", {})
        provenance = detail.get("provenance", {})
        cohort = None
        if schema_version == COHORT_SCHEMA_VERSION:
            cohort_id = detail.get("cohortId")
            if item.get("cohortId") != cohort_id or cohort_id not in cohorts:
                errors.append(f"detail: unknown or contradictory cohort for {item_id}")
            else:
                cohort = cohorts[cohort_id]
                binding = cohort.get("source", {})
                rights = cohort.get("rights", {})
                if source.get("authorityId") != binding.get("authorityId"):
                    errors.append(f"detail: source authority differs from cohort for {item_id}")
                if source.get("producerAuthorityId") != binding.get("producerAuthorityId"):
                    errors.append(f"detail: producer authority differs from cohort for {item_id}")
                if source.get("sourceRepository") != binding.get("repository") or provenance.get("sourceRepository") != binding.get("repository"):
                    errors.append(f"detail: source repository differs from cohort for {item_id}")
                if source.get("sourceCommit") != binding.get("commit") or provenance.get("sourceCommit") != binding.get("commit"):
                    errors.append(f"detail: source commit differs from cohort for {item_id}")
                if source.get("sourceArtifactSha256") != binding.get("artifactSha256") or provenance.get("sourceArtifactSha256") != binding.get("artifactSha256"):
                    errors.append(f"detail: source artifact differs from cohort for {item_id}")
                if source.get("license") != rights.get("arabicSource", {}).get("license") or source.get("attribution") != rights.get("arabicSource", {}).get("attribution"):
                    errors.append(f"detail: Arabic rights differ from cohort for {item_id}")
                if source.get("englishRights") != rights.get("englishTranslation"):
                    errors.append(f"detail: English rights differ from cohort for {item_id}")
                if source.get("rightsMatrix") != rights.get("matrix"):
                    errors.append(f"detail: rights matrix differs from cohort for {item_id}")
        else:
            if source.get("authorityId") != SOURCE_AUTHORITY_ID:
                errors.append(f"detail: wrong source authority for {item_id}")
            if source.get("sourceUrl") != SOURCE_URL:
                errors.append(f"detail: wrong source URL for {item_id}")
            if source.get("license", {}).get("spdx") != LICENSE_SPDX:
                errors.append(f"detail: wrong source license for {item_id}")
            if source.get("license", {}).get("url") != LICENSE_URL:
                errors.append(f"detail: wrong source license URL for {item_id}")
            if provenance.get("sourceArtifactSha256") != SOURCE_SHA256:
                errors.append(f"detail: wrong source artifact hash for {item_id}")
        exact_source_sha = source.get("sourceExactTextSha256")
        if (
            not isinstance(exact_source_sha, str)
            or not SHA256.fullmatch(exact_source_sha)
            or provenance.get("sourceExactTextSha256") != exact_source_sha
        ):
            errors.append(f"detail: exact source text integrity is missing for {item_id}")
        remediation = detail.get("remediation")
        if remediation is not None:
            if remediation.get("sourceArabicReplaced") is not True:
                errors.append(f"detail: source Arabic was not replaced for {item_id}")
            if remediation.get("privateLocatorsRemoved") is not True:
                errors.append(f"detail: private locators were not removed for {item_id}")
        elif source.get("alignment", {}).get("method") != (
            "al-isabah-public-distribution-v2"
            if (cohort and cohort.get("kind") == "distribution-v2") or (distribution_v2 and schema_version == SCHEMA_VERSION)
            else "al-isabah-public-distribution-v1"
        ):
            errors.append(f"detail: {item_id} has neither remediation nor direct distribution provenance")
        if distribution_v2 and schema_version == SCHEMA_VERSION:
            if not source.get("producerAuthorityId"):
                errors.append(f"detail: producer authority is missing for {item_id}")
            if source.get("rightsMatrix") != corpus_rights.get("matrix"):
                errors.append(f"detail: rights matrix differs for {item_id}")
            if source.get("englishRights") != corpus_rights.get("englishTranslation"):
                errors.append(f"detail: English rights differ for {item_id}")
            if source.get("attribution") != corpus_rights.get("arabicSource", {}).get("attribution"):
                errors.append(f"detail: Arabic attribution differs for {item_id}")
        segments = detail.get("segments", [])
        source_entry_number = detail.get("sourceEntryNumber")
        title_decision = title_decisions.get(source_entry_number)
        if title_decision is not None:
            if detail.get("title") != title_decision["title"]:
                errors.append(
                    f"detail: {item_id} title differs from Al-Isabah entry {source_entry_number} contract"
                )
            if not segments:
                errors.append(f"detail: {item_id} has no contracted body opening")
            else:
                kind = title_decision["bodyOpeningKind"]
                for language, field in (("ar", "arabic"), ("en", "english")):
                    opening = title_decision["bodyOpening"][language]
                    body = str(segments[0].get(field, ""))
                    remainder = body[len(opening) :] if body.startswith(opening) else ""
                    if not body.startswith(opening):
                        errors.append(
                            f"detail: {item_id} loses the contracted {language} body opening"
                        )
                    elif kind == "lineage" and not re.match(
                        r"^[.,;:،؛]*\n\n", remainder
                    ):
                        errors.append(
                            f"detail: {item_id} lineage must be a separate opening paragraph in {language}"
                        )
        displayed_arabic = " ".join(
            [str(detail.get("title", {}).get("ar", ""))]
            + [str(segment.get("arabic", "")) for segment in segments]
        ).strip()
        displayed_arabic = " ".join(displayed_arabic.split())
        if "%" in displayed_arabic:
            errors.append(f"detail: OpenITI poetry delimiter remains for {item_id}")
        source_text_sha = hashlib.sha256(displayed_arabic.encode("utf-8")).hexdigest()
        if source.get("sourceTextSha256") != source_text_sha:
            errors.append(f"detail: source text hash mismatch for {item_id}")
        if provenance.get("sourceTextSha256") != source_text_sha:
            errors.append(f"detail: provenance text hash mismatch for {item_id}")
        displayed_english = "\n".join(
            [str(detail.get("title", {}).get("en", ""))]
            + [str(segment.get("english", "")) for segment in segments]
        )
        translation_state = detail.get("translationState")
        exclusion_reasons = (
            remediation.get("englishExclusionReasonCodes", [])
            if remediation is not None
            else []
        )
        if translation_state != "translated":
            errors.append(f"detail: {item_id} must expose public working English")
        if not displayed_english.strip() or detail.get("title", {}).get("en", "").startswith(
            "Entry "
        ):
            errors.append(f"detail: public working English is empty or generic for {item_id}")
        if remediation is not None and (
            remediation.get("englishExcluded") is not False or exclusion_reasons
        ):
            errors.append(f"detail: public working English is marked excluded for {item_id}")
        if MISATTACHED_COMPACT_HONORIFIC.search(displayed_english):
            errors.append(
                f"detail: compact honorific retains parenthetical punctuation for {item_id}"
            )
        if EMBEDDED_ENTRY_HEADING.search(displayed_english):
            errors.append(f"detail: embedded legacy entry heading remains for {item_id}")
        if DANGLING_DASH_BOUNDARY.search(displayed_english):
            errors.append(f"detail: dangling dash crosses a paragraph boundary for {item_id}")
        if detail.get("kind") == "entry" and STRUCTURAL_HEADING_IN_PROSE.search(
            displayed_english
        ):
            errors.append(f"detail: source structure is embedded in entry prose for {item_id}")
        if RAW_METER_LABEL.search(displayed_english):
            errors.append(f"detail: raw poetry meter label remains for {item_id}")
        expected_headings = list(SOURCE_HEADINGS_BEFORE.get(source_entry_number, ()))
        if detail.get("headingsBefore", []) != expected_headings:
            errors.append(
                f"detail: source headings before entry {source_entry_number} differ for {item_id}"
            )
        for old, _new in SOURCE_ARABIC_APPARATUS_REPLACEMENTS.get(
            source_entry_number, ()
        ):
            if old in displayed_arabic:
                errors.append(f"detail: audited Arabic apparatus remains for {item_id}")
        if detail.get("honorificPolicyVersion") != HONORIFIC_POLICY_VERSION:
            errors.append(f"detail: wrong honorific policy version for {item_id}")
        occurrences = detail.get("honorifics")
        if not isinstance(occurrences, list):
            errors.append(f"detail: honorific occurrence metadata missing for {item_id}")
            occurrences = []
        semantic_counts = {"ar": {}, "en": {}}
        literal_counts = {"ar": {}, "en": {}}
        for occurrence in occurrences:
            semantic_id = occurrence.get("semanticId")
            entry = HONORIFIC_ENTRY_BY_ID.get(semantic_id)
            if entry is None:
                errors.append(f"detail: unknown honorific semantic ID for {item_id}")
                continue
            if occurrence.get("agreement") != entry["agreement"]:
                errors.append(f"detail: honorific agreement differs from registry for {item_id}")
            if occurrence.get("familyIncluded") != entry["familyIncluded"]:
                errors.append(f"detail: honorific family scope differs from registry for {item_id}")
            language = occurrence.get("language")
            if language not in semantic_counts:
                continue
            if occurrence.get("renderedForm") != honorific_display(entry, language):
                errors.append(f"detail: honorific rendering differs from registry for {item_id}")
            semantic_key = honorific_semantic_key(entry)
            semantic_counts[language][semantic_key] = (
                semantic_counts[language].get(semantic_key, 0) + 1
            )
            literal_counts[language][semantic_id] = (
                literal_counts[language].get(semantic_id, 0) + 1
            )
        source_semantics = dict(sorted(semantic_counts["ar"].items()))
        english_semantics = dict(sorted(semantic_counts["en"].items()))
        literal_differs = literal_counts["ar"] != literal_counts["en"]
        semantic_differs = source_semantics != english_semantics
        if remediation is not None and remediation.get("sourceHonorificSemantics") != source_semantics:
            errors.append(f"detail: source honorific semantics differ for {item_id}")
        if remediation is not None and remediation.get("englishHonorificSemantics") != english_semantics:
            errors.append(f"detail: English honorific semantics differ for {item_id}")
        if remediation is not None and remediation.get("honorificLiteralInventoryDiffers") != literal_differs:
            errors.append(f"detail: honorific literal-difference flag is wrong for {item_id}")
        expected_review = "needs_attention" if semantic_differs else "passed"
        if remediation is not None and remediation.get("honorificSemanticReview") != expected_review:
            errors.append(f"detail: honorific semantic review state is wrong for {item_id}")
        if semantic_differs and detail.get("machineAssessment") != "needs_attention":
            errors.append(f"detail: semantic honorific difference did not fail review for {item_id}")
        for character in HONORIFIC_CODEPOINT_RANGES.findall(
            f"{displayed_arabic}\n{displayed_english}"
        ):
            if character not in HONORIFIC_BY_CHARACTER:
                errors.append(f"detail: unknown compact honorific {ord(character):04X} for {item_id}")
            elif HONORIFIC_BY_CHARACTER[character]["fontSupport"] != "supported":
                errors.append(f"detail: unsupported compact honorific {ord(character):04X} for {item_id}")
        expected_search = normalize_search_text(
            "\n".join(
                [
                    str(detail.get("title", {}).get("en", "")),
                    str(detail.get("title", {}).get("ar", "")),
                ]
                + [
                    f"{segment.get('english', '')}\n{segment.get('arabic', '')}"
                    for segment in segments
                ]
            )
        )
        if item.get("searchText") != expected_search:
            errors.append(f"index: expanded honorific search text differs for {item_id}")
        serialized = json.dumps(detail, ensure_ascii=False)
        if any(pattern.search(serialized) for pattern in FORBIDDEN_PUBLIC_PATTERNS):
            errors.append(f"detail: private or unapproved expression remains for {item_id}")
        if len(detail.get("unresolved", [])) != item.get("unresolvedCount"):
            errors.append(f"detail: unresolved count differs for {item_id}")
        unresolved += int(item.get("unresolvedCount", 0))
        needs_attention += item.get("machineAssessment") == "needs_attention"
        translated += item.get("translationState") == "translated"

    if schema_version == COHORT_SCHEMA_VERSION:
        assigned = {
            item_id
            for cohort in cohorts.values()
            for item_id in cohort.get("membership", {}).get("itemIds", [])
        }
        if assigned != ids:
            errors.append("summary: cohort membership leaves records unassigned or unknown")

    quarantined_records = quarantine.get("records")
    if not isinstance(quarantined_records, list):
        errors.append("quarantine: records must be a list")
        quarantined_records = []
    quarantined_ids = {
        record.get("id") for record in quarantined_records if isinstance(record.get("id"), str)
    }
    if len(quarantined_ids) != len(quarantined_records):
        errors.append("quarantine: duplicate or invalid record IDs")
    if ids & quarantined_ids:
        errors.append("quarantine: a record is both public and quarantined")
    if any(not record.get("reasonCodes") for record in quarantined_records):
        errors.append("quarantine: every record requires a reason")
    allowed_dispositions = {
        "excluded-pending-public-source-alignment",
        "remediation-required",
    }
    if any(
        record.get("disposition") not in allowed_dispositions
        for record in quarantined_records
    ):
        errors.append("quarantine: every record requires a recognized disposition")
    source_inventory = quarantine.get("sourceInventoryCount")
    if source_inventory != len(ids) + len(quarantined_ids):
        errors.append("quarantine: public and quarantined records do not account for the source inventory")
    if quarantine.get("publicItemCount") != len(ids):
        errors.append("quarantine: public item count differs from index")
    if quarantine.get("quarantinedCount") != len(quarantined_ids):
        errors.append("quarantine: count differs from records")

    public_exclusions = exclusions.get("records")
    if not isinstance(public_exclusions, list):
        errors.append("exclusions: records must be a list")
        public_exclusions = []
    public_exclusion_ids = {
        record.get("id")
        for record in public_exclusions
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }
    if public_exclusion_ids != quarantined_ids:
        errors.append("exclusions: public records differ from quarantine accounting")
    if any(
        set(record) - {"id", "kind", "titleEn", "disposition", "reasonCodes"}
        for record in public_exclusions
        if isinstance(record, dict)
    ):
        errors.append("exclusions: a public record exposes an unexpected field")

    disposition_counts = Counter(
        record.get("disposition")
        for record in quarantined_records
        if isinstance(record, dict)
    )
    expected_exclusions = {
        "contextualPassagesPendingPublicSourceAlignment": disposition_counts[
            "excluded-pending-public-source-alignment"
        ],
        "recordsPendingRemediation": disposition_counts["remediation-required"],
    }
    if exclusions.get("counts") != expected_exclusions:
        errors.append("exclusions: disposition counts differ")

    counts = summary.get("counts", {})
    expected_counts = {
        "sourceInventory": source_inventory,
        "entries": entry_count,
        "passages": passage_count,
        "translated": translated,
        "needsAttention": needs_attention,
        "unresolvedItems": unresolved,
        "humanReviewed": human_reviewed,
        "quarantined": len(quarantined_ids),
    }
    for key, expected in expected_counts.items():
        if counts.get(key) != expected:
            errors.append(f"summary: {key} count differs")
    if summary.get("exclusions") != expected_exclusions:
        errors.append("summary: exclusion disposition counts differ")

    section_ids: set[str] = set()
    section_item_ids: list[str] = []
    detail_by_id = {
        item_id: load(root / "items" / f"{item_id}.json")
        for item_id in ids
        if (root / "items" / f"{item_id}.json").is_file()
    }
    volume_eight_opening = sorted(
        int(detail["sourceEntryNumber"])
        for detail in detail_by_id.values()
        if detail.get("volume") == 8
        and 11426 <= int(detail.get("sourceEntryNumber", 0)) <= 11481
    )
    if volume_eight_opening and volume_eight_opening != list(range(11426, 11482)):
        errors.append(
            "sections: Volume 8 pages 1-25 must contain entries 11426-11481 exactly once"
        )
    for volume in summary.get("volumes", []):
        matching_sections = {
            item.get("sectionId") for item in items if item.get("volume") == volume.get("number")
        }
        matching_entries = [
            item for item in items
            if item.get("volume") == volume.get("number") and item.get("kind") == "entry"
        ]
        matching_passages = [
            item for item in items
            if item.get("volume") == volume.get("number") and item.get("kind") == "passage"
        ]
        if len(matching_sections) != volume.get("sectionCount"):
            errors.append(f"summary: section count differs for volume {volume.get('number')}")
        if len(matching_entries) != volume.get("itemCount"):
            errors.append(f"summary: item count differs for volume {volume.get('number')}")
        if volume.get("passageCount", 0) != len(matching_passages):
            errors.append(f"summary: passage count differs for volume {volume.get('number')}")
        source_item_count = volume.get("sourceItemCount")
        item_count = volume.get("itemCount")
        availability = volume.get("availability")
        if not isinstance(source_item_count, int) or source_item_count < item_count:
            errors.append(f"summary: invalid source inventory for volume {volume.get('number')}")
        elif availability == "complete_translation" and item_count != source_item_count:
            errors.append(f"summary: complete coverage is false for volume {volume.get('number')}")
        elif availability == "selected_passages" and not (0 < item_count < source_item_count):
            errors.append(f"summary: partial coverage is false for volume {volume.get('number')}")
        elif availability == "not_translated" and item_count != 0:
            errors.append(f"summary: untranslated coverage is false for volume {volume.get('number')}")
        section_ids.update(value for value in matching_sections if isinstance(value, str))
    for section_id in sorted(section_ids):
        path = root / "sections" / f"{section_id}.json"
        if not path.is_file():
            errors.append(f"index: missing section {section_id}")
            continue
        section = load(path)
        if section.get("id") != section_id or section.get("corpusId") != corpus_id:
            errors.append(f"section: inconsistent identity for {section_id}")
        if section.get("schemaVersion") != schema_version:
            errors.append(f"section: wrong schema version for {section_id}")
        for section_item in section.get("items", []):
            if not isinstance(section_item, dict) or not isinstance(
                section_item.get("id"), str
            ):
                errors.append(f"section: invalid embedded item in {section_id}")
                continue
            section_item_id = section_item["id"]
            section_item_ids.append(section_item_id)
            if detail_by_id.get(section_item_id) != section_item:
                errors.append(
                    f"section: embedded item differs from detail {section_item_id}"
                )
    if sorted(section_item_ids) != sorted(ids):
        errors.append("sections: public items are not accounted for exactly once")
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
    expected_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*.json")
        if path.name != "manifest.json"
    }
    if manifest_paths != expected_paths:
        errors.append("manifest: file set differs from public corpus")
    if manifest.get("objectCount") != len(manifest_paths):
        errors.append("manifest: object count differs from file set")
    if schema_version == COHORT_SCHEMA_VERSION:
        expected_manifest_cohorts = [
            {"id": cohort["id"], **cohort["membership"]}
            for cohort in corpus.get("cohorts", [])
            if isinstance(cohort, dict) and isinstance(cohort.get("membership"), dict)
        ]
        if manifest.get("cohorts") != expected_manifest_cohorts:
            errors.append("manifest: cohort coverage differs from summary")
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
    print("Public corpus eligibility, quarantine accounting, and integrity are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
