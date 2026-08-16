import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ingest_al_isabah_distribution import (  # noqa: E402
    IngestionError,
    LegacyBindingInputs,
    ingest,
)
from test_ingest_al_isabah_distribution import (  # noqa: E402
    ASSET,
    COMMIT,
    TAG,
    DistributionCase,
    base_corpus,
    write,
)
from validate_public_corpus import validate as validate_public_corpus  # noqa: E402
from verify_al_isabah_legacy_binding import (  # noqa: E402
    LegacyBindingError,
    compact_json,
    digest_bytes,
    digest_file,
    git_blob_sha1,
    membership,
    scope_digest,
    verify_legacy_binding,
)


LICENSE = {
    "spdx": "CC-BY-NC-SA-4.0",
    "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
}


def file_evidence(path: Path, repository: str, commit: str, relative: str) -> dict:
    raw = path.read_bytes()
    return {
        "repository": repository,
        "commit": commit,
        "path": relative,
        "gitBlobSha1": git_blob_sha1(raw),
        "sha256": digest_bytes(raw),
    }


class LegacyBindingCase:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.distribution = DistributionCase(root)
        release = json.loads(self.distribution.release.read_text(encoding="utf-8"))
        release["id"] = 101
        release["url"] = "https://api.github.com/repos/yaqub0r/al-isabah/releases/101"
        release["assets"][0]["id"] = 202
        write(self.distribution.release, release)
        tag_ref = json.loads(self.distribution.tag_ref.read_text(encoding="utf-8"))
        tag_ref["url"] = f"https://api.github.com/repos/yaqub0r/al-isabah/git/refs/tags/{TAG}"
        write(self.distribution.tag_ref, tag_ref)
        self.base = base_corpus(root)
        self.corpus_id = "synthetic-bound-schema-4"
        original_path = self.base / "items" / "synthetic-legacy-entry-0002.json"
        original = json.loads(original_path.read_text(encoding="utf-8"))
        original["corpusId"] = self.corpus_id
        original["source"]["alignment"]["method"] = "al-isabah-public-distribution-v1"
        original["source"]["license"] = LICENSE
        original["provenance"]["sourceArtifactSha256"] = (
            "bc9db8134c8278973967c91c00324531833f643fc0fb2c8ebe318c9ed4469eea"
        )
        for key in (
            "sourceRepository", "sourceCommit", "sourceArtifactSha256", "attribution",
            "englishRights", "rightsMatrix",
        ):
            original["source"].pop(key, None)
        for key in ("sourceRepository", "sourceCommit"):
            original["provenance"].pop(key, None)
        stable = copy.deepcopy(original)
        stable["id"] = "synthetic-stable-entry-0003"
        stable["sequence"] = 300
        stable["printedEntryNumber"] = 3
        stable["sourceEntryNumber"] = 3
        stable["segments"][0]["id"] = "synthetic-stable-entry-0003-body"
        stable["source"]["alignment"]["method"] = (
            "stable-sequence-map-and-normalized-body-comparison-v1"
        )
        stable["remediation"] = {
            "sourceArabicReplaced": True,
            "privateLocatorsRemoved": True,
            "englishExcluded": False,
            "englishExclusionReasonCodes": [],
            "sourceHonorificSemantics": {},
            "englishHonorificSemantics": {},
            "honorificLiteralInventoryDiffers": False,
            "honorificSemanticReview": "passed",
        }
        original_path.unlink()
        write(self.base / "items" / f"{original['id']}.json", original)
        write(self.base / "items" / f"{stable['id']}.json", stable)
        summary = json.loads((self.base / "summary.json").read_text(encoding="utf-8"))
        summary["corpus"] = {
            "id": self.corpus_id,
            "sourceRepository": "https://github.com/OpenITI/0875AH",
            "sourceCommit": "5835c183b8bbf4ea454d5c1be2b168b669403771",
            "sourceAuthorityId": "al-isabah-openiti-5835c18-aco-v1",
            "sourceArtifactSha256": "bc9db8134c8278973967c91c00324531833f643fc0fb2c8ebe318c9ed4469eea",
            "license": LICENSE,
            "generatedAt": "2026-08-15T12:00:00Z",
            "promotionStatus": "blocked",
            "publicationStatus": "public-working",
        }
        summary["counts"] = {
            "sourceInventory": 2,
            "entries": 2,
            "passages": 0,
            "translated": 2,
            "needsAttention": 0,
            "unresolvedItems": 0,
            "humanReviewed": 0,
            "quarantined": 0,
        }
        summary["volumes"][1].update(sourceItemCount=2, itemCount=2)
        write(self.base / "summary.json", summary)
        index = json.loads((self.base / "index.json").read_text(encoding="utf-8"))
        index["corpusId"] = self.corpus_id
        listed = index["items"][0]
        listed["id"] = original["id"]
        stable_listed = {**listed, "id": stable["id"], "sequence": 300, "printedEntryNumber": 3, "sourceEntryNumber": 3}
        index["items"] = [listed, stable_listed]
        write(self.base / "index.json", index)
        write(self.base / "quarantine.json", {
            "corpusId": self.corpus_id,
            "sourceInventoryCount": 2,
            "publicItemCount": 2,
            "quarantinedCount": 0,
            "records": [],
        })
        write(self.base / "exclusions.json", {
            "corpusId": self.corpus_id,
            "counts": {
                "contextualPassagesPendingPublicSourceAlignment": 0,
                "recordsPendingRemediation": 0,
            },
            "records": [],
        })
        write(self.base / "sections" / "volume-02-pages-0001-0025.json", {
            "schemaVersion": "4.0.0",
            "corpusId": self.corpus_id,
            "id": "volume-02-pages-0001-0025",
            "items": [original, stable],
        })
        self._write_manifest()
        self.pointer = root / "current.json"
        write(self.pointer, {
            "schemaVersion": "1.0.0",
            "corpusId": self.corpus_id,
            "prefix": f"public-corpora/al-isabah/{self.corpus_id}",
            "distributionId": "al-isabah-public-working-aaaaaaaaaaaa",
            "distributionCommit": COMMIT,
            "distributionManifestSha256": "b" * 64,
            "activatedAt": "2026-08-15T12:30:00Z",
        })
        self.approval = root / "approval.json"
        self.comment = root / "approval-comment.json"
        self.approval_body = "Synthetic approval for one exact legacy migration."
        self.comment_body = "Synthetic immutable approval-comment anchor."
        write(self.approval, {
            "number": 999,
            "node_id": "synthetic-approval-node",
            "created_at": "2026-08-16T00:00:00Z",
            "body": self.approval_body,
            "url": "https://api.github.com/repos/yaqub0r/sabiqah/issues/999",
            "repository_url": "https://api.github.com/repos/yaqub0r/sabiqah",
            "user": {"login": "yaqub0r", "id": 42},
        })
        self.run = root / "run.json"
        write(self.run, {
            "id": 303,
            "workflow_id": 404,
            "head_sha": "c" * 40,
            "status": "completed",
            "conclusion": "success",
        })
        self.binding = root / "binding.json"
        self._write_binding()

    def _write_manifest(self) -> None:
        files = []
        for path in sorted(self.base.rglob("*.json")):
            if path.name == "manifest.json":
                continue
            files.append({
                "path": path.relative_to(self.base).as_posix(),
                "sha256": digest_file(path),
                "bytes": path.stat().st_size,
            })
        write(self.base / "manifest.json", {
            "schemaVersion": "4.0.0",
            "corpusId": self.corpus_id,
            "distribution": {
                "id": "al-isabah-public-working-aaaaaaaaaaaa",
                "repository": "https://github.com/yaqub0r/al-isabah",
                "commit": COMMIT,
                "manifestSha256": "b" * 64,
            },
            "objectCount": len(files),
            "files": files,
        })

    def _release_binding(self) -> dict:
        release = json.loads(self.distribution.release.read_text(encoding="utf-8"))
        asset = release["assets"][0]
        return {
            "repository": "https://github.com/yaqub0r/al-isabah",
            "releaseId": release["id"],
            "tag": TAG,
            "commit": COMMIT,
            "assetId": asset["id"],
            "assetName": ASSET,
            "assetBytes": asset["size"],
            "assetSha256": asset["digest"].removeprefix("sha256:"),
        }

    def _write_binding(self) -> None:
        summary = json.loads((self.base / "summary.json").read_text(encoding="utf-8"))
        manifest = json.loads((self.base / "manifest.json").read_text(encoding="utf-8"))
        index = json.loads((self.base / "index.json").read_text(encoding="utf-8"))
        by_id = {item["id"]: item for item in index["items"]}
        item_objects = {
            Path(record["path"]).stem: record for record in manifest["files"]
            if record["path"].startswith("items/")
        }
        rights = json.loads(self.distribution.rights.read_text(encoding="utf-8"))
        matrix = {
            "id": rights["matrix_id"],
            "schema": rights["schema"],
            "decision": rights["publication_decision"]["public_reuse"],
            "reviewedOn": rights["reviewed_on"],
            "followUp": rights["follow_up_review"]["status"],
        }
        arabic = {"license": LICENSE, "attribution": rights["attribution"][1]}
        shared_exclusions = ["synthetic restricted material", "canonical promotion"]
        cohorts = []
        definitions = [
            (
                "legacy:synthetic-stable", "stable-sequence-map-and-normalized-body-comparison-v1",
                "synthetic-sabiqah", "Sabiqah contributors", "sabiqah-authored",
            ),
            (
                "legacy:synthetic-distribution", "al-isabah-public-distribution-v1",
                "synthetic-al-isabah", rights["attribution"][0], "al-isabah-project-authored",
            ),
        ]
        for cohort_id, method, producer, english_attribution, evidence_kind in definitions:
            ids = sorted(
                item_id for item_id in by_id
                if json.loads((self.base / "items" / f"{item_id}.json").read_text(encoding="utf-8"))["source"]["alignment"]["method"] == method
            )
            objects = [
                {"id": item_id, "bytes": item_objects[item_id]["bytes"], "sha256": item_objects[item_id]["sha256"]}
                for item_id in ids
            ]
            cohorts.append({
                "id": cohort_id,
                "selector": {"field": "source.alignment.method", "equals": method},
                "membership": {
                    "itemCount": len(ids),
                    "itemIdsSha256": membership(ids)["itemIdsSha256"],
                    "itemObjectsSha256": digest_bytes(compact_json(objects)),
                },
                "source": {"producerAuthorityId": producer},
                "rights": {
                    "arabicSource": arabic,
                    "englishTranslation": {"license": LICENSE, "attribution": english_attribution},
                    "matrix": matrix,
                    "excludedMaterial": shared_exclusions,
                },
                "state": {
                    "publicationStatus": "public-working",
                    "promotionStatus": "blocked",
                    "completeness": "carried-forward",
                },
                "evidenceKind": evidence_kind,
            })
        section_objects = [
            {"id": Path(record["path"]).stem, "bytes": record["bytes"], "sha256": record["sha256"]}
            for record in manifest["files"] if record["path"].startswith("sections/")
        ]
        item_ids = sorted(by_id)
        all_items = [
            {"id": item_id, "bytes": item_objects[item_id]["bytes"], "sha256": item_objects[item_id]["sha256"]}
            for item_id in item_ids
        ]
        repository = "https://github.com/yaqub0r/sabiqah"
        source_authority = ROOT / "evidence" / "source-authorities" / "al-isabah.v1.json"
        binding = {
            "schema": "sabiqah.al-isabah-legacy-provenance-binding.v1",
            "bindingId": "synthetic-one-time-binding",
            "status": "approved-one-time",
            "base": {
                "pointer": json.loads(self.pointer.read_text(encoding="utf-8")),
                "pointerSha256": digest_file(self.pointer),
                "corpusSchemaVersion": "4.0.0",
                "coreObjects": {
                    name: digest_file(self.base / name)
                    for name in ("summary.json", "index.json", "quarantine.json", "exclusions.json")
                },
                "manifestSha256": digest_file(self.base / "manifest.json"),
                "objectCount": manifest["objectCount"],
                "objectInventorySha256": digest_bytes(compact_json(manifest["files"])),
                "membership": {
                    "itemCount": len(item_ids),
                    "itemIdsSha256": membership(item_ids)["itemIdsSha256"],
                    "itemObjectsSha256": digest_bytes(compact_json(all_items)),
                },
                "sectionCount": len(section_objects),
                "sectionObjectsSha256": digest_bytes(compact_json(section_objects)),
                "counts": summary["counts"],
                "state": {"publicationStatus": "public-working", "promotionStatus": "blocked"},
            },
            "source": {
                "authorityId": "al-isabah-openiti-5835c18-aco-v1",
                "repository": "https://github.com/OpenITI/0875AH",
                "commit": "5835c183b8bbf4ea454d5c1be2b168b669403771",
                "artifactSha256": "bc9db8134c8278973967c91c00324531833f643fc0fb2c8ebe318c9ed4469eea",
                "arabicRights": arabic,
            },
            "cohorts": cohorts,
            "evidence": {
                "sourceAuthority": file_evidence(source_authority, repository, "d" * 40, "evidence/source-authorities/al-isabah.v1.json"),
                "contentLicense": file_evidence(ROOT / "CONTENT-LICENSE.md", repository, "d" * 40, "CONTENT-LICENSE.md"),
                "notice": file_evidence(ROOT / "NOTICE.md", repository, "d" * 40, "NOTICE.md"),
                "attribution": file_evidence(ROOT / "docs" / "attribution" / "al-isabah.md", repository, "d" * 40, "docs/attribution/al-isabah.md"),
                "rightsMatrix": file_evidence(self.distribution.rights, "https://github.com/yaqub0r/al-isabah", COMMIT, self.distribution.rights.as_posix()),
                "legacyRelease": self._release_binding(),
                "activationRun": json.loads(self.run.read_text(encoding="utf-8")),
            },
            "approval": {
                "repository": repository,
                "issueNumber": 999,
                "nodeId": "synthetic-approval-node",
                "actor": {"login": "yaqub0r", "id": 42, "authority": "repository-owner"},
                "recordedAt": "2026-08-16T00:00:00Z",
                "decision": "approved-one-time-compatibility-migration",
                "bodySha256": digest_bytes(self.approval_body.encode("utf-8")),
                "scopeSha256": "",
                "comment": {
                    "id": 1000,
                    "nodeId": "synthetic-comment-node",
                    "createdAt": "2026-08-16T00:05:00Z",
                    "bodySha256": digest_bytes(self.comment_body.encode("utf-8")),
                },
            },
            "allowedMigration": {
                "schemaVersion": "5.0.0",
                "release": self._release_binding(),
                "oneTime": True,
                "reusePolicy": "exact-active-schema-4-pointer-only",
            },
            "nonClaims": [f"Synthetic non-claim {index}" for index in range(6)],
            "retirement": {"condition": "synthetic supersession", "preserve": "synthetic audit record"},
        }
        binding["approval"]["scopeSha256"] = scope_digest(binding)
        write(self.comment, {
            "id": 1000,
            "node_id": "synthetic-comment-node",
            "created_at": "2026-08-16T00:05:00Z",
            "body": self.comment_body,
            "issue_url": "https://api.github.com/repos/yaqub0r/sabiqah/issues/999",
            "user": {"login": "yaqub0r", "id": 42},
        })
        write(self.binding, binding)

    def verify_args(self) -> tuple:
        return (
            self.binding,
            self.base,
            self.pointer,
            self.distribution.release,
            self.distribution.tag_ref,
            self.distribution.rights,
            self.distribution.authority,
            ROOT / "CONTENT-LICENSE.md",
            ROOT / "NOTICE.md",
            ROOT / "docs" / "attribution" / "al-isabah.md",
            self.approval,
            self.comment,
            self.run,
            self.distribution.distribution / "manifest.json",
            self.distribution.release,
            self.distribution.tag_ref,
        )

    def ingest_args(self, output: Path) -> tuple:
        legacy = LegacyBindingInputs(
            self.binding,
            self.pointer,
            self.distribution.release,
            self.distribution.tag_ref,
            self.approval,
            self.comment,
            self.run,
        )
        return (
            self.distribution.distribution,
            self.base,
            output,
            "2026-08-16T01:00:00Z",
            self.distribution.archive,
            self.distribution.release,
            self.distribution.tag_ref,
            self.distribution.rights,
            self.distribution.authority,
            legacy,
        )


class LegacyBindingTests(unittest.TestCase):
    def test_exact_binding_is_idempotent_and_discloses_rights_per_record(self):
        with tempfile.TemporaryDirectory() as temp:
            case = LegacyBindingCase(Path(temp))
            cohorts, record = verify_legacy_binding(*case.verify_args())
            self.assertEqual(len(cohorts), 2)
            self.assertEqual(sum(cohort["membership"]["itemCount"] for cohort in cohorts), 2)
            first = ingest(*case.ingest_args(case.root / "first"))
            second = ingest(*case.ingest_args(case.root / "second"))
            self.assertEqual(first["corpusId"], second["corpusId"])
            self.assertEqual(first["rollback"]["previousCorpusId"], case.corpus_id)
            self.assertEqual(first["legacyBinding"], record)
            self.assertEqual(validate_public_corpus(case.root / "first"), [])
            details = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in (case.root / "first" / "items").glob("synthetic-*-entry-*.json")
            ]
            legacy = [item for item in details if item["id"] != "synthetic-entry-0001"]
            self.assertEqual({item["source"]["englishRights"]["attribution"] for item in legacy}, {
                "Sabiqah contributors",
                "Al-Isabah project synthetic English scholarly content",
            })
            self.assertTrue(all(item["source"]["rightsMatrix"]["id"] == "al-isabah-rights-synthetic" for item in legacy))

    def test_pointer_member_object_claim_and_evidence_tampering_fail_before_output(self):
        mutations = [
            lambda case: write(case.pointer, {**json.loads(case.pointer.read_text()), "corpusId": "wrong-corpus"}),
            lambda case: (case.base / "items" / "synthetic-legacy-entry-0002.json").write_text("{}\n", encoding="utf-8"),
            lambda case: (case.base / "items" / "extra-member.json").write_text("{}\n", encoding="utf-8"),
            lambda case: (case.base / "items" / "synthetic-stable-entry-0003.json").unlink(),
            lambda case: self._mutate_binding(case, lambda value: value["base"]["membership"].update(itemCount=99)),
            lambda case: self._mutate_binding(case, lambda value: value["source"]["arabicRights"].update(attribution="False claim")),
            lambda case: self._mutate_binding(case, lambda value: value["evidence"]["sourceAuthority"].update(commit="e" * 40)),
            lambda case: self._mutate_binding(case, lambda value: value["cohorts"][1]["selector"].update(equals=value["cohorts"][0]["selector"]["equals"])),
            lambda case: write(case.distribution.rights, {"schema": "tampered"}),
        ]
        for position, mutate in enumerate(mutations):
            with self.subTest(position=position), tempfile.TemporaryDirectory() as temp:
                case = LegacyBindingCase(Path(temp))
                mutate(case)
                output = case.root / "output"
                with self.assertRaises((LegacyBindingError, IngestionError, KeyError, OSError)):
                    ingest(*case.ingest_args(output))
                self.assertFalse(output.exists())
                self.assertFalse((case.root / "activation.json").exists())

    def test_wrong_target_unknown_schema_and_reuse_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            case = LegacyBindingCase(Path(temp))
            self._mutate_binding(
                case,
                lambda value: value["allowedMigration"]["release"].update(commit="f" * 40),
            )
            with self.assertRaisesRegex(IngestionError, "approval identity"):
                ingest(*case.ingest_args(case.root / "wrong-target"))
        with tempfile.TemporaryDirectory() as temp:
            case = LegacyBindingCase(Path(temp))
            summary_path = case.base / "summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["schemaVersion"] = "6.0.0"
            write(summary_path, summary)
            with self.assertRaisesRegex(IngestionError, "cannot be reused"):
                ingest(*case.ingest_args(case.root / "unknown-schema"))
        with tempfile.TemporaryDirectory() as temp:
            case = LegacyBindingCase(Path(temp))
            first = case.root / "first"
            ingest(*case.ingest_args(first))
            args = list(case.ingest_args(case.root / "reuse"))
            args[1] = first
            with self.assertRaisesRegex(IngestionError, "cannot be reused"):
                ingest(*args)

    @staticmethod
    def _mutate_binding(case: LegacyBindingCase, mutate) -> None:
        value = json.loads(case.binding.read_text(encoding="utf-8"))
        mutate(value)
        write(case.binding, value)


if __name__ == "__main__":
    unittest.main()
