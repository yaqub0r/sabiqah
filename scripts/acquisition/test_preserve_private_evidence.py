from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping


MODULE_PATH = Path(__file__).with_name("preserve_private_evidence.py")
SPEC = importlib.util.spec_from_file_location("preserve_private_evidence", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeR2:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.metadata: dict[str, Mapping[str, Any]] = {}

    def head(self, key: str) -> Mapping[str, Any] | None:
        if key not in self.objects:
            return None
        return {
            "ContentLength": len(self.objects[key]),
            "Metadata": self.metadata[key],
        }

    def put(self, key: str, archive: Path, archive_sha256: str) -> None:
        self.objects[key] = archive.read_bytes()
        self.metadata[key] = {"sha256": archive_sha256}

    def get(self, key: str, destination: Path) -> None:
        destination.write_bytes(self.objects[key])


def make_bundle(root: Path, *, classification: str = "private-reference") -> Path:
    source = root / "evidence"
    source.mkdir()
    evidence = b"restricted research evidence\n"
    (source / "page-01.txt").write_bytes(evidence)
    manifest = {
        "schemaVersion": 1,
        "evidenceId": "example-evidence-v1",
        "classification": classification,
        "publicationEligibility": "blocked",
        "acquiredAt": "2026-08-13",
        "purpose": "Contract test fixture",
        "provenance": {"status": "recorded"},
        "rights": {"status": "unresolved"},
        "files": [
            {
                "name": "page-01.txt",
                "bytes": len(evidence),
                "sha256": hashlib.sha256(evidence).hexdigest(),
            }
        ],
    }
    (source / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return source


class PrivateEvidenceTests(unittest.TestCase):
    def test_archive_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = make_bundle(root)
            bundle = MODULE.validate_bundle(source)
            first_hash, first_bytes = MODULE.build_deterministic_archive(bundle, root / "one.zip")
            second_hash, second_bytes = MODULE.build_deterministic_archive(bundle, root / "two.zip")
            self.assertEqual(first_hash, second_hash)
            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual((root / "one.zip").read_bytes(), (root / "two.zip").read_bytes())

    def test_rejects_public_classification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = make_bundle(Path(directory), classification="public-domain")
            with self.assertRaisesRegex(MODULE.EvidenceError, "classification"):
                MODULE.validate_bundle(source)

    def test_rejects_changed_and_unlisted_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = make_bundle(root)
            (source / "page-01.txt").write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.EvidenceError, "byte-count mismatch"):
                MODULE.validate_bundle(source)

            source = root / "second"
            source.mkdir()
            fixture = make_bundle(source)
            (fixture / "unlisted.txt").write_text("not declared", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.EvidenceError, "inventory mismatch"):
                MODULE.validate_bundle(fixture)

    def test_uploads_then_verifies_existing_identical_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = make_bundle(root)
            client = FakeR2()
            runtime = root / "runtime"
            first = MODULE.preserve(
                source,
                "al-isabah",
                dry_run=False,
                client=client,
                runtime_directory=runtime,
            )
            second = MODULE.preserve(
                source,
                "al-isabah",
                dry_run=False,
                client=client,
                runtime_directory=runtime,
            )
            self.assertEqual(first["status"], "uploaded")
            self.assertEqual(second["status"], "verified-existing")

    def test_refuses_existing_object_with_different_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = make_bundle(root)
            client = FakeR2()
            key = "research-evidence/al-isabah/example-evidence-v1/example-evidence-v1.zip"
            client.objects[key] = b"different"
            client.metadata[key] = {"sha256": hashlib.sha256(b"different").hexdigest()}
            with self.assertRaisesRegex(MODULE.EvidenceError, "refusing to overwrite"):
                MODULE.preserve(
                    source,
                    "al-isabah",
                    dry_run=False,
                    client=client,
                    runtime_directory=root / "runtime",
                )


if __name__ == "__main__":
    unittest.main()
