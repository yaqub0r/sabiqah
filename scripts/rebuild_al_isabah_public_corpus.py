#!/usr/bin/env python3
"""Rebuild the posted Al-Isabah corpus as publicly consumable work products.

The legacy corpus is a private comparison input. No legacy Arabic, source URL,
workflow trace, or modern apparatus is copied to the output. Source-aligned
records receive Arabic from the pinned OpenITI publication base. Sabiqah's
English is retained only when it passes every public-output gate; otherwise the
record remains publicly readable in Arabic with an explicit translation gap.
Records without a reliable source identity are accounted for in quarantine.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "3.0.0"
CORPUS_ID = "al-isabah-public-openiti-5835c18-v1"
SOURCE_AUTHORITY_ID = "al-isabah-openiti-5835c18-aco-v1"
SOURCE_COMMIT = "5835c183b8bbf4ea454d5c1be2b168b669403771"
SOURCE_SHA256 = "bc9db8134c8278973967c91c00324531833f643fc0fb2c8ebe318c9ed4469eea"
SOURCE_REPOSITORY = "https://github.com/OpenITI/0875AH"
SOURCE_PATH = (
    "data/0852IbnHajarCasqalani/"
    "0852IbnHajarCasqalani.IsabaFiTamyiz/"
    "0852IbnHajarCasqalani.IsabaFiTamyiz.JK000533-ara1.mARkdown"
)
SOURCE_URL = (
    "https://github.com/OpenITI/0875AH/blob/"
    + SOURCE_COMMIT
    + "/"
    + SOURCE_PATH
)
LICENSE_SPDX = "CC-BY-NC-SA-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
DEFAULT_SOURCE_AUTHORITY = (
    Path(__file__).resolve().parents[1]
    / "evidence"
    / "source-authorities"
    / "al-isabah.v1.json"
)

ENTRY_RE = re.compile(r"^### \$+\s+(\d+)\s+(.*)$")
PAGE_RE = re.compile(r"\bPageV(\d{2})P(\d{3})\b")
MILESTONE_RE = re.compile(r"\bms\d+\b")
DIACRITICS_RE = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")
NON_ARABIC_RE = re.compile(r"[^\u0621-\u063a\u0641-\u064a]+")
FOOTNOTE_CALLOUT_RE = re.compile(r"\[?\(\d+\)\]?|\[\d+\]|[¹²³⁴⁵⁶⁷⁸⁹⁰]+")
FOOTNOTE_PARAGRAPH_RE = re.compile(
    r"^\s*(?:\[?\(\d+\)\]?|\[\d+\]|[¹²³⁴⁵⁶⁷⁸⁹⁰]+)\s*"
)
EDITORIAL_NOTE_RE = re.compile(r"\[Editorial note:.*?\]", re.I | re.S)

# These records precede the contiguous women-entry run. Their mappings were
# independently checked against title and body text. The final three correct
# false candidates found by unrestricted fuzzy matching.
SELECTED_ENTRY_MAP = {
    1805: 1802,
    2263: 2260,
    2847: 2842,
    2897: 2892,
    4321: 4306,
    5602: 5590,
    7284: 7274,
    8302: 8290,
    8695: 8680,
    8907: 8891,
    8912: 8896,
    8935: 8919,
    9027: 9013,
    9151: 9137,
    10182: 10176,
}

# Longest formula first. The replacements are typography-only ligatures whose
# Unicode names encode the complete Arabic formulas.
SOURCE_FORMULAS = (
    (re.compile(r"صلى\s+الله\s+عليه\s+وعلى\s+آله\s+وسلم"), "﵌"),
    (re.compile(r"صلى\s+الله\s+عليه\s+وآله\s+وسلم"), "﵌"),
    (re.compile(r"صلى\s+الله\s+عليه\s+وسلم"), "ﷺ"),
    (re.compile(r"رضي\s+الله\s+عنهم\s+أجمعين"), "﵃"),
    (re.compile(r"رضي\s+الله\s+عنهن"), "﵅"),
    (re.compile(r"رضي\s+الله\s+عنهما"), "﵄"),
    (re.compile(r"رضي\s+الله\s+عنهم"), "﵃"),
    (re.compile(r"رضي\s+الله\s+عنها"), "﵂"),
    (re.compile(r"رضي\s+الله\s+عنه"), "﵁"),
    (re.compile(r"عليهما\s+السلام"), "﵉"),
    (re.compile(r"عليهم\s+السلام"), "﵈"),
    (re.compile(r"عليها\s+السلام"), "﵍"),
    (re.compile(r"عليه\s+الصلاة\s+والسلام"), "﵊"),
    (re.compile(r"عليه\s+السلام"), "﵇"),
    (re.compile(r"رحمهم\s+الله"), "﵏"),
    (re.compile(r"رحمه\s+الله"), "﵀"),
    (re.compile(r"تبارك\s+وتعالى"), "﵎"),
    (re.compile(r"عز\s+وجل"), "﷿"),
)

ENGLISH_FORMULAS = (
    (
        re.compile(
            r"may (?:Allah|God) bless him and (?:his family|the members of his family) and grant (?:him|them) peace",
            re.I,
        ),
        "﵌",
    ),
    (re.compile(r"may (?:Allah|God) bless him and grant him peace", re.I), "ﷺ"),
    (re.compile(r"peace and blessings be upon him", re.I), "ﷺ"),
    (re.compile(r"blessings and peace be upon him", re.I), "ﷺ"),
    (re.compile(r"may (?:Allah|God) be pleased with them all", re.I), "﵃"),
    (re.compile(r"may (?:Allah|God) be pleased with them both", re.I), "﵄"),
    (re.compile(r"may (?:Allah|God) be pleased with them", re.I), "﵃"),
    (re.compile(r"may (?:Allah|God) be pleased with her", re.I), "﵂"),
    (re.compile(r"may (?:Allah|God) be pleased with him", re.I), "﵁"),
    (re.compile(r"peace be upon them both", re.I), "﵉"),
    (re.compile(r"peace be upon them", re.I), "﵈"),
    (re.compile(r"peace be upon her", re.I), "﵍"),
    (re.compile(r"prayers and peace be upon him", re.I), "﵊"),
    (re.compile(r"peace be upon him", re.I), "﵇"),
    (re.compile(r"may (?:Allah|God) have mercy on them", re.I), "﵏"),
    (re.compile(r"may (?:Allah|God) have mercy on him", re.I), "﵀"),
    (re.compile(r"blessed and exalted is He", re.I), "﵎"),
    (re.compile(r"(?:Allah|God),? (?:the )?[Mm]ighty and [Mm]ajestic", re.I), "Allah ﷿"),
)

FORMULA_TOKENS = ("ﷺ", "﵌", "﵀", "﵁", "﵂", "﵃", "﵄", "﵅", "﵇", "﵈", "﵉", "﵊", "﵎", "﵏", "﷿")
ARABIC_TEXT_FORMULAS: tuple[str, ...] = ()
FORMULA_OCCURRENCE_RE = re.compile(
    r"(?:Allah|الله)\s+تعالى|"
    + "|".join(
        re.escape(token) for token in (*FORMULA_TOKENS, *ARABIC_TEXT_FORMULAS)
    )
)
FORBIDDEN_PUBLIC_PATTERNS = (
    re.compile(r"usul\.ai", re.I),
    re.compile(r"\[Editorial note:", re.I),
    re.compile(r"al-isabah:(?:entry|passage):", re.I),
    re.compile(r"f12585cea28d7c7b318728f74b1a95a0d8b2812cb25d6e70f1b9e7b0b9422a3f", re.I),
    re.compile(r"(?:omitted|reads|added) in manuscript", re.I),
    re.compile(r"in manuscripts? [A-Z](?:\b|-)", re.I),
    re.compile(r"canonical (?:Arabic|text) reads", re.I),
)


@dataclass(frozen=True)
class OpenITIEntry:
    number: int
    clean: str
    rendered: str
    pages: tuple[tuple[int, int], ...]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def reset_output(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)


def validate_source_authority_record(path: Path) -> None:
    record = json.loads(path.read_text(encoding="utf-8"))
    machine = record.get("machineText", {})
    binding = record.get("sourceBinding", {})
    expected = {
        "authorityId": (record.get("authorityId"), SOURCE_AUTHORITY_ID),
        "assessment.status": (
            record.get("assessment", {}).get("status"),
            "approved-for-publication",
        ),
        "sourceBinding.mode": (
            binding.get("mode"),
            "licensed-machine-text-with-independent-facsimile-witness",
        ),
        "sourceBinding.humanViewableAuthority": (
            binding.get("humanViewableAuthority"),
            "machineText",
        ),
        "sourceBinding.sameEditionFacsimileApproved": (
            binding.get("sameEditionFacsimileApproved"),
            False,
        ),
        "machineText.repository": (machine.get("repository"), SOURCE_REPOSITORY),
        "machineText.commit": (machine.get("commit"), SOURCE_COMMIT),
        "machineText.path": (machine.get("path"), SOURCE_PATH),
        "machineText.sha256": (machine.get("sha256"), SOURCE_SHA256),
        "machineText.license.spdx": (
            machine.get("license", {}).get("spdx"),
            LICENSE_SPDX,
        ),
        "machineText.license.url": (
            machine.get("license", {}).get("url"),
            LICENSE_URL,
        ),
    }
    mismatches = [
        name for name, (actual, required) in expected.items() if actual != required
    ]
    if mismatches:
        raise ValueError(
            "Source-authority record does not match the public corpus contract: "
            + ", ".join(mismatches)
        )


def normalize_arabic(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = DIACRITICS_RE.sub("", value)
    value = value.translate(
        str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ؤ": "و", "ئ": "ي", "ة": "ه"})
    )
    return " ".join(NON_ARABIC_RE.sub(" ", value).split())


def render_source_formulas(value: str) -> str:
    for pattern, replacement in SOURCE_FORMULAS:
        value = pattern.sub(replacement, value)
    return value


def parse_openiti(path: Path) -> dict[int, OpenITIEntry]:
    if hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("OpenITI input does not match the approved pinned SHA-256")
    entries: list[OpenITIEntry] = []
    number: int | None = None
    lines: list[str] = []
    entry_pages: list[tuple[int, int]] = []
    current_page: tuple[int, int] | None = None

    def flush() -> None:
        nonlocal number, lines, entry_pages
        if number is None:
            return
        value = "\n".join(lines)
        value = PAGE_RE.sub("", value)
        value = MILESTONE_RE.sub("", value)
        value = re.sub(r"^### \$+\s+\d+\s+", "", value)
        value = re.sub(r"(?m)^(?:#|~~)\s?", "", value)
        value = value.replace("|", " ")
        clean = " ".join(value.split())
        pages = tuple(dict.fromkeys(entry_pages))
        entries.append(
            OpenITIEntry(
                number=number,
                clean=clean,
                rendered=render_source_formulas(clean),
                pages=pages,
            )
        )

    for line in path.read_text(encoding="utf-8").splitlines():
        before_page = current_page
        page_matches = [(int(volume), int(page)) for volume, page in PAGE_RE.findall(line)]
        match = ENTRY_RE.match(line)
        if match:
            flush()
            number = int(match.group(1))
            lines = [line]
            entry_pages = []
            if before_page is not None:
                entry_pages.append(before_page)
            entry_pages.extend(page_matches)
        elif number is not None:
            if line.startswith("### ") and not line.startswith("### $"):
                if page_matches:
                    entry_pages.extend(page_matches)
                current_page = page_matches[-1] if page_matches else current_page
                continue
            lines.append(line)
            entry_pages.extend(page_matches)
        if page_matches:
            current_page = page_matches[-1]
    flush()
    return {entry.number: entry for entry in entries}


def source_entry_number(legacy_number: int) -> int | None:
    if legacy_number in SELECTED_ENTRY_MAP:
        return SELECTED_ENTRY_MAP[legacy_number]
    if 10759 <= legacy_number <= 11428:
        return legacy_number - 6
    if 11429 <= legacy_number <= 12308:
        return legacy_number - 4
    return None


def legacy_arabic_core(item: dict[str, Any]) -> str:
    parts = []
    for segment in item.get("segments", []):
        value = str(segment.get("arabic", "")).split("_________", 1)[0]
        paragraphs = re.split(r"\n\s*\n|\n(?=\s*\(\s*[٠-٩0-9]+\s*\)\s)", value)
        value = "\n".join(
            paragraph
            for paragraph in paragraphs
            if not re.match(r"^\s*\(\s*[٠-٩0-9]+\s*\)\s", paragraph)
        )
        parts.append(value)
    return "\n".join(parts)


def clean_arabic_title(value: str) -> str:
    value = re.sub(r"^[\s٠-٩0-9]+[-—]?\s*", "", value)
    value = re.sub(r"^[مز]\s*[-—]\s*", "", value)
    value = re.sub(r"[«\[]\s*[٠-٩0-9]+\s*[»\]]", "", value)
    value = FOOTNOTE_CALLOUT_RE.sub("", value)
    return value.strip(" \t\r\n،,:؛.-—")


def clean_english_title(value: str) -> str:
    value = re.sub(r"^[\s0-9]+[-—]?\s*", "", value)
    value = FOOTNOTE_CALLOUT_RE.sub("", value)
    return render_english_formulas(
        " ".join(value.strip(" \t\r\n,:;.-—").split())
    )


def public_arabic_title(source: OpenITIEntry, legacy_title: str) -> str:
    word_count = max(1, len(clean_arabic_title(legacy_title).split()))
    return " ".join(source.rendered.split()[:word_count])


def public_arabic_body(source: OpenITIEntry, title: str) -> str:
    words = source.rendered.split()
    return " ".join(words[len(title.split()) :])


def render_english_formulas(value: str) -> str:
    for pattern, replacement in ENGLISH_FORMULAS:
        value = pattern.sub(replacement, value)
    value = re.sub(r"\(([ﷺ-﷿﵀-﵏])\)", r"\1", value)
    value = re.sub(r"\b(?:Allah|God) Most High\b", "Allah تعالى", value, flags=re.I)
    return value


def sanitize_english(item: dict[str, Any]) -> tuple[str, dict[str, int]]:
    removed_notes = 0
    removed_editorial = 0
    kept: list[str] = []
    title = clean_english_title(str(item.get("title", {}).get("en", "")))
    for segment in item.get("segments", []):
        value = str(segment.get("english", "")).split("_________", 1)[0]
        editorial = list(EDITORIAL_NOTE_RE.finditer(value))
        removed_editorial += len(editorial)
        value = EDITORIAL_NOTE_RE.sub("", value)
        paragraphs = re.split(r"\n\s*\n", value)
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if FOOTNOTE_PARAGRAPH_RE.match(paragraph):
                removed_notes += 1
                continue
            paragraph = FOOTNOTE_CALLOUT_RE.sub("", paragraph)
            paragraph = re.sub(r"^\s*\d+\s*[-—]\s*", "", paragraph)
            paragraph = " ".join(paragraph.split())
            paragraph = render_english_formulas(paragraph)
            if not paragraph:
                continue
            if title and paragraph.casefold().startswith(title.casefold()):
                paragraph = paragraph[len(title) :].lstrip(" \t\r\n,:;.-—")
                if not paragraph:
                    continue
            kept.append(paragraph)
    value = render_english_formulas("\n\n".join(kept)).strip()
    return value, {
        "removedApparatusParagraphs": removed_notes,
        "removedEditorialNotes": removed_editorial,
    }


def formula_counts(value: str) -> dict[str, int]:
    counts = {token: value.count(token) for token in FORMULA_TOKENS if value.count(token)}
    allah_taala = len(re.findall(r"(?:الله|Allah)\s+تعالى", value))
    if allah_taala:
        counts["Allah تعالى"] = allah_taala
    for formula in ARABIC_TEXT_FORMULAS:
        if value.count(formula):
            counts[formula] = value.count(formula)
    return counts


def formula_sequence(value: str) -> list[str]:
    return [
        "Allah تعالى" if "تعالى" in match.group(0) else match.group(0)
        for match in FORMULA_OCCURRENCE_RE.finditer(value)
    ]


def align_formula_types(
    source: OpenITIEntry, title: str, english: str
) -> tuple[str, str, int]:
    source_sequence = formula_sequence(source.rendered)
    combined = f"{title}\u0000{english}"
    english_sequence = formula_sequence(combined)
    if len(source_sequence) != len(english_sequence) or source_sequence == english_sequence:
        return title, english, 0
    position = 0

    def replace(_match: re.Match[str]) -> str:
        nonlocal position
        replacement = source_sequence[position]
        position += 1
        return replacement

    aligned = FORMULA_OCCURRENCE_RE.sub(replace, combined)
    aligned_title, aligned_english = aligned.split("\u0000", 1)
    corrections = sum(left != right for left, right in zip(source_sequence, english_sequence))
    return aligned_title, aligned_english, corrections


def item_alignment(item: dict[str, Any], source: OpenITIEntry) -> tuple[float, float]:
    legacy = normalize_arabic(legacy_arabic_core(item))
    public = normalize_arabic(source.clean)
    title = normalize_arabic(clean_arabic_title(str(item.get("title", {}).get("ar", ""))))
    title_score = SequenceMatcher(
        None, title[:180], public[: len(title[:180])], autojunk=False
    ).ratio()
    body_score = SequenceMatcher(None, legacy[:500], public[:500], autojunk=False).ratio()
    return title_score, body_score


def public_item(
    legacy: dict[str, Any],
    source: OpenITIEntry,
    title_en: str,
    english: str,
    title_score: float,
    body_score: float,
    removals: dict[str, int],
    formula_type_corrections: int,
    english_exclusion_reasons: list[str],
) -> dict[str, Any]:
    legacy_number = int(legacy["printedEntryNumber"])
    title_ar = public_arabic_title(source, str(legacy["title"]["ar"]))
    arabic_body = public_arabic_body(source, title_ar)
    page = source.pages[0] if source.pages else (1, 0)
    unresolved = []
    if legacy.get("unresolved"):
        unresolved.append(
            {
                "category": "legacy-review-finding",
                "explanation": "The earlier workflow recorded one or more unresolved findings. Restricted evidence remains available in the private reviewer package.",
                "priority": "review",
            }
        )
    if english_exclusion_reasons:
        unresolved.append(
            {
                "category": "translation-withheld",
                "explanation": "The legacy English did not pass the public-output gates and is not displayed. The approved Arabic remains available for a new or corrected translation.",
                "priority": "review",
            }
        )
    source_sha = sha256_text(source.rendered)
    alignment_score = round(body_score, 4)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "corpusId": CORPUS_ID,
        "id": legacy["id"],
        "kind": "entry",
        "sequence": legacy_number,
        "printedEntryNumber": source.number,
        "sourceEntryNumber": source.number,
        "volume": page[0],
        "title": {"en": title_en, "ar": title_ar},
        "translationState": "translated" if english else "untranslated",
        "machineAssessment": "needs_attention" if unresolved or not english else "passed",
        "humanReview": "unreviewed",
        "publicEligibility": "eligible",
        "segments": [
            {
                "id": f"{legacy['id']}-public-segment-0001",
                "arabic": arabic_body,
                "english": english,
                "pages": [
                    {
                        "volume": page[0],
                        "printedPage": page[1] or None,
                        "readerPage": None,
                        "providerPage": SOURCE_URL,
                    }
                ],
                "machineState": (
                    "public_source_remediated_unreviewed"
                    if english
                    else "public_source_remediated_untranslated"
                ),
            }
        ],
        "names": [],
        "unresolved": unresolved,
        "workflowStages": [
            {
                "stage": "source_alignment",
                "state": "complete",
                "summary": f"The stable record was aligned to OpenITI entry {source.number}; restricted Arabic was replaced rather than republished.",
            },
            {
                "stage": "adjudication",
                "state": "complete",
                "summary": (
                    "The legacy English did not pass every public-output gate and was withheld; only the approved Arabic is displayed."
                    if english_exclusion_reasons
                    else "Sabiqah-authored English was retained only after modern apparatus and private workflow expression were removed."
                ),
            },
            {
                "stage": "machine_validation",
                "state": "needs_attention" if unresolved else "complete",
                "summary": "Public-source alignment, apparatus exclusion, provenance, and honorific inventories passed automated validation.",
            },
            {
                "stage": "human_review",
                "state": "pending",
                "summary": "The publicly readable working translation has not yet received human scholarly approval.",
            },
            {
                "stage": "compliance_promotion",
                "state": "blocked",
                "summary": "Canonical promotion remains separate and requires human review plus receiving-repository approval.",
            },
        ],
        "source": {
            "authorityId": SOURCE_AUTHORITY_ID,
            "entryNumber": source.number,
            "pages": [f"V{volume:02d}P{printed_page:03d}" for volume, printed_page in source.pages],
            "sourceTextSha256": source_sha,
            "sourceUrl": SOURCE_URL,
            "license": {"spdx": LICENSE_SPDX, "url": LICENSE_URL},
            "alignment": {
                "method": "stable-sequence-map-and-normalized-body-comparison-v1",
                "titleScore": round(title_score, 4),
                "bodyScore": alignment_score,
            },
        },
        "remediation": {
            "legacyAllocationNumber": legacy_number,
            "sourceArabicReplaced": True,
            "privateLocatorsRemoved": True,
            "honorificInventory": formula_counts(source.rendered),
            "honorificTypeCorrections": formula_type_corrections,
            "englishExcluded": bool(english_exclusion_reasons),
            "englishExclusionReasonCodes": sorted(set(english_exclusion_reasons)),
            **removals,
        },
        "provenance": {
            "sourceAuthorityId": SOURCE_AUTHORITY_ID,
            "sourceArtifactSha256": SOURCE_SHA256,
            "sourceTextSha256": source_sha,
        },
    }


def printed_page_bounds(item: dict[str, Any]) -> tuple[int | None, int | None]:
    pages = [
        page["printedPage"]
        for segment in item["segments"]
        for page in segment["pages"]
        if page["printedPage"] is not None
    ]
    return (min(pages), max(pages)) if pages else (None, None)


def list_item(item: dict[str, Any], section_id: str) -> dict[str, Any]:
    page_start, page_end = printed_page_bounds(item)
    return {
        "id": item["id"],
        "kind": item["kind"],
        "sequence": item["sequence"],
        "printedEntryNumber": item["printedEntryNumber"],
        "sourceEntryNumber": item["sourceEntryNumber"],
        "volume": item["volume"],
        "printedPageStart": page_start,
        "printedPageEnd": page_end,
        "sectionId": section_id,
        "titleEn": item["title"]["en"],
        "titleAr": item["title"]["ar"],
        "translationState": item["translationState"],
        "machineAssessment": item["machineAssessment"],
        "humanReview": item["humanReview"],
        "publicEligibility": item["publicEligibility"],
        "unresolvedCount": len(item["unresolved"]),
    }


def quarantine_record(
    legacy: dict[str, Any], source_number: int | None, reasons: list[str]
) -> dict[str, Any]:
    return {
        "id": legacy["id"],
        "kind": legacy.get("kind", "entry"),
        "legacyAllocationNumber": legacy.get("printedEntryNumber"),
        "candidateSourceEntryNumber": source_number,
        "reasonCodes": sorted(set(reasons)),
    }


def build_sections(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sections: list[dict[str, Any]] = []
    volumes: list[dict[str, Any]] = []
    for volume in sorted({item["volume"] for item in items}):
        volume_items = [item for item in items if item["volume"] == volume]
        grouped: dict[int, list[dict[str, Any]]] = {}
        for item in volume_items:
            page_start, _ = printed_page_bounds(item)
            bucket = ((page_start or 1) - 1) // 25
            grouped.setdefault(bucket, []).append(item)
        ordered_groups = sorted(grouped.items())
        total = len(ordered_groups)
        volume_pages = [page for item in volume_items for page in printed_page_bounds(item) if page is not None]
        volumes.append(
            {
                "id": f"volume-{volume:02d}",
                "number": volume,
                "label": f"Volume {volume}",
                "availability": "selected_passages",
                "itemCount": len(volume_items),
                "sectionCount": total,
                "firstPrintedPage": min(volume_pages) if volume_pages else None,
                "lastPrintedPage": max(volume_pages) if volume_pages else None,
                "description": "Publicly consumable working entries; this is partial coverage rather than a complete translated volume.",
            }
        )
        for position, (bucket, section_items) in enumerate(ordered_groups, start=1):
            start = bucket * 25 + 1
            end = start + 24
            section_id = f"volume-{volume:02d}-pages-{start:04d}-{end:04d}"
            pages = [page for item in section_items for page in printed_page_bounds(item) if page is not None]
            sections.append(
                {
                    "schemaVersion": SCHEMA_VERSION,
                    "corpusId": CORPUS_ID,
                    "id": section_id,
                    "volume": volume,
                    "label": f"Pages {start}–{end}",
                    "availability": "selected_passages",
                    "position": position,
                    "totalSections": total,
                    "printedPageStart": min(pages) if pages else None,
                    "printedPageEnd": max(pages) if pages else None,
                    "previousSectionId": (
                        f"volume-{volume:02d}-pages-{(ordered_groups[position - 2][0] * 25 + 1):04d}-{(ordered_groups[position - 2][0] * 25 + 25):04d}"
                        if position > 1
                        else None
                    ),
                    "nextSectionId": (
                        f"volume-{volume:02d}-pages-{(ordered_groups[position][0] * 25 + 1):04d}-{(ordered_groups[position][0] * 25 + 25):04d}"
                        if position < total
                        else None
                    ),
                    "items": section_items,
                }
            )
    return sections, volumes


def rebuild(legacy_root: Path, openiti_path: Path, output: Path, generated_at: str) -> dict[str, Any]:
    reset_output(output)
    openiti = parse_openiti(openiti_path)
    legacy_items = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((legacy_root / "items").glob("*.json"))
    ]
    eligible: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    for legacy in legacy_items:
        if legacy.get("kind") != "entry" or not isinstance(legacy.get("printedEntryNumber"), int):
            quarantined.append(quarantine_record(legacy, None, ["no-approved-entry-alignment"]))
            continue
        mapped_number = source_entry_number(int(legacy["printedEntryNumber"]))
        source = openiti.get(mapped_number) if mapped_number is not None else None
        reasons: list[str] = []
        english_exclusion_reasons: list[str] = []
        if source is None:
            reasons.append("no-approved-entry-alignment")
            title_score = body_score = 0.0
        else:
            title_score, body_score = item_alignment(legacy, source)
            legacy_length = len(normalize_arabic(legacy_arabic_core(legacy)))
            source_length = len(normalize_arabic(source.clean))
            short_exact_title = title_score >= 0.95 and min(legacy_length, source_length) <= 150
            exact_title_with_substantial_body_overlap = (
                title_score >= 0.995 and body_score >= 0.60
            )
            if (
                body_score < 0.70
                and not short_exact_title
                and not exact_title_with_substantial_body_overlap
            ):
                reasons.append("source-alignment-below-threshold")
        english, removals = sanitize_english(legacy)
        title_en = clean_english_title(str(legacy.get("title", {}).get("en", "")))
        formula_type_corrections = 0
        if source is not None:
            title_en, english, formula_type_corrections = align_formula_types(
                source, title_en, english
            )
        if source is not None and formula_counts(source.rendered) != formula_counts(
            f"{title_en}\n{english}"
        ):
            english_exclusion_reasons.append("honorific-inventory-mismatch")
        if removals["removedEditorialNotes"]:
            english_exclusion_reasons.append("unsupported-editorial-intervention")
        if any(pattern.search(english) for pattern in FORBIDDEN_PUBLIC_PATTERNS):
            english_exclusion_reasons.append("unapproved-apparatus-remains")
        if reasons or source is None:
            quarantined.append(quarantine_record(legacy, mapped_number, reasons))
            continue
        if not english:
            english_exclusion_reasons.append("no-retainable-translation")
        if english_exclusion_reasons:
            title_en = f"Entry {source.number}"
            english = ""
        eligible.append(
            public_item(
                legacy,
                source,
                title_en,
                english,
                title_score,
                body_score,
                removals,
                formula_type_corrections,
                english_exclusion_reasons,
            )
        )

    eligible.sort(key=lambda item: (item["volume"], printed_page_bounds(item)[0] or 0, item["sourceEntryNumber"]))
    sections, volumes = build_sections(eligible)
    section_by_item = {
        item["id"]: section["id"]
        for section in sections
        for item in section["items"]
    }
    list_items = [list_item(item, section_by_item[item["id"]]) for item in eligible]
    unresolved_count = sum(item["unresolvedCount"] for item in list_items)
    needs_attention = sum(item["machineAssessment"] == "needs_attention" for item in list_items)
    summary = {
        "schemaVersion": SCHEMA_VERSION,
        "work": {
            "slug": "al-isabah",
            "titleAr": "الإصابة في تمييز الصحابة",
            "titleEn": "Al-Isabah fi Tamyiz al-Sahabah",
        },
        "corpus": {
            "id": CORPUS_ID,
            "sourceRepository": SOURCE_REPOSITORY,
            "sourceCommit": SOURCE_COMMIT,
            "sourceAuthorityId": SOURCE_AUTHORITY_ID,
            "sourceArtifactSha256": SOURCE_SHA256,
            "generatedAt": generated_at,
            "publicationStatus": "public-working",
            "promotionStatus": "blocked",
            "license": {"spdx": LICENSE_SPDX, "url": LICENSE_URL},
        },
        "counts": {
            "sourceInventory": len(legacy_items),
            "entries": len(eligible),
            "passages": 0,
            "translated": sum(item["translationState"] == "translated" for item in eligible),
            "needsAttention": needs_attention,
            "unresolvedItems": unresolved_count,
            "humanReviewed": 0,
            "quarantined": len(quarantined),
        },
        "volumes": volumes,
    }
    index = {"schemaVersion": SCHEMA_VERSION, "corpusId": CORPUS_ID, "items": list_items}
    quarantine = {
        "schemaVersion": "1.0.0",
        "corpusId": CORPUS_ID,
        "sourceInventoryCount": len(legacy_items),
        "publicItemCount": len(eligible),
        "quarantinedCount": len(quarantined),
        "reasonCounts": dict(
            sorted(Counter(reason for record in quarantined for reason in record["reasonCodes"]).items())
        ),
        "records": sorted(quarantined, key=lambda record: record["id"]),
    }
    write_json(output / "summary.json", summary)
    write_json(output / "index.json", index)
    write_json(output / "quarantine.json", quarantine)
    for item in eligible:
        write_json(output / "items" / f"{item['id']}.json", item)
    for section in sections:
        write_json(output / "sections" / f"{section['id']}.json", section)

    files = []
    for path in sorted(path for path in output.rglob("*.json") if path.name != "manifest.json"):
        relative = path.relative_to(output).as_posix()
        files.append(
            {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
        )
    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "corpusId": CORPUS_ID,
        "sourceAuthorityId": SOURCE_AUTHORITY_ID,
        "sourceArtifactSha256": SOURCE_SHA256,
        "generatedAt": generated_at,
        "objectCount": len(files),
        "files": files,
    }
    write_json(output / "manifest.json", manifest)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-corpus", required=True, type=Path)
    parser.add_argument("--openiti", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--source-authority", type=Path, default=DEFAULT_SOURCE_AUTHORITY
    )
    parser.add_argument(
        "--generated-at",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    args = parser.parse_args()
    validate_source_authority_record(args.source_authority.resolve())
    summary = rebuild(
        args.legacy_corpus.resolve(),
        args.openiti.resolve(),
        args.output.resolve(),
        args.generated_at,
    )
    print(
        f"Rebuilt {summary['counts']['entries']} public entries; "
        f"quarantined {summary['counts']['quarantined']} of "
        f"{summary['counts']['sourceInventory']} posted records."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
