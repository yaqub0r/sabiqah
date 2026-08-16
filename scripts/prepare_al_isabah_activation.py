#!/usr/bin/env python3
"""Fail-closed preflight for an Al-Isabah current-pointer replacement."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SHA256 = re.compile(r"^[a-f0-9]{64}$")
POINTER_SCHEMA = "1.0.0"
MUTABLE_ACTIVATION_KEYS = {"activatedAt", "rollback"}


class ActivationPreflightError(RuntimeError):
    """Raised when a mutable pointer cannot be replaced safely."""


def load_pointer(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ActivationPreflightError(f"{label} is missing or invalid") from error
    if not isinstance(value, dict):
        raise ActivationPreflightError(f"{label} must be an object")
    return value


def validate_identity(pointer: dict[str, Any], label: str) -> None:
    if pointer.get("schemaVersion") != POINTER_SCHEMA:
        raise ActivationPreflightError(f"{label} has an unsupported pointer schema")
    corpus_id = pointer.get("corpusId")
    if (
        not isinstance(corpus_id, str)
        or not corpus_id
        or pointer.get("prefix") != f"public-corpora/al-isabah/{corpus_id}"
    ):
        raise ActivationPreflightError(f"{label} has an invalid corpus identity")
    if (
        not isinstance(pointer.get("distributionId"), str)
        or not pointer["distributionId"]
    ):
        raise ActivationPreflightError(f"{label} has an invalid distribution identity")
    if not re.fullmatch(
        r"[a-f0-9]{40}", str(pointer.get("distributionCommit", ""))
    ):
        raise ActivationPreflightError(f"{label} has an invalid distribution commit")
    if not SHA256.fullmatch(
        str(pointer.get("distributionManifestSha256", ""))
    ):
        raise ActivationPreflightError(
            f"{label} has an invalid distribution manifest digest"
        )


def identity(pointer: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in pointer.items()
        if key not in MUTABLE_ACTIVATION_KEYS
    }


def validate_rollback(pointer: dict[str, Any]) -> None:
    rollback = pointer.get("rollback")
    if not isinstance(rollback, dict):
        raise ActivationPreflightError("active intended corpus lacks rollback metadata")
    previous_id = rollback.get("previousCorpusId")
    previous_prefix = rollback.get("previousPrefix")
    if (
        not isinstance(previous_id, str)
        or not previous_id
        or previous_id == pointer["corpusId"]
        or previous_prefix != f"public-corpora/al-isabah/{previous_id}"
        or previous_prefix == pointer["prefix"]
    ):
        raise ActivationPreflightError("active intended corpus has unsafe rollback metadata")


def activation_action(
    expected_current: dict[str, Any],
    observed_current: dict[str, Any],
    proposed_activation: dict[str, Any],
) -> str:
    validate_identity(expected_current, "expected current pointer")
    validate_identity(observed_current, "observed current pointer")
    validate_identity(proposed_activation, "proposed activation pointer")

    if identity(observed_current) == identity(proposed_activation):
        validate_rollback(observed_current)
        return "preserve"
    validate_rollback(proposed_activation)
    if observed_current != expected_current:
        raise ActivationPreflightError(
            "current pointer changed after candidate construction"
        )
    if identity(expected_current) == identity(proposed_activation):
        raise ActivationPreflightError(
            "proposed activation would replace an already-active corpus"
        )
    return "activate"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-current", required=True, type=Path)
    parser.add_argument("--observed-current", required=True, type=Path)
    parser.add_argument("--proposed-activation", required=True, type=Path)
    args = parser.parse_args()
    try:
        action = activation_action(
            load_pointer(args.expected_current, "expected current pointer"),
            load_pointer(args.observed_current, "observed current pointer"),
            load_pointer(args.proposed_activation, "proposed activation pointer"),
        )
    except ActivationPreflightError as error:
        parser.error(str(error))
    print(action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
