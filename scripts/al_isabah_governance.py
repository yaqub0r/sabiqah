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


def _consumer_entries() -> tuple[dict[str, Any], ...]:
    presentation_entries = PRESENTATION["entries"]
    by_character = {
        entry["compactCharacter"]: entry
        for entry in presentation_entries
        if entry.get("compactCharacter")
    }
    adapters: dict[str, dict[str, Any]] = {}

    for formula in FORMULA_PROJECTION["entries"]:
        target = str(formula["target"])
        presentation = by_character.get(target)
        if presentation is None:
            continue

        adapter_id = str(presentation["id"])
        family_included = "family" in str(formula["semanticClass"]).casefold()
        if presentation.get("familyIncluded") != family_included:
            raise ValueError(
                f"Upstream family semantics differ for presentation adapter {adapter_id}"
            )
        agreement = copy.deepcopy(presentation["agreement"])
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
