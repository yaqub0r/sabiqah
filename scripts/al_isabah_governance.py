"""Load the pinned Al-Isabah governance projection for consumer adapters.

Al-Isabah owns formula semantics. This module joins its verified projection to
Sabiqah-owned rendering metadata without treating the presentation file as a
translation policy.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
COMPATIBILITY_PATH = (
    ROOT
    / "packages"
    / "release-model"
    / "src"
    / "al-isabah-governance.compatibility.json"
)
FORMULA_PROJECTION_PATH = (
    ROOT
    / "packages"
    / "release-model"
    / "src"
    / "al-isabah-honorifics.projection.json"
)
PRESENTATION_PATH = (
    ROOT
    / "packages"
    / "release-model"
    / "src"
    / "honorifics.presentation.json"
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top level must be an object")
    return value


COMPATIBILITY = _load(COMPATIBILITY_PATH)
FORMULA_PROJECTION = _load(FORMULA_PROJECTION_PATH)
PRESENTATION = _load(PRESENTATION_PATH)


def _validate_bindings() -> None:
    upstream = COMPATIBILITY["upstream"]
    formula = COMPATIBILITY["formulaProjection"]
    source = FORMULA_PROJECTION["source"]
    expected = {
        "repository": upstream["repository"],
        "commit": upstream["commit"],
        "referencePath": upstream["referencePath"],
        "referenceVersion": upstream["referenceVersion"],
        "referenceSha256": upstream["referenceSha256"],
        "artifactPath": formula["path"],
        "artifactVersion": formula["artifactVersion"],
        "artifactSha256": formula["artifactSha256"],
        "textNormalization": upstream["textNormalization"],
    }
    if source != expected:
        raise ValueError("Al-Isabah honorific projection does not match the consumer pin")
    if FORMULA_PROJECTION.get("role") != "verified-consumer-projection":
        raise ValueError("Al-Isabah honorific projection has the wrong consumer role")
    if PRESENTATION.get("role") != "consumer-presentation-only":
        raise ValueError("Sabiqah honorific metadata is not presentation-only")
    if int(str(upstream["referenceVersion"]).split(".", 1)[0]) != int(
        upstream["supportedReferenceMajor"]
    ):
        raise ValueError("Unsupported Al-Isabah governance reference major version")


def _agreement(value: str) -> dict[str, str]:
    agreements = {
        "masculine singular and masculine plural": {
            "number": "plural",
            "gender": "masculine-or-mixed",
        },
        "masculine singular with family inclusion": {
            "number": "plural",
            "gender": "mixed",
        },
        "masculine singular": {"number": "singular", "gender": "masculine"},
        "feminine singular": {"number": "singular", "gender": "feminine"},
        "dual": {"number": "dual", "gender": "common"},
        "masculine plural": {
            "number": "plural",
            "gender": "masculine-or-mixed",
        },
        "feminine plural": {"number": "plural", "gender": "feminine"},
        "plural": {"number": "plural", "gender": "masculine-or-mixed"},
        "not_applicable": {
            "number": "not-applicable",
            "gender": "not-applicable",
        },
    }
    try:
        return agreements[value]
    except KeyError as error:
        raise ValueError(f"Unknown upstream honorific agreement: {value}") from error


def _referent_kind(scope: str) -> str:
    lowered = scope.casefold()
    if "god" in lowered:
        return "Allah"
    if "prophet" in lowered and "companions" not in lowered:
        return "prophet"
    if any(token in lowered for token in ("group", "two ", "companions")):
        return "people"
    return "person"


def _consumer_entries() -> tuple[dict[str, Any], ...]:
    presentation_entries = PRESENTATION["entries"]
    by_character = {
        entry["compactCharacter"]: entry
        for entry in presentation_entries
        if entry.get("compactCharacter")
    }
    by_expanded = {
        form: entry
        for entry in presentation_entries
        for form in (entry["expandedArabic"], *entry.get("arabicAliases", []))
    }
    adapters: dict[str, dict[str, Any]] = {}

    for index, formula in enumerate(FORMULA_PROJECTION["entries"]):
        target = str(formula["target"])
        presentation = by_character.get(target) or by_expanded.get(
            str(formula["expandedArabic"])
        )
        if presentation is None:
            presentation = {
                "id": f"al-isabah-upstream-formula-{index + 1:02d}",
                "expandedArabic": formula["expandedArabic"],
                "accessibleEnglish": formula["accessibleEnglish"],
                "compactCharacter": "",
                "codePoint": "",
                "unicodeVersion": "",
                "fontSupport": "fallback-expanded",
                "referent": {"kind": _referent_kind(formula["referentScope"])},
                "alternateCharacters": [],
                "arabicAliases": [],
                "englishAliases": [],
            }

        adapter_id = str(presentation["id"])
        agreement = _agreement(str(formula["grammaticalAgreement"]))
        family_included = "family" in str(formula["semanticClass"]).casefold()
        existing = adapters.get(adapter_id)
        if existing is not None:
            if (
                existing["semanticClass"] != formula["semanticClass"]
                or existing["agreement"] != agreement
                or existing["familyIncluded"] != family_included
            ):
                raise ValueError(
                    f"Conflicting upstream semantics for presentation adapter {adapter_id}"
                )
            for field, value in (
                ("arabicAliases", formula["source"]),
                ("englishAliases", str(formula["accessibleEnglish"]).rstrip(".")),
            ):
                if value not in existing[field]:
                    existing[field].append(value)
            continue

        adapter = copy.deepcopy(presentation)
        if not (len(target) == 1 and target in by_character):
            adapter["fontSupport"] = "fallback-expanded"
        adapter["semanticClass"] = formula["semanticClass"]
        adapter["agreement"] = agreement
        adapter["familyIncluded"] = family_included
        adapter["referent"] = {
            "kind": presentation.get("referent", {}).get("kind")
            or _referent_kind(str(formula["referentScope"])),
            "scope": formula["referentScope"],
        }
        adapter.setdefault("arabicAliases", [])
        adapter.setdefault("englishAliases", [])
        for field, value in (
            ("arabicAliases", formula["source"]),
            ("englishAliases", str(formula["accessibleEnglish"]).rstrip(".")),
        ):
            if value not in adapter[field]:
                adapter[field].append(value)
        adapters[adapter_id] = adapter

    return tuple(adapters.values())


_validate_bindings()
# Existing corpus objects expose the Sabiqah presentation-adapter version in
# this legacy field. Upstream formula compatibility is bound separately by the
# immutable projection source and must not rewrite carried corpus members.
HONORIFIC_POLICY_VERSION = str(PRESENTATION["schemaVersion"])
HONORIFIC_ENTRIES = _consumer_entries()
