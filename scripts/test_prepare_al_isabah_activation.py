#!/usr/bin/env python3
"""Tests for the Al-Isabah current-pointer activation preflight."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from prepare_al_isabah_activation import (
    ActivationPreflightError,
    activation_action,
    load_pointer,
)


def pointer(corpus_id: str, commit: str, *, rollback_to: str | None = None) -> dict:
    value = {
        "schemaVersion": "1.0.0",
        "corpusId": corpus_id,
        "prefix": f"public-corpora/al-isabah/{corpus_id}",
        "distributionId": f"distribution-{commit[:12]}",
        "distributionCommit": commit,
        "distributionManifestSha256": commit[0] * 64,
        "activatedAt": "2026-08-16T00:00:00Z",
    }
    if rollback_to:
        value["rollback"] = {
            "previousCorpusId": rollback_to,
            "previousPrefix": f"public-corpora/al-isabah/{rollback_to}",
        }
    return value


class AlIsabahActivationPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.old = pointer("old-corpus", "a" * 40)
        self.proposed = pointer(
            "new-content-addressed-corpus", "b" * 40, rollback_to="old-corpus"
        )

    def test_exact_unchanged_pointer_allows_activation(self) -> None:
        self.assertEqual(
            activation_action(self.old, copy.deepcopy(self.old), self.proposed),
            "activate",
        )

    def test_already_active_candidate_preserves_first_pointer_and_rollback(self) -> None:
        active = copy.deepcopy(self.proposed)
        active["activatedAt"] = "2026-08-16T01:00:00Z"
        later = copy.deepcopy(self.proposed)
        later["activatedAt"] = "2026-08-16T02:00:00Z"
        later["rollback"] = {
            "previousCorpusId": later["corpusId"],
            "previousPrefix": later["prefix"],
        }
        self.assertEqual(activation_action(active, active, later), "preserve")

    def test_changed_pointer_fails_closed(self) -> None:
        changed = pointer("other-corpus", "c" * 40)
        with self.assertRaisesRegex(ActivationPreflightError, "changed"):
            activation_action(self.old, changed, self.proposed)

    def test_claim_change_for_same_candidate_fails_closed(self) -> None:
        changed = copy.deepcopy(self.proposed)
        changed["legacyBinding"] = {"id": "unexpected"}
        with self.assertRaisesRegex(ActivationPreflightError, "changed"):
            activation_action(self.old, changed, self.proposed)

    def test_same_candidate_with_self_referential_rollback_fails_closed(self) -> None:
        unsafe = copy.deepcopy(self.proposed)
        unsafe["rollback"] = {
            "previousCorpusId": unsafe["corpusId"],
            "previousPrefix": unsafe["prefix"],
        }
        with self.assertRaisesRegex(ActivationPreflightError, "unsafe rollback"):
            activation_action(self.old, unsafe, self.proposed)

    def test_unknown_pointer_schema_fails_closed(self) -> None:
        unknown = copy.deepcopy(self.old)
        unknown["schemaVersion"] = "2.0.0"
        with self.assertRaisesRegex(ActivationPreflightError, "unsupported"):
            activation_action(unknown, unknown, self.proposed)

    def test_invalid_identity_fails_closed(self) -> None:
        invalid = copy.deepcopy(self.old)
        invalid["prefix"] = "public-corpora/al-isabah/wrong"
        with self.assertRaisesRegex(ActivationPreflightError, "invalid corpus"):
            activation_action(invalid, invalid, self.proposed)

    def test_missing_pointer_fails_closed_without_content_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "missing.json"
            with self.assertRaisesRegex(
                ActivationPreflightError, "missing or invalid"
            ):
                load_pointer(missing, "observed current pointer")


if __name__ == "__main__":
    unittest.main()
