#!/usr/bin/env python3
"""Rebuild the posted Al-Isabah corpus as publicly consumable work products.

The legacy corpus is a private comparison input. No legacy Arabic, source URL,
workflow trace, or modern apparatus is copied to the output. Source-aligned
records receive Arabic from the pinned OpenITI publication base. Sabiqah's
English is retained as public working text after private apparatus is removed
and unsupported emendations are returned to the pinned source wording.
Honorific differences become review evidence rather than hidden output. Records
without a reliable source identity are accounted for in quarantine.json.
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


SCHEMA_VERSION = "4.0.0"
CORPUS_ID = "al-isabah-public-openiti-5835c18-v8"
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
DEFAULT_ENTRY_TITLE_PROFILE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "releases"
    / "al-isabah-entry-title-profile.v2.json"
)
ENTRY_TITLE_PROFILE_SOURCE = {
    "repository": "https://github.com/yaqub0r/al-isabah",
    "commit": "29c39e3f5428d1d00f3dcff11e674feb96c6d19b",
    "path": "profiles/entry-title-decisions.v2.json",
    "sha256": "818a0a1ad51fd898839f7f65374879afe18edde6bb47fcfd04ba536987c21898",
    "semanticSha256": "0e69aea83c096f9d9540d64d729c8d61879106b2ff73cb0ffb5ea4d6921d8ff3",
}
HONORIFIC_REGISTRY_PATH = (
    Path(__file__).resolve().parents[1]
    / "packages"
    / "release-model"
    / "src"
    / "honorifics.registry.json"
)
HONORIFIC_REGISTRY = json.loads(
    HONORIFIC_REGISTRY_PATH.read_text(encoding="utf-8")
)
HONORIFIC_POLICY_VERSION = str(HONORIFIC_REGISTRY["schemaVersion"])
HONORIFIC_ENTRIES: tuple[dict[str, Any], ...] = tuple(
    HONORIFIC_REGISTRY["entries"]
)
HONORIFIC_BY_CHARACTER = {
    character: entry
    for entry in HONORIFIC_ENTRIES
    for character in (entry["compactCharacter"], *entry["alternateCharacters"])
}

ENTRY_RE = re.compile(r"^### \$+\s+(\d+)\s+(.*)$")
PAGE_RE = re.compile(r"\bPageV(\d{2})P(\d{3})\b")
MILESTONE_RE = re.compile(r"\bms\d+\b")
DIACRITICS_RE = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")
NON_ARABIC_RE = re.compile(r"[^\u0621-\u063a\u0641-\u064a]+")
FOOTNOTE_CALLOUT_RE = re.compile(r"\[?\(\d+\)\]?|\[\d+\]|[¹²³⁴⁵⁶⁷⁸⁹⁰]+")
FOOTNOTE_PARAGRAPH_RE = re.compile(
    r"^\s*(?:\[?\(\d+\)\]?|\[\d+\]|[¹²³⁴⁵⁶⁷⁸⁹⁰]+)\s*"
)
EDITORIAL_NOTE_RE = re.compile(r"\[(?:Editorial|Textual) note:.*?\]", re.I | re.S)
STRUCTURAL_HEADING_PARAGRAPH_RE = re.compile(
    r"^(?:THE LETTER\b.*|(?:THE\s+)?(?:SECOND\s+AND\s+THIRD\s+SECTIONS|SECOND,\s+THIRD,\s+AND\s+FOURTH\s+SECTIONS|SECTION\s+(?:ONE|TWO|THREE|FOUR)|FOURTH\s+SECTION)|NO ONE WAS MENTIONED IN (?:EITHER|ANY) OF THEM\.?\s*)$",
    re.I,
)
METER_LABEL_RE = re.compile(
    r"\[(?:al-)?(rajaz|tawil|basit)(?: meter)?\]|\[al-([A-Za-z-]+) meter\]",
    re.I,
)
METER_PARAGRAPH_RE = re.compile(
    r"^\[(?:al-)?(rajaz|tawil|basit)(?: meter)?\]$|^\[al-([A-Za-z-]+) meter\]$",
    re.I,
)


def display_meter(value: str) -> str:
    names = {"tawil": "Ṭawīl", "rajaz": "Rajaz", "basit": "Basit"}
    normalized = value.strip().casefold()
    return f"Meter: al-{names.get(normalized, value.strip().title())}"

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

FORBIDDEN_PUBLIC_PATTERNS = (
    re.compile(r"usul\.ai", re.I),
    re.compile(r"\[(?:Editorial|Textual) note:", re.I),
    re.compile(r"al-isabah:(?:entry|passage):", re.I),
    re.compile(r"f12585cea28d7c7b318728f74b1a95a0d8b2812cb25d6e70f1b9e7b0b9422a3f", re.I),
    re.compile(r"(?:omitted|reads|added) in manuscript", re.I),
    re.compile(r"in manuscripts? [A-Z](?:\b|-)", re.I),
    re.compile(r"canonical (?:Arabic|text) reads", re.I),
)

SOURCE_HEADINGS_BEFORE: dict[int, tuple[dict[str, str], ...]] = {
    11431: (
        {"level": "section", "ar": "القسم الثاني والقسم الثالث", "en": "Sections Two and Three", "noteAr": "لم يذكر فيهما أحد", "noteEn": "No entries are recorded in either section."},
        {"level": "section", "ar": "الرابع", "en": "Section Four"},
    ),
    11433: (
        {"level": "letter", "ar": "حرف الطاء المهملة", "en": "Letter Ṭāʾ (ط)"},
        {"level": "section", "ar": "الأول", "en": "Section One"},
    ),
    11438: (
        {"level": "section", "ar": "القسم الثاني", "en": "Section Two", "noteAr": "لم يذكر فيه أحد", "noteEn": "No entries are recorded in this section."},
        {"level": "section", "ar": "الثالث", "en": "Section Three"},
    ),
    11441: (
        {"level": "letter", "ar": "حرف الظاء المشالة", "en": "Letter Ẓāʾ (ظ)"},
        {"level": "section", "ar": "الأول", "en": "Section One"},
    ),
    11445: (
        {"level": "section", "ar": "القسم الثاني والقسم الثالث والقسم الرابع", "en": "Sections Two, Three, and Four", "noteAr": "لم يذكر فيها أحد", "noteEn": "No entries are recorded in these sections."},
        {"level": "letter", "ar": "العين المهملة", "en": "Letter ʿAyn (ع)"},
        {"level": "section", "ar": "القسم الأول", "en": "Section One"},
    ),
}

# Exact, source-entry-scoped removal of modern page/callout numerals that are
# embedded inside words in the approved digital source. The untouched source
# bytes remain bound by sourceExactTextSha256; only the public projection is
# repaired and the decision is recorded on the entry.
SOURCE_ARABIC_APPARATUS_REPLACEMENTS: dict[int, tuple[tuple[str, str], ...]] = {
    11448: (("عبد الله 327 بن الزبير", "عبد الله بن الزبير"),),
    11456: (("نكح 328 رسول الله", "نكح رسول الله"),),
    11457: (("زيد 329 بن خالد", "زيد بن خالد"),),
    11472: (
        ("ألا 33 تشرك", "ألا تشرك"),
        ("ولا تسرق 33 ولا تزني", "ولا تسرق ولا تزني"),
    ),
}

ENGLISH_HONORIFIC_SOURCE_CORRECTIONS: dict[int, tuple[tuple[str, str], ...]] = {
    11457: (
        (
            "may Allah Most High be pleased with them",
            "may Allah be pleased with them",
        ),
    ),
    11473: (
        (
            "may Allah Most High bless him and grant him peace",
            "may Allah bless him and grant him peace",
        ),
    ),
}

ENGLISH_PRESENTATION_SOURCE_REPAIRS: dict[int, tuple[tuple[str, str], ...]] = {
    11446: (
        (
            "Word was sent by Umar ibn...\n\n…ibn al-Khattab sent",
            "Umar ibn al-Khattab sent",
        ),
    ),
}


@dataclass(frozen=True)
class OpenITIEntry:
    number: int
    exact: str
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


def load_entry_title_profile(
    path: Path = DEFAULT_ENTRY_TITLE_PROFILE,
) -> dict[int, dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schemaVersion") != "1.0.0":
        raise ValueError("Entry-title profile pin has an unsupported schema")
    if document.get("source") != ENTRY_TITLE_PROFILE_SOURCE:
        raise ValueError("Entry-title profile does not match the pinned Al-Isabah artifact")
    profile = document.get("profile", {})
    semantic_sha = hashlib.sha256(
        json.dumps(
            profile, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    if semantic_sha != ENTRY_TITLE_PROFILE_SOURCE["semanticSha256"]:
        raise ValueError("Embedded entry-title profile differs from its pinned semantics")
    expected = {
        "schemaVersion": "1.0.0",
        "contractId": "al-isabah-entry-title-structure",
        "workId": "ibn-hajar-al-isabah",
        "status": "active",
    }
    if any(profile.get(key) != value for key, value in expected.items()):
        raise ValueError("Entry-title profile identity or status is invalid")
    authority = profile.get("sourceAuthority", {})
    if (
        authority.get("repository") != SOURCE_REPOSITORY
        or authority.get("commit") != SOURCE_COMMIT
        or authority.get("license") != LICENSE_SPDX
    ):
        raise ValueError("Entry-title profile uses a different public source authority")
    decisions: dict[int, dict[str, Any]] = {}
    for decision in profile.get("decisions", []):
        number = decision.get("sourceEntryNumber")
        title = decision.get("title", {})
        opening = decision.get("bodyOpening", {})
        if not isinstance(number, int) or number < 1 or number in decisions:
            raise ValueError("Entry-title decisions require unique positive source numbers")
        if decision.get("bodyOpeningKind") not in {"lineage", "prose"}:
            raise ValueError(f"Entry-title decision {number} has an invalid body block kind")
        if any(not str(value.get(language, "")).strip() for value in (title, opening) for language in ("ar", "en")):
            raise ValueError(f"Entry-title decision {number} is not bilingual")
        decisions[number] = decision
    if set(decisions) != {
        11426, 11427, 11430, 11436, 11439, 11441, 11442, 11443,
        11445, 11446, 11449, 11451, 11454, 11458, 11459, 11473,
        11474, 11476,
    }:
        raise ValueError("Entry-title profile does not cover the contracted audit set")
    return decisions


def honorific_display(entry: dict[str, Any], language: str) -> str:
    if entry["fontSupport"] == "supported":
        return str(entry["compactCharacter"])
    if language == "en":
        return str(entry["accessibleEnglish"])
    return str(entry["expandedArabic"])


def compact_registry_aliases(value: str, language: str) -> str:
    """Compact formulaic aliases without changing their semantic identity.

    Unsupported Unicode 17 characters deliberately remain expanded in the
    reading language. Divine aliases that include the name Allah or God retain
    that name because the Unicode character represents the following
    exaltation, not the name itself.
    """

    grouped: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    key = "englishAliases" if language == "en" else "arabicAliases"
    for entry in HONORIFIC_ENTRIES:
        for raw_alias in entry[key]:
            alias = str(raw_alias)
            lookup = alias.casefold() if language == "en" else alias
            grouped.setdefault(lookup, []).append((alias, entry))
    aliases: dict[str, tuple[str, dict[str, Any]]] = {}
    for lookup, candidates in grouped.items():
        semantic_keys = {
            honorific_semantic_key(entry) for _alias, entry in candidates
        }
        if len(semantic_keys) > 1:
            continue
        aliases[lookup] = next(
            (
                candidate
                for candidate in candidates
                if candidate[1]["fontSupport"] == "supported"
            ),
            candidates[0],
        )
    if not aliases:
        return value
    aliases_pattern = "|".join(
        re.escape(alias)
        for alias, _entry in sorted(
            aliases.values(), key=lambda candidate: len(candidate[0]), reverse=True
        )
    )
    pattern = re.compile(
        (
            rf"(?P<leading>(?:,[\t ]*|—[\t ]*))?(?P<alias>{aliases_pattern})(?P<trailing>(?:[\t ]*,|[\t ]*—))?"
            if language == "en"
            else rf"(?P<alias>{aliases_pattern})"
        ),
        re.I if language == "en" else 0,
    )

    def replace(match: re.Match[str]) -> str:
        matched_alias = match.group("alias")
        lookup = matched_alias.casefold() if language == "en" else matched_alias
        _alias, entry = aliases[lookup]
        replacement = honorific_display(entry, language)
        if language == "en" and entry["semanticClass"] == "divine-exaltation":
            divine_name = re.match(r"^(Allah|God)\b", matched_alias, re.I)
            if divine_name:
                replacement = f"{divine_name.group(1)} {replacement}"
        if language == "en" and match.group("leading"):
            # Commas and dashes punctuate the expanded parenthetical phrase,
            # not the compact glyph. Attach the glyph to its referent and
            # consume the paired closing punctuation when it is present.
            trailing = match.group("trailing") or ""
            return f" {replacement}{' ' if trailing.strip() == '—' else ''}"
        if language == "en":
            return f"{replacement}{match.group('trailing') or ''}"
        return replacement

    return pattern.sub(replace, value)


def honorific_semantic_key(entry: dict[str, Any]) -> str:
    agreement = entry["agreement"]
    return "|".join(
        (
            str(entry["semanticClass"]),
            str(agreement["number"]),
            str(agreement["gender"]),
            "family" if entry["familyIncluded"] else "no-family",
        )
    )


def honorific_occurrences(
    value: str,
    language: str,
    field: str,
    id_prefix: str,
    segment_id: str | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in HONORIFIC_ENTRIES:
        displayed = honorific_display(entry, language)
        forms = [
            displayed,
            *[str(character) for character in entry["alternateCharacters"]],
            *[
                str(alias)
                for alias in entry[
                    "englishAliases" if language == "en" else "arabicAliases"
                ]
            ],
        ]
        for form in forms:
            if form:
                lookup = form.casefold() if language == "en" else form
                grouped.setdefault(lookup, []).append(entry)
    by_form: dict[str, dict[str, Any]] = {}
    for lookup, entries in grouped.items():
        semantic_keys = {honorific_semantic_key(entry) for entry in entries}
        if len(semantic_keys) > 1:
            continue
        by_form[lookup] = next(
            (entry for entry in entries if entry["fontSupport"] == "supported"),
            entries[0],
        )
    pattern = re.compile(
        "|".join(re.escape(form) for form in sorted(by_form, key=len, reverse=True)),
        re.I if language == "en" else 0,
    )
    results: list[dict[str, Any]] = []
    for position, match in enumerate(pattern.finditer(value), start=1):
        lookup = match.group(0).casefold() if language == "en" else match.group(0)
        entry = by_form[lookup]
        context_start = max(0, match.start() - 80)
        context_end = min(len(value), match.end() + 80)
        occurrence = {
            "id": f"{id_prefix}-honorific-{position:04d}",
            "semanticId": entry["id"],
            "semanticClass": entry["semanticClass"],
            "language": language,
            "field": field,
            "observedForm": match.group(0),
            "renderedForm": honorific_display(entry, language),
            "expandedArabic": entry["expandedArabic"],
            "accessibleText": (
                entry["accessibleEnglish"]
                if language == "en"
                else entry["expandedArabic"]
            ),
            "formulaRole": "formulaic",
            "referent": {
                "kind": entry["referent"]["kind"],
                "scope": entry["referent"]["scope"],
                "context": value[context_start:context_end],
                "status": "machine-inferred",
            },
            "agreement": entry["agreement"],
            "familyIncluded": entry["familyIncluded"],
        }
        if segment_id is not None:
            occurrence["segmentId"] = segment_id
        results.append(occurrence)
    return results


def honorific_inventory(
    occurrences: list[dict[str, Any]], semantic: bool = False
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for occurrence in occurrences:
        if semantic:
            entry = next(
                entry
                for entry in HONORIFIC_ENTRIES
                if entry["id"] == occurrence["semanticId"]
            )
            counts[honorific_semantic_key(entry)] += 1
        else:
            counts[str(occurrence["semanticId"])] += 1
    return dict(sorted(counts.items()))


def normalize_search_text(value: str) -> str:
    for character, entry in HONORIFIC_BY_CHARACTER.items():
        searchable = " ".join(
            (
                str(entry["expandedArabic"]),
                str(entry["accessibleEnglish"]),
                *[str(alias) for alias in entry["arabicAliases"]],
                *[str(alias) for alias in entry["englishAliases"]],
            )
        )
        value = value.replace(character, searchable)
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


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
    return compact_registry_aliases(value, "ar")


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
        exact = "\n".join(lines)
        value = exact
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
                exact=exact,
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


def render_arabic_poetry(value: str) -> str:
    """Turn OpenITI poetry delimiters into reader-visible verse boundaries."""

    return re.sub(r"\s*%\s*", "\n", value).strip()


def structure_body_opening(body: str, opening: str, kind: str, entry_number: int) -> str:
    if not body.startswith(opening):
        raise ValueError(
            f"Entry-title decision {entry_number} would lose or reorder its {kind} body opening"
        )
    if kind != "lineage":
        return body
    remainder = body[len(opening) :]
    if not remainder or remainder.startswith("\n\n"):
        return body
    punctuation = re.match(r"^([.,;:،؛]+)", remainder)
    suffix = punctuation.group(1) if punctuation else ""
    remainder = remainder[len(suffix) :].lstrip()
    return f"{opening}{suffix}\n\n{remainder}" if remainder else f"{opening}{suffix}"


def apply_entry_title_decision(
    source: OpenITIEntry,
    legacy_title_en: str,
    english: str,
    decision: dict[str, Any],
) -> tuple[str, str, str, str]:
    number = source.number
    title_ar = str(decision["title"]["ar"])
    title_en = str(decision["title"]["en"])
    opening_ar = str(decision["bodyOpening"]["ar"])
    opening_en = str(decision["bodyOpening"]["en"])
    kind = str(decision["bodyOpeningKind"])

    if not source.rendered.startswith(f"{title_ar} "):
        raise ValueError(f"Entry-title decision {number} does not match the pinned Arabic source")
    arabic = source.rendered[len(title_ar) :].lstrip()
    arabic = structure_body_opening(arabic, opening_ar, kind, number)

    if not legacy_title_en.casefold().startswith(title_en.casefold()):
        raise ValueError(f"Entry-title decision {number} does not match the working English title")
    moved = legacy_title_en[len(title_en) :].lstrip(" \t\r\n,:;.-—")
    if moved and not english.casefold().startswith(moved.casefold()):
        english = f"{moved}\n\n{english}".strip()
    english = structure_body_opening(english, opening_en, kind, number)
    return title_ar, title_en, arabic, english


def render_english_formulas(value: str) -> str:
    value = compact_registry_aliases(value, "en")
    compact_characters = "".join(
        re.escape(character) for character in HONORIFIC_BY_CHARACTER
    )
    return re.sub(rf"\(([{compact_characters}])\)", r"\1", value)


def repair_public_arabic_projection(
    source_number: int, title: str, body: str, decisions: list[dict[str, str]]
) -> tuple[str, str]:
    """Remove only audited modern apparatus from the displayed projection."""

    combined = f"{title}\u0000{body}"
    for old, new in SOURCE_ARABIC_APPARATUS_REPLACEMENTS.get(source_number, ()):
        if combined.count(old) != 1:
            raise ValueError(
                f"Expected one audited Arabic apparatus marker for {source_number}: {old}"
            )
        combined = combined.replace(old, new, 1)
        decisions.append(
            {
                "issue": "The approved digital source embeds a modern numeric apparatus marker inside the reading text.",
                "resolution": "Removed the audited marker from the public reading projection without changing the pinned source evidence.",
                "basis": "Al-Isabah public-presentation and source-integrity contracts; exact entry-scoped replacement.",
            }
        )
    repaired_title, repaired_body = combined.split("\u0000", 1)
    return repaired_title, repaired_body


def sanitize_english(
    item: dict[str, Any], source_number: int | None = None
) -> tuple[str, dict[str, int]]:
    removed_notes = 0
    removed_editorial = 0
    honorific_type_corrections = 0
    source_honorific_corrections = ENGLISH_HONORIFIC_SOURCE_CORRECTIONS.get(
        source_number or 0, ()
    )
    source_presentation_repairs = ENGLISH_PRESENTATION_SOURCE_REPAIRS.get(
        source_number or 0, ()
    )
    kept: list[str] = []
    title = clean_english_title(str(item.get("title", {}).get("en", "")))
    for segment in item.get("segments", []):
        value = str(segment.get("english", "")).split("_________", 1)[0]
        for old, new in source_honorific_corrections:
            if value.count(old) > 1:
                raise ValueError(
                    f"Found repeated source-locked honorific correction for source entry {source_number}"
                )
            if old in value:
                value = value.replace(old, new, 1)
                honorific_type_corrections += 1
        editorial = list(EDITORIAL_NOTE_RE.finditer(value))
        removed_editorial += len(editorial)
        value = EDITORIAL_NOTE_RE.sub("", value)
        paragraphs = re.split(r"\n\s*\n", value)
        poetry_indices: set[int] = set()
        for index, paragraph in enumerate(paragraphs):
            if not METER_PARAGRAPH_RE.fullmatch(paragraph.strip()):
                continue
            cursor = index - 1
            while cursor >= 0:
                candidate = paragraphs[cursor].strip()
                if not candidate or candidate.endswith(":"):
                    break
                poetry_indices.add(cursor)
                cursor -= 1
        for index, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if STRUCTURAL_HEADING_PARAGRAPH_RE.fullmatch(paragraph):
                continue
            if FOOTNOTE_PARAGRAPH_RE.match(paragraph):
                removed_notes += 1
                continue
            paragraph = FOOTNOTE_CALLOUT_RE.sub("", paragraph)
            paragraph = re.sub(r"^\s*\d+\s*[.\-—]\s*", "", paragraph)
            meter = METER_PARAGRAPH_RE.fullmatch(paragraph)
            if meter:
                paragraph = display_meter(meter.group(1) or meter.group(2))
            elif index in poetry_indices:
                paragraph = "\n".join(
                    " ".join(line.split())
                    for line in paragraph.splitlines()
                    if line.strip()
                )
            else:
                paragraph = " ".join(paragraph.split())
            paragraph = render_english_formulas(paragraph)
            if not paragraph:
                continue
            if title and paragraph.casefold().startswith(title.casefold()):
                paragraph = paragraph[len(title) :].lstrip(" \t\r\n,:;.-—")
                if not paragraph:
                    continue
            kept.append(paragraph)
    if honorific_type_corrections != len(source_honorific_corrections):
        raise ValueError(
            f"Expected {len(source_honorific_corrections)} source-locked honorific corrections for source entry {source_number}"
        )
    value = render_english_formulas("\n\n".join(kept)).strip()
    presentation_repairs = 0
    for old, new in source_presentation_repairs:
        if value.count(old) != 1:
            raise ValueError(
                f"Expected one source-locked presentation repair for source entry {source_number}"
            )
        value = value.replace(old, new, 1)
        presentation_repairs += 1
    value = METER_LABEL_RE.sub(
        lambda match: display_meter(match.group(1) or match.group(2)),
        value,
    )
    value = re.sub(r"—\n\n(?=\S)", " ", value)
    return value, {
        "removedApparatusParagraphs": removed_notes,
        "removedEditorialNotes": removed_editorial,
        "honorificTypeCorrections": honorific_type_corrections,
        "sourcePresentationRepairs": presentation_repairs,
    }


def formula_counts(value: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for character, entry in HONORIFIC_BY_CHARACTER.items():
        count = value.count(character)
        if count:
            counts[str(entry["id"])] += count
    for entry in HONORIFIC_ENTRIES:
        if entry["fontSupport"] != "fallback-expanded":
            continue
        for displayed in (entry["expandedArabic"], entry["accessibleEnglish"]):
            count = value.count(displayed)
            if count:
                counts[str(entry["id"])] += count
    return dict(sorted(counts.items()))


SOURCE_LOCKED_ENGLISH_REPLACEMENTS: dict[int, tuple[tuple[str, str], ...]] = {
    10800: (
        ("al-Daraqutni transmitted her hadith", "al-Dar al-Daraqutni transmitted her hadith"),
        (
            "from Abu Harmala, from Abu Thifal, from Ribah ibn Abd al-Rahman",
            "from Abu Harmala, from his father, who said, from Ribah ibn Abd al-Rahman",
        ),
    ),
    10804: (("lived until the early part of 73 AH", "lived until the early part of 24 AH"),),
    11430: (("ibn Rabi'a ibn Amir", "ibn Bi'a ibn Amir"),),
    11587: (
        (
            "May Allah fight you, O people of Iraq!",
            "May Allah fight you, O people of nocturnal incursions!",
        ),
    ),
    11588: (("mother of Ali and his brothers", "father of Ali and his brothers"),),
}

SUPPLEMENTAL_SOURCE_TRANSLATIONS: dict[int, str] = {
    10886: "She pledged allegiance to the Prophet ﷺ. Ibn Habib said this, and Ibn al-Athir added her."
}


def apply_source_locked_english(
    legacy_number: int, title: str, english: str, removals: dict[str, int]
) -> tuple[str, str, list[dict[str, str]], bool]:
    """Undo unsupported emendations while retaining transparent decisions."""

    decisions: list[dict[str, str]] = []
    source_uncertainty = False
    for old, new in SOURCE_LOCKED_ENGLISH_REPLACEMENTS.get(legacy_number, ()):
        combined = f"{title}\u0000{english}"
        if old not in combined:
            raise ValueError(
                f"Expected source-locked correction text is absent for {legacy_number}: {old}"
            )
        combined = combined.replace(old, new, 1)
        title, english = combined.split("\u0000", 1)
        decisions.append(
            {
                "issue": "The legacy working translation adopted an editorial emendation not present in the approved source authority.",
                "resolution": f"The public working text follows the approved source wording: {new}",
                "basis": "Pinned OpenITI source authority and Sabiqah's source-faithful public-output contract.",
            }
        )
        source_uncertainty = True
    supplement = SUPPLEMENTAL_SOURCE_TRANSLATIONS.get(legacy_number)
    if supplement and supplement not in english:
        english = f"{english}\n\n{supplement}".strip()
        decisions.append(
            {
                "issue": "The legacy working English omitted a sentence present in the approved source authority.",
                "resolution": f"Added an independent source-faithful translation: {supplement}",
                "basis": "Pinned OpenITI source authority.",
            }
        )
    if removals["removedEditorialNotes"]:
        decisions.append(
            {
                "issue": "The private comparison text contained an editorial workflow note.",
                "resolution": "Removed the note from public reading text; any source-locked wording change is recorded separately.",
                "basis": "Public-output compliance policy excludes private apparatus from reader-facing prose.",
            }
        )
    if removals["sourcePresentationRepairs"]:
        decisions.append(
            {
                "issue": "The working translation split a single name across a paragraph boundary and duplicated its connective text.",
                "resolution": "Joined the audited phrase into one continuous sentence without changing its meaning.",
                "basis": "Al-Isabah presentation contract and the pinned source sequence.",
            }
        )
    return title, english, decisions, source_uncertainty


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
    decisions: list[dict[str, str]],
    source_uncertainty: bool,
    title_decision: dict[str, Any] | None,
) -> dict[str, Any]:
    legacy_number = int(legacy["printedEntryNumber"])
    if title_decision is not None:
        title_ar, title_en, arabic_body, english = apply_entry_title_decision(
            source, title_en, english, title_decision
        )
    else:
        title_ar = public_arabic_title(source, str(legacy["title"]["ar"]))
        arabic_body = public_arabic_body(source, title_ar)
    title_ar, arabic_body = repair_public_arabic_projection(
        source.number, title_ar, arabic_body, decisions
    )
    arabic_body = render_arabic_poetry(arabic_body)
    segment_id = f"{legacy['id']}-public-segment-0001"
    source_honorifics = honorific_occurrences(
        source.clean,
        "ar",
        "segment",
        f"{legacy['id']}-ar-source",
        segment_id,
    )
    english_honorifics = [
        *honorific_occurrences(
            title_en, "en", "title", f"{legacy['id']}-en-title"
        ),
        *honorific_occurrences(
            english,
            "en",
            "segment",
            f"{legacy['id']}-en-segment",
            segment_id,
        ),
    ]
    source_semantics = honorific_inventory(source_honorifics, semantic=True)
    english_semantics = honorific_inventory(english_honorifics, semantic=True)
    source_literals = honorific_inventory(source_honorifics)
    english_literals = honorific_inventory(english_honorifics)
    honorific_findings = []
    if source_semantics != english_semantics:
        honorific_findings.append(
            "Source and English formula inventories differ semantically or in grammatical agreement; a human must adjudicate referents before approval."
        )
    literal_inventory_differs = source_literals != english_literals
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
    if honorific_findings:
        unresolved.append(
            {
                "category": "honorific-semantic-review",
                "explanation": honorific_findings[0],
                "priority": "review",
            }
        )
    if source_uncertainty:
        unresolved.append(
            {
                "category": "source-text-uncertainty",
                "explanation": "The public English now follows the approved source authority, but the locked source wording appears textually uncertain and requires human review before approval.",
                "priority": "review",
            }
        )
    if english_exclusion_reasons:
        raise ValueError(
            f"Public working English unexpectedly failed for {legacy['id']}: "
            + ", ".join(english_exclusion_reasons)
        )
    if not title_en.strip() and not english.strip():
        raise ValueError(f"No public working English remains for {legacy['id']}")
    displayed_source = " ".join(f"{title_ar} {arabic_body}".split())
    source_sha = sha256_text(displayed_source)
    exact_source_sha = sha256_text(source.exact)
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
        "headingsBefore": list(SOURCE_HEADINGS_BEFORE.get(source.number, ())),
        "translationState": "translated",
        "machineAssessment": "needs_attention" if unresolved else "passed",
        "humanReview": "unreviewed",
        "publicEligibility": "eligible",
        "segments": [
            {
                "id": segment_id,
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
                "machineState": "public_source_remediated_unreviewed",
            }
        ],
        "names": [],
        "unresolved": unresolved,
        "honorificPolicyVersion": HONORIFIC_POLICY_VERSION,
        "honorifics": [*source_honorifics, *english_honorifics],
        "decisions": decisions,
        "workflowStages": [
            {
                "stage": "source_alignment",
                "state": "complete",
                "summary": f"The stable record was aligned to OpenITI entry {source.number}; restricted Arabic was replaced rather than republished.",
            },
            {
                "stage": "adjudication",
                "state": "complete",
                "summary": "Sabiqah-authored working English was retained after private apparatus was removed and unsupported emendations were returned to the approved source wording.",
            },
            {
                "stage": "machine_validation",
                "state": "needs_attention" if unresolved else "complete",
                "summary": (
                    "Honorific semantics or source-locked wording require human adjudication; the working English remains public."
                    if unresolved
                    else "Public-source alignment, apparatus exclusion, provenance, and honorific semantics passed automated validation."
                ),
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
            "sourceExactTextSha256": exact_source_sha,
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
            "sourceHonorificSemantics": source_semantics,
            "englishHonorificSemantics": english_semantics,
            "honorificLiteralInventoryDiffers": literal_inventory_differs,
            "honorificSemanticReview": (
                "needs_attention" if honorific_findings else "passed"
            ),
            "honorificFindings": honorific_findings,
            "englishExcluded": False,
            "englishExclusionReasonCodes": [],
            **removals,
        },
        "provenance": {
            "sourceAuthorityId": SOURCE_AUTHORITY_ID,
            "sourceArtifactSha256": SOURCE_SHA256,
            "sourceTextSha256": source_sha,
            "sourceExactTextSha256": exact_source_sha,
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
    search_text = normalize_search_text(
        "\n".join(
            (
                item["title"]["en"],
                item["title"]["ar"],
                *(
                    f"{segment['english']}\n{segment['arabic']}"
                    for segment in item["segments"]
                ),
            )
        )
    )
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
        "searchText": search_text,
    }


def quarantine_record(
    legacy: dict[str, Any], source_number: int | None, reasons: list[str]
) -> dict[str, Any]:
    reason_codes = sorted(set(reasons))
    is_contextual_passage = (
        legacy.get("kind") == "passage"
        and reason_codes == ["no-approved-entry-alignment"]
    )
    record = {
        "id": legacy["id"],
        "kind": legacy.get("kind", "entry"),
        "legacyAllocationNumber": legacy.get("printedEntryNumber"),
        "candidateSourceEntryNumber": source_number,
        "disposition": (
            "excluded-pending-public-source-alignment"
            if is_contextual_passage
            else "remediation-required"
        ),
        "reasonCodes": reason_codes,
    }
    title_en = legacy.get("title", {}).get("en")
    if isinstance(title_en, str) and title_en.strip():
        record["titleEn"] = title_en.strip()
    return record


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


def rebuild(
    legacy_root: Path,
    openiti_path: Path,
    output: Path,
    generated_at: str,
    entry_title_profile: Path = DEFAULT_ENTRY_TITLE_PROFILE,
) -> dict[str, Any]:
    reset_output(output)
    openiti = parse_openiti(openiti_path)
    title_decisions = load_entry_title_profile(entry_title_profile)
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
        english, removals = sanitize_english(
            legacy, source.number if source is not None else None
        )
        title_en = clean_english_title(str(legacy.get("title", {}).get("en", "")))
        formula_type_corrections = removals["honorificTypeCorrections"]
        title_en, english, decisions, source_uncertainty = apply_source_locked_english(
            int(legacy["printedEntryNumber"]), title_en, english, removals
        )
        if any(
            pattern.search(f"{title_en}\n{english}")
            for pattern in FORBIDDEN_PUBLIC_PATTERNS
        ):
            english_exclusion_reasons.append("unapproved-apparatus-remains")
        if reasons or source is None:
            quarantined.append(quarantine_record(legacy, mapped_number, reasons))
            continue
        if not title_en.strip() and not english.strip():
            english_exclusion_reasons.append("no-retainable-translation")
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
                decisions,
                source_uncertainty,
                title_decisions.get(source.number),
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
    disposition_counts = Counter(record["disposition"] for record in quarantined)
    exclusion_summary = {
        "contextualPassagesPendingPublicSourceAlignment": disposition_counts[
            "excluded-pending-public-source-alignment"
        ],
        "recordsPendingRemediation": disposition_counts["remediation-required"],
    }
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
        "exclusions": exclusion_summary,
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
    exclusions = {
        "schemaVersion": "1.0.0",
        "corpusId": CORPUS_ID,
        "counts": exclusion_summary,
        "records": [
            {
                key: record[key]
                for key in ("id", "kind", "titleEn", "disposition", "reasonCodes")
                if key in record
            }
            for record in sorted(quarantined, key=lambda record: record["id"])
        ],
    }
    write_json(output / "summary.json", summary)
    write_json(output / "index.json", index)
    write_json(output / "quarantine.json", quarantine)
    write_json(output / "exclusions.json", exclusions)
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
        "--entry-title-profile", type=Path, default=DEFAULT_ENTRY_TITLE_PROFILE
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
        args.entry_title_profile.resolve(),
    )
    print(
        f"Rebuilt {summary['counts']['entries']} public entries; "
        f"quarantined {summary['counts']['quarantined']} of "
        f"{summary['counts']['sourceInventory']} posted records."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
