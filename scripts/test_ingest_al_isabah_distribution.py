import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ingest_al_isabah_distribution import IngestionError, ingest, membership  # noqa: E402
from validate_public_corpus import validate as validate_public_corpus  # noqa: E402
from verify_al_isabah_distribution import CompatibilityError, verify_distribution  # noqa: E402


FIXTURES = ROOT / "fixtures" / "releases"
COMMIT = "a" * 40
TAG = f"public-working-{COMMIT}"
ASSET = f"al-isabah-public-distribution-{COMMIT}.zip"
CHECKSUM = f"{ASSET}.sha256"


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


def refresh_manifest(root: Path) -> None:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for record in manifest["files"]:
        path = root / record["path"]
        record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        record["bytes"] = path.stat().st_size
    write(manifest_path, manifest)


class DistributionCase:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.distribution = root / "distribution"
        shutil.copytree(FIXTURES / "al-isabah-v2-synthetic", self.distribution)
        shard = self.distribution / "records" / "volume-01.jsonl"
        shard.write_bytes(shard.read_bytes().replace(b"\r\n", b"\n"))
        self.rights = root / "rights.json"
        shutil.copyfile(FIXTURES / "al-isabah-rights-matrix-v1.synthetic.json", self.rights)
        self.authority = ROOT / "evidence" / "source-authorities" / "al-isabah.v1.json"
        self.release = root / "release.json"
        self.tag_ref = root / "tag-ref.json"
        self.archive = root / ASSET
        self.checksum = root / CHECKSUM
        self.finalize()

    def manifest(self) -> dict:
        return json.loads((self.distribution / "manifest.json").read_text(encoding="utf-8"))

    def record(self) -> dict:
        return json.loads((self.distribution / "records" / "volume-01.jsonl").read_text(encoding="utf-8"))

    def update_manifest(self, update) -> None:
        value = self.manifest()
        update(value)
        write(self.distribution / "manifest.json", value)

    def update_record(self, update) -> None:
        value = self.record()
        previous_id = value["id"]
        update(value)
        if value["id"] != previous_id:
            for formula in value.get("formulas", []):
                if formula.get("recordId") == previous_id:
                    formula["recordId"] = value["id"]
        path = self.distribution / "records" / "volume-01.jsonl"
        path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        data = path.read_bytes()
        self.update_manifest(
            lambda manifest: manifest["files"][0].update(
                sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)
            )
        )
        closure_path = self.distribution / "release-closure.json"
        closure = json.loads(closure_path.read_text(encoding="utf-8"))
        closure["outputInventory"][0].update(
            sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)
        )
        write(closure_path, closure)
        self.update_manifest(
            lambda manifest: manifest["releaseClosure"].update(
                sha256=hashlib.sha256(closure_path.read_bytes()).hexdigest()
            )
        )

    def finalize(self) -> None:
        if self.archive.exists():
            self.archive.unlink()
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(self.distribution.rglob("*")):
                if path.is_file():
                    bundle.write(path, path.relative_to(self.distribution).as_posix())
        write(
            self.release,
            {
                "tag_name": TAG,
                "target_commitish": COMMIT,
                "draft": False,
                "prerelease": True,
                "assets": [
                    {
                        "name": ASSET,
                        "size": self.archive.stat().st_size,
                        "digest": f"sha256:{hashlib.sha256(self.archive.read_bytes()).hexdigest()}",
                    }
                ],
            },
        )
        write(
            self.tag_ref,
            {
                "ref": f"refs/tags/{TAG}",
                "object": {"type": "commit", "sha": COMMIT},
            },
        )

    def add_checksum_sidecar(self, archive_sha: str | None = None) -> None:
        declared_sha = archive_sha or hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.checksum.write_bytes(f"{declared_sha}  {ASSET}\n".encode("ascii"))
        release = json.loads(self.release.read_text(encoding="utf-8"))
        release["assets"].append(
            {
                "name": CHECKSUM,
                "size": self.checksum.stat().st_size,
                "digest": f"sha256:{hashlib.sha256(self.checksum.read_bytes()).hexdigest()}",
            }
        )
        write(self.release, release)

    def verify(self, checksum: Path | None = None):
        return verify_distribution(
            self.distribution,
            self.archive,
            self.release,
            self.tag_ref,
            self.rights,
            self.authority,
            checksum=checksum,
        )


def base_corpus(root: Path) -> Path:
    base = root / "base"
    legacy_license = {
        "spdx": "CC-BY-NC-SA-4.0",
        "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    }
    legacy_matrix = {
        "id": "al-isabah-rights-legacy-synthetic",
        "schema": "al-isabah.book-rights-matrix.v1",
        "decision": "approved-under-cc-by-nc-sa-4.0",
        "reviewedOn": "2026-08-12",
        "followUp": "required-on-change",
    }
    legacy_rights = {
        "arabicSource": {
            "license": legacy_license,
            "attribution": "Synthetic legacy Arabic attribution",
        },
        "englishTranslation": {
            "license": legacy_license,
            "attribution": "Synthetic legacy English authorship",
        },
        "matrix": legacy_matrix,
        "excludedMaterial": ["synthetic restricted material"],
    }
    legacy_arabic = "Ù†Øµ Ø¹Ø±Ø¨ÙŠ Ù‚Ø¯ÙŠÙ… ØªØ¬Ø±ÙŠØ¨ÙŠ"
    legacy_title_arabic = "Ø¹Ù†ÙˆØ§Ù† Ù‚Ø¯ÙŠÙ… ØªØ¬Ø±ÙŠØ¨ÙŠ"
    legacy_display_hash = hashlib.sha256(
        f"{legacy_title_arabic} {legacy_arabic}".encode("utf-8")
    ).hexdigest()
    legacy_item = {
        "schemaVersion": "4.0.0",
        "corpusId": "old-corpus",
        "id": "synthetic-legacy-entry-0002",
        "kind": "entry",
        "sequence": 200,
        "printedEntryNumber": 2,
        "sourceEntryNumber": 2,
        "volume": 2,
        "title": {"en": "Synthetic legacy title", "ar": legacy_title_arabic},
        "translationState": "translated",
        "machineAssessment": "passed",
        "humanReview": "unreviewed",
        "publicEligibility": "eligible",
        "segments": [{
            "id": "synthetic-legacy-entry-0002-body",
            "arabic": legacy_arabic,
            "english": "Synthetic carried-forward English text.",
            "pages": [{
                "volume": 2,
                "printedPage": 2,
                "readerPage": None,
                "providerPage": "https://example.test/legacy-source",
            }],
            "machineState": "translated",
        }],
        "names": [],
        "unresolved": [],
        "honorificPolicyVersion": "1.0.0",
        "honorifics": [],
        "workflowStages": [
            {"stage": "machine_validation", "state": "complete", "summary": "Synthetic legacy validation passed."},
            {"stage": "human_review", "state": "pending", "summary": "Synthetic human review remains pending."},
        ],
        "source": {
            "authorityId": "al-isabah-openiti-5835c18-aco-v1",
            "entryNumber": 2,
            "pages": ["V02P002"],
            "sourceTextSha256": legacy_display_hash,
            "sourceExactTextSha256": "7" * 64,
            "sourceUrl": "https://example.test/legacy-source",
            "license": legacy_license,
            "attribution": legacy_rights["arabicSource"]["attribution"],
            "englishRights": legacy_rights["englishTranslation"],
            "rightsMatrix": legacy_matrix,
            "alignment": {"method": "al-isabah-public-distribution-v1", "titleScore": 1.0, "bodyScore": 1.0},
        },
        "provenance": {
            "sourceAuthorityId": "al-isabah-openiti-5835c18-aco-v1",
            "sourceArtifactSha256": "6" * 64,
            "sourceTextSha256": legacy_display_hash,
            "sourceExactTextSha256": "7" * 64,
        },
    }
    volumes = [
        {
            "id": f"volume-{number:02d}",
            "number": number,
            "label": f"Volume {number}",
            "availability": "complete_translation" if number == 2 else "not_translated",
            "sourceItemCount": 1 if number == 2 else 0,
            "itemCount": 1 if number == 2 else 0,
            "sectionCount": 0,
            "firstPrintedPage": None,
            "lastPrintedPage": None,
            "description": "No public translation.",
        }
        for number in range(1, 9)
    ]
    write(
        base / "summary.json",
        {
            "schemaVersion": "4.0.0",
            "work": {"slug": "al-isabah", "titleAr": "عنوان تجريبي", "titleEn": "Synthetic title"},
            "corpus": {
                "id": "old-corpus",
                "sourceRepository": "https://github.com/OpenITI/0875AH",
                "sourceCommit": "5" * 40,
                "sourceAuthorityId": "al-isabah-openiti-5835c18-aco-v1",
                "sourceArtifactSha256": "6" * 64,
                "license": legacy_license,
                "rights": legacy_rights,
                "generatedAt": "2026-08-12T00:00:00Z",
                "promotionStatus": "blocked",
                "publicationStatus": "public-working",
            },
            "counts": {"entries": 1, "passages": 0, "translated": 1, "needsAttention": 0, "unresolvedItems": 0, "humanReviewed": 0},
            "exclusions": {"contextualPassagesPendingPublicSourceAlignment": 0, "recordsPendingRemediation": 0},
            "volumes": volumes,
        },
    )
    write(base / "index.json", {
        "schemaVersion": "4.0.0",
        "corpusId": "old-corpus",
        "items": [{
            "id": legacy_item["id"],
            "kind": "entry",
            "sequence": 200,
            "printedEntryNumber": 2,
            "sourceEntryNumber": 2,
            "volume": 2,
            "printedPageStart": 2,
            "printedPageEnd": 2,
            "sectionId": "volume-02-pages-0001-0025",
            "titleEn": legacy_item["title"]["en"],
            "titleAr": legacy_item["title"]["ar"],
            "translationState": "translated",
            "machineAssessment": "passed",
            "humanReview": "unreviewed",
            "unresolvedCount": 0,
            "publicEligibility": "eligible",
        }],
    })
    write(base / "items" / f"{legacy_item['id']}.json", legacy_item)
    write(base / "quarantine.json", {"records": []})
    write(base / "exclusions.json", {"counts": {"contextualPassagesPendingPublicSourceAlignment": 0, "recordsPendingRemediation": 0}, "records": []})
    return base


def add_base_passage(base: Path, passage_id: str) -> None:
    entry_path = base / "items" / "synthetic-legacy-entry-0002.json"
    passage = json.loads(entry_path.read_text(encoding="utf-8"))
    passage.update(
        id=passage_id,
        kind="passage",
        sequence=99,
        printedEntryNumber=None,
        sourceEntryNumber=1,
        volume=1,
        relationship="Synthetic structure before entry 1",
    )
    passage["segments"][0]["id"] = f"{passage_id}-body"
    write(base / "items" / f"{passage_id}.json", passage)
    index_path = base / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["items"].append(
        {
            "id": passage_id,
            "kind": "passage",
            "sequence": 99,
            "printedEntryNumber": None,
            "sourceEntryNumber": 1,
            "volume": 1,
            "printedPageStart": 1,
            "printedPageEnd": 1,
            "sectionId": "volume-01-pages-0001-0025",
            "titleEn": passage["title"]["en"],
            "titleAr": passage["title"]["ar"],
            "translationState": "translated",
            "machineAssessment": "passed",
            "humanReview": "unreviewed",
            "unresolvedCount": 0,
            "publicEligibility": "eligible",
            "relationship": passage["relationship"],
        }
    )
    write(index_path, index)


def synthetic_preceding_material(passage_id: str) -> dict:
    return {
        "id": passage_id,
        "kind": "front_matter",
        "arabic": "نص تمهيدي تجريبي",
        "english": "Synthetic structural passage.",
        "heading": {
            "arabic": "تمهيد تجريبي",
            "english": "Synthetic front matter",
        },
        "sourceSha256": "8" * 64,
        "pages": [{"volume": 1, "page": 1}],
        "unresolved": [],
        "humanReview": "unreviewed",
    }


class AlIsabahDistributionVerificationTests(unittest.TestCase):
    def test_valid_v2_binds_release_source_rights_and_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest, records, binding = DistributionCase(Path(temp)).verify()
            self.assertEqual(manifest["schemaVersion"], "2.0.0")
            self.assertEqual(len(records), 1)
            self.assertEqual(binding["sourceAuthorityId"], "al-isabah-openiti-5835c18-aco-v1")
            self.assertEqual(binding["rightsMatrix"]["id"], "al-isabah-rights-synthetic")
            self.assertEqual(manifest["counts"]["humanReviewed"], 0)
            self.assertNotEqual(
                manifest["packets"][0]["packetId"], records[0]["packetId"]
            )

    def test_release_accepts_matching_checksum_sidecar(self):
        with tempfile.TemporaryDirectory() as temp:
            case = DistributionCase(Path(temp))
            case.add_checksum_sidecar()
            _, _, binding = case.verify(case.checksum)
            self.assertEqual(
                binding["sha256"],
                hashlib.sha256(case.archive.read_bytes()).hexdigest(),
            )

    def test_release_rejects_missing_or_mismatched_checksum_sidecar(self):
        with tempfile.TemporaryDirectory() as temp:
            case = DistributionCase(Path(temp))
            case.add_checksum_sidecar()
            with self.assertRaisesRegex(CompatibilityError, "sidecar is missing"):
                case.verify()
        with tempfile.TemporaryDirectory() as temp:
            case = DistributionCase(Path(temp))
            case.add_checksum_sidecar("0" * 64)
            with self.assertRaisesRegex(CompatibilityError, "declaration does not match"):
                case.verify(case.checksum)

    def test_release_rejects_duplicate_or_unsupported_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            case = DistributionCase(Path(temp))
            release = json.loads(case.release.read_text(encoding="utf-8"))
            release["assets"].append(copy.deepcopy(release["assets"][0]))
            write(case.release, release)
            with self.assertRaisesRegex(CompatibilityError, "exactly one distribution archive"):
                case.verify()
        with tempfile.TemporaryDirectory() as temp:
            case = DistributionCase(Path(temp))
            release = json.loads(case.release.read_text(encoding="utf-8"))
            release["assets"].append(
                {"name": "unrelated.txt", "size": 0, "digest": "sha256:" + "0" * 64}
            )
            write(case.release, release)
            with self.assertRaisesRegex(CompatibilityError, "unsupported asset"):
                case.verify()

    def test_record_v21_accepts_only_explicit_title_only_content(self):
        with tempfile.TemporaryDirectory() as temp:
            case = DistributionCase(Path(temp))
            case.update_record(
                lambda value: value.update(
                    schemaVersion="2.1.0",
                    bodyState="title-only",
                    arabic="",
                    english="",
                    formulas=[],
                )
            )
            case.finalize()
            _, records, _ = case.verify()
            self.assertEqual(records[0]["bodyState"], "title-only")
            self.assertTrue(records[0]["title"]["arabic"])
            self.assertTrue(records[0]["title"]["english"])

    def test_record_rejects_undeclared_or_invalid_title_only_content(self):
        mutations = [
            lambda value: value.update(schemaVersion="2.1.0", arabic="", english=""),
            lambda value: value.update(schemaVersion="2.1.0", bodyState="title-only"),
            lambda value: value.update(bodyState=None),
            lambda value: value.update(schemaVersion="2.2.0"),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index), tempfile.TemporaryDirectory() as temp:
                case = DistributionCase(Path(temp))
                case.update_record(mutate)
                case.finalize()
                with self.assertRaisesRegex(CompatibilityError, "body state"):
                    case.verify()

    def test_record_formula_must_match_the_pinned_upstream_projection(self):
        with tempfile.TemporaryDirectory() as temp:
            case = DistributionCase(Path(temp))
            case.update_record(
                lambda value: value["formulas"][0].update(
                    observedArabic="صيغة تجريبية غير مسجلة"
                )
            )
            case.finalize()
            with self.assertRaisesRegex(CompatibilityError, "formula"):
                case.verify()

    def test_v1_is_rollback_only_and_unknown_major_rejects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            distribution = root / "distribution"
            distribution.mkdir()
            shutil.copyfile(FIXTURES / "al-isabah-v1-rollback-only.synthetic.json", distribution / "manifest.json")
            args = [distribution, root / "archive.zip", root / "release.json", root / "tag.json", root / "rights.json", root / "authority.json"]
            with self.assertRaisesRegex(CompatibilityError, "rollback-only"):
                verify_distribution(*args)
            write(distribution / "manifest.json", {"schemaVersion": "3.0.0"})
            with self.assertRaisesRegex(CompatibilityError, "unsupported"):
                verify_distribution(*args)

    def test_release_repo_tag_commit_and_digest_mismatches_reject(self):
        mutations = [
            lambda case: case.update_manifest(lambda value: value["repository"].update(url="https://example.invalid/repo")),
            lambda case: write(case.tag_ref, {"object": {"type": "commit", "sha": "b" * 40}}),
            lambda case: case.update_manifest(lambda value: value["repository"].update(commit="b" * 40)),
            lambda case: write(case.release, {**json.loads(case.release.read_text()), "assets": [{**json.loads(case.release.read_text())["assets"][0], "digest": "sha256:" + "0" * 64}]}),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)), tempfile.TemporaryDirectory() as temp:
                case = DistributionCase(Path(temp))
                mutate(case)
                if mutations.index(mutate) in {0, 2}:
                    case.finalize()
                with self.assertRaises(CompatibilityError):
                    case.verify()

    def test_source_rights_policy_count_and_hash_mismatches_reject(self):
        mutations = [
            lambda case: case.update_record(lambda value: value["source"].update(commit="b" * 40)),
            lambda case: case.update_manifest(lambda value: value["rights"].update(matrixId="wrong-matrix")),
            lambda case: case.update_record(lambda value: value["policy"].update(bindingSha256="bad")),
            lambda case: case.update_manifest(lambda value: value["counts"].update(entries=2)),
            lambda case: (case.distribution / "records" / "volume-01.jsonl").write_text("{}\n", encoding="utf-8"),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index), tempfile.TemporaryDirectory() as temp:
                case = DistributionCase(Path(temp))
                mutate(case)
                case.finalize()
                with self.assertRaises(CompatibilityError):
                    case.verify()

    def test_false_canonical_promotion_and_prohibited_internal_fields_reject(self):
        with tempfile.TemporaryDirectory() as temp:
            case = DistributionCase(Path(temp))
            case.update_manifest(lambda value: value.update(canonicalPromotion="complete"))
            case.finalize()
            with self.assertRaisesRegex(CompatibilityError, "promotion"):
                case.verify()
        with tempfile.TemporaryDirectory() as temp:
            case = DistributionCase(Path(temp))
            case.update_record(lambda value: value.update(model_trace="private"))
            case.finalize()
            with self.assertRaisesRegex(CompatibilityError, "public contract|internal"):
                case.verify()

    def test_archive_must_match_the_verified_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            case = DistributionCase(Path(temp))
            case.update_record(lambda value: value.update(english="Changed synthetic text."))
            with self.assertRaisesRegex(CompatibilityError, "archive bytes"):
                case.verify()

    def test_review_disclosure_and_release_closure_are_required(self):
        with tempfile.TemporaryDirectory() as temp:
            case = DistributionCase(Path(temp))
            case.update_record(lambda value: value.pop("humanReview"))
            case.finalize()
            with self.assertRaisesRegex(CompatibilityError, "public contract|review"):
                case.verify()
        with tempfile.TemporaryDirectory() as temp:
            case = DistributionCase(Path(temp))
            review = case.distribution / "reviews" / "issue-0136.json"
            review.write_text("{}\n", encoding="utf-8")
            case.finalize()
            with self.assertRaisesRegex(CompatibilityError, "closure output|archive bytes"):
                case.verify()


class AlIsabahDistributionIngestionTests(unittest.TestCase):
    def build_candidate(self, root: Path, case: DistributionCase | None = None) -> Path:
        case = case or DistributionCase(root)
        ingest(
            case.distribution,
            base_corpus(root),
            root / "output",
            "2026-08-15T18:00:00Z",
            case.archive,
            case.release,
            case.tag_ref,
            case.rights,
            case.authority,
        )
        return root / "output"

    def test_ingestion_preserves_separate_rights_and_plans_idempotently(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = DistributionCase(root)
            args = (
                case.distribution, base_corpus(root), root / "output", "2026-08-15T18:00:00Z",
                case.archive, case.release, case.tag_ref, case.rights, case.authority,
            )
            activation = ingest(*args)
            summary = json.loads((root / "output" / "summary.json").read_text(encoding="utf-8"))
            item = json.loads((root / "output" / "items" / "isabah-entry-00000001.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["schemaVersion"], "5.0.0")
            self.assertNotIn("rights", summary["corpus"])
            cohorts = {cohort["id"]: cohort for cohort in summary["corpus"]["cohorts"]}
            self.assertEqual(len(cohorts), 2)
            self.assertEqual(
                cohorts[item["cohortId"]]["rights"]["matrix"]["id"],
                "al-isabah-rights-synthetic",
            )
            legacy = json.loads(
                (root / "output" / "items" / "synthetic-legacy-entry-0002.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                cohorts[legacy["cohortId"]]["rights"]["matrix"]["id"],
                "al-isabah-rights-legacy-synthetic",
            )
            self.assertEqual(legacy["source"]["sourceCommit"], "5" * 40)
            self.assertEqual(legacy["provenance"]["sourceArtifactSha256"], "6" * 64)
            self.assertEqual(item["source"]["producerAuthorityId"], "openiti-cleaned-arabic-comparison")
            self.assertEqual(item["id"], "isabah-entry-00000001")
            self.assertEqual(item["source"]["distributionRecordId"], "synthetic-entry-0001")
            self.assertEqual(item["provenance"]["distributionRecordId"], "synthetic-entry-0001")
            self.assertEqual(item["humanReview"], "unreviewed")
            self.assertEqual(item["honorifics"], [])
            self.assertIn(
                "O God, bless Muḥammad and the family of Muḥammad.",
                item["segments"][0]["english"],
            )
            self.assertIn("englishRights", item["source"])
            self.assertEqual(validate_public_corpus(root / "output"), [])
            self.assertEqual(activation["rollback"]["previousCorpusId"], "old-corpus")
            first_plan = copy.deepcopy(activation)
            shutil.rmtree(root / "output")
            (root / "activation.json").unlink()
            second_plan = ingest(*args)
            self.assertEqual(first_plan, second_plan)

    def test_ingestion_preserves_title_only_entries_without_inventing_body_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = DistributionCase(root)
            case.update_record(
                lambda value: value.update(
                    schemaVersion="2.1.0",
                    bodyState="title-only",
                    arabic="",
                    english="",
                    formulas=[],
                )
            )
            case.finalize()
            output = self.build_candidate(root, case)
            item = json.loads(
                (output / "items" / "isabah-entry-00000001.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(item["title"]["ar"], "عنوان تجريبي")
            self.assertEqual(item["title"]["en"], "Synthetic title")
            self.assertEqual(item["segments"][0]["arabic"], "")
            self.assertEqual(item["segments"][0]["english"], "")
            self.assertEqual(validate_public_corpus(output), [])

    def test_current_distribution_content_is_not_bound_to_legacy_projection_repairs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = DistributionCase(root)
            case.update_record(
                lambda value: value.update(printedEntryNumber=11441)
            )
            case.finalize()
            output = self.build_candidate(root, case)
            item = json.loads(
                (output / "items" / "isabah-entry-00011441.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(item["sourceEntryNumber"], 11441)
            self.assertEqual(item["title"]["en"], "Synthetic title")
            self.assertEqual(validate_public_corpus(output), [])

    def test_printed_entry_number_defines_stable_public_reader_id(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = DistributionCase(root)
            case.update_record(
                lambda value: value.update(
                    volume=8,
                    printedEntryNumber=11827,
                    pages=[{"volume": 8, "page": 126}],
                )
            )
            case.finalize()
            output = self.build_candidate(root, case)
            item = json.loads(
                (output / "items" / "isabah-entry-00011827.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(item["id"], "isabah-entry-00011827")
            self.assertEqual(item["printedEntryNumber"], 11827)
            self.assertEqual(item["source"]["distributionRecordId"], "synthetic-entry-0001")
            self.assertEqual(validate_public_corpus(output), [])

    def test_verification_failure_writes_no_output_or_activation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = DistributionCase(root)
            case.update_manifest(lambda value: value["counts"].update(entries=2))
            case.finalize()
            with self.assertRaises(IngestionError):
                ingest(
                    case.distribution, base_corpus(root), root / "output", "2026-08-15T18:00:00Z",
                    case.archive, case.release, case.tag_ref, case.rights, case.authority,
                )
            self.assertFalse((root / "output").exists())
            self.assertFalse((root / "activation.json").exists())

    def test_unknown_compact_formula_fails_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = DistributionCase(root)
            case.update_record(
                lambda value: value["formulas"][0].update(
                    observedArabic="صيغة غير مسجلة",
                    targetRealization="Unregistered formula.",
                )
            )
            case.finalize()
            with self.assertRaisesRegex(IngestionError, "pinned registry"):
                ingest(
                    case.distribution,
                    base_corpus(root),
                    root / "output",
                    "2026-08-15T18:00:00Z",
                    case.archive,
                    case.release,
                    case.tag_ref,
                    case.rights,
                    case.authority,
                )
            self.assertFalse((root / "output").exists())
            self.assertFalse((root / "activation.json").exists())

    def test_mixed_cohort_tampering_and_false_global_claims_fail_closed(self):
        mutations = [
            (
                lambda root, summary: summary["corpus"]["cohorts"][0]["membership"].update(itemCount=99),
                "membership count mismatch",
            ),
            (
                lambda root, summary: summary["corpus"]["cohorts"][0]["membership"].update(itemIdsSha256="0" * 64),
                "membership hash mismatch",
            ),
            (
                lambda root, summary: summary["corpus"].update(rights={}),
                "false corpus-wide source or rights claim",
            ),
            (
                lambda root, summary: summary["corpus"]["cohorts"][0].update(kind="unknown"),
                "cohort kind is unknown",
            ),
        ]
        for mutate, expected in mutations:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                output = self.build_candidate(root)
                summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
                mutate(output, summary)
                write(output / "summary.json", summary)
                self.assertTrue(any(expected in error for error in validate_public_corpus(output)))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = self.build_candidate(root)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            cohorts = summary["corpus"]["cohorts"]
            legacy_id = cohorts[0]["membership"]["itemIds"][0]
            cohorts[1]["membership"] = membership(
                [*cohorts[1]["membership"]["itemIds"], legacy_id]
            )
            write(output / "summary.json", summary)
            errors = validate_public_corpus(output)
            self.assertTrue(any("membership overlaps" in error for error in errors))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = self.build_candidate(root)
            legacy_path = output / "items" / "synthetic-legacy-entry-0002.json"
            legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
            legacy["source"]["sourceCommit"] = "0" * 40
            write(legacy_path, legacy)
            self.assertTrue(
                any("source commit differs from cohort" in error for error in validate_public_corpus(output))
            )

    def test_active_pointer_preserves_historical_adapter_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = self.build_candidate(root)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            current_cohort = next(
                cohort
                for cohort in summary["corpus"]["cohorts"]
                if cohort["upstream"].get("distributionId")
                == manifest["distribution"]["id"]
            )
            item_id = current_cohort["membership"]["itemIds"][0]
            detail_path = output / "items" / f"{item_id}.json"
            detail = json.loads(detail_path.read_text(encoding="utf-8"))
            detail["honorificPolicyVersion"] = "historic-policy"
            write(detail_path, detail)
            for section_path in (output / "sections").glob("*.json"):
                section = json.loads(section_path.read_text(encoding="utf-8"))
                for position, embedded in enumerate(section["items"]):
                    if embedded["id"] == item_id:
                        section["items"][position] = detail
                        write(section_path, section)
            refresh_manifest(output)
            pointer_path = root / "current.json"
            write(pointer_path, {
                "schemaVersion": "1.0.0",
                "corpusId": summary["corpus"]["id"],
                "prefix": f"public-corpora/al-isabah/{summary['corpus']['id']}",
                "distributionId": manifest["distribution"]["id"],
                "distributionCommit": manifest["distribution"]["commit"],
                "distributionManifestSha256": manifest["distribution"]["manifestSha256"],
            })

            self.assertTrue(
                any(
                    f"wrong honorific policy version for {item_id}" in error
                    for error in validate_public_corpus(output)
                )
            )
            self.assertEqual(
                validate_public_corpus(
                    output, active_pointer_path=pointer_path
                ),
                [],
            )
            pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
            pointer["corpusId"] = "different-corpus"
            write(pointer_path, pointer)
            errors = validate_public_corpus(
                output, active_pointer_path=pointer_path
            )
            self.assertTrue(any("active pointer: identity differs" in error for error in errors))
            self.assertTrue(any("wrong honorific policy" in error for error in errors))

    def test_same_source_correction_records_explicit_supersession(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = DistributionCase(root)
            case.update_record(
                lambda record: record.update(
                    id="synthetic-legacy-entry-0002",
                    volume=2,
                    printedEntryNumber=2,
                    pages=[{"volume": 2, "page": 2}],
                )
            )
            case.finalize()
            output = self.build_candidate(root, case)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            cohorts = {cohort["kind"]: cohort for cohort in summary["corpus"]["cohorts"]}
            self.assertEqual(cohorts["legacy-schema-4"]["membership"]["itemCount"], 0)
            self.assertEqual(
                cohorts["distribution-v2"]["supersedes"][0]["itemIds"],
                ["synthetic-legacy-entry-0002"],
            )
            self.assertEqual(validate_public_corpus(output), [])
            second = root / "output-second"
            ingest(
                case.distribution, output, second, "2026-08-15T18:00:00Z",
                case.archive, case.release, case.tag_ref, case.rights, case.authority,
            )
            self.assertEqual(
                (output / "summary.json").read_bytes(),
                (second / "summary.json").read_bytes(),
            )

    def test_unique_legacy_source_entry_alias_is_superseded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = DistributionCase(root)
            case.update_record(
                lambda record: record.update(
                    volume=2,
                    printedEntryNumber=2,
                    pages=[{"volume": 2, "page": 2}],
                )
            )
            case.finalize()
            output = self.build_candidate(root, case)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            index = json.loads((output / "index.json").read_text(encoding="utf-8"))
            cohorts = {cohort["kind"]: cohort for cohort in summary["corpus"]["cohorts"]}
            volume = next(volume for volume in summary["volumes"] if volume["number"] == 2)
            self.assertEqual(
                [item["id"] for item in index["items"] if item["volume"] == 2],
                ["isabah-entry-00000002"],
            )
            self.assertEqual(volume["itemCount"], 1)
            self.assertEqual(volume["sourceItemCount"], 1)
            self.assertEqual(cohorts["legacy-schema-4"]["membership"]["itemCount"], 0)
            self.assertEqual(
                cohorts["distribution-v2"]["supersedes"][0]["itemIds"],
                ["synthetic-legacy-entry-0002"],
            )
            self.assertEqual(validate_public_corpus(output), [])

    def test_projected_passage_replaces_carried_member_by_stable_id(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = DistributionCase(root)
            passage_id = "synthetic-structural-passage-0001"
            case.update_record(
                lambda record: record["precedingMaterial"].append(
                    synthetic_preceding_material(passage_id)
                )
            )
            case.finalize()
            base = base_corpus(root)
            add_base_passage(base, passage_id)
            output = root / "output"
            ingest(
                case.distribution,
                base,
                output,
                "2026-08-15T18:00:00Z",
                case.archive,
                case.release,
                case.tag_ref,
                case.rights,
                case.authority,
            )
            summary = json.loads(
                (output / "summary.json").read_text(encoding="utf-8")
            )
            item = json.loads(
                (output / "items" / f"{passage_id}.json").read_text(
                    encoding="utf-8"
                )
            )
            cohorts = {
                cohort["kind"]: cohort
                for cohort in summary["corpus"]["cohorts"]
            }
            self.assertEqual(item["cohortId"], cohorts["distribution-v2"]["id"])
            self.assertNotIn(
                passage_id, cohorts["legacy-schema-4"]["membership"]["itemIds"]
            )
            self.assertIn(
                passage_id,
                cohorts["distribution-v2"]["supersedes"][0]["itemIds"],
            )
            self.assertEqual(validate_public_corpus(output), [])

    def test_duplicate_incoming_projection_ids_fail_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = DistributionCase(root)
            case.update_record(
                lambda record: record["precedingMaterial"].extend([
                    synthetic_preceding_material("duplicate-structural-passage"),
                    synthetic_preceding_material("duplicate-structural-passage"),
                ])
            )
            case.finalize()
            with self.assertRaisesRegex(
                IngestionError, "incoming projection contains invalid or duplicate"
            ):
                ingest(
                    case.distribution,
                    base_corpus(root),
                    root / "output",
                    "2026-08-15T18:00:00Z",
                    case.archive,
                    case.release,
                    case.tag_ref,
                    case.rights,
                    case.authority,
                )
            self.assertFalse((root / "output").exists())
            self.assertFalse((root / "activation.json").exists())

    def test_unknown_base_major_fails_before_candidate_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = DistributionCase(root)
            base = base_corpus(root)
            summary = json.loads((base / "summary.json").read_text(encoding="utf-8"))
            summary["schemaVersion"] = "6.0.0"
            write(base / "summary.json", summary)
            with self.assertRaisesRegex(IngestionError, "unsupported major"):
                ingest(
                    case.distribution, base, root / "output", "2026-08-15T18:00:00Z",
                    case.archive, case.release, case.tag_ref, case.rights, case.authority,
                )
            self.assertFalse((root / "output").exists())
            self.assertFalse((root / "activation.json").exists())

    def test_schema_5_candidate_is_a_compatible_idempotent_base(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = DistributionCase(root)
            first = self.build_candidate(root, case)
            second = root / "output-second"
            ingest(
                case.distribution, first, second, "2026-08-15T18:00:00Z",
                case.archive, case.release, case.tag_ref, case.rights, case.authority,
            )
            self.assertEqual(validate_public_corpus(second), [])
            for relative in (
                "summary.json", "index.json",
                "items/isabah-entry-00000001.json",
                "items/synthetic-legacy-entry-0002.json",
            ):
                self.assertEqual((first / relative).read_bytes(), (second / relative).read_bytes())

    def test_schema_5_upstream_id_projection_is_replaced_without_duplication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = DistributionCase(root)
            first = self.build_candidate(root, case)
            stable_id = "isabah-entry-00000001"
            upstream_id = "synthetic-entry-0001"
            stable_path = first / "items" / f"{stable_id}.json"
            item = json.loads(stable_path.read_text(encoding="utf-8"))
            item["id"] = upstream_id
            item["segments"][0]["id"] = f"{upstream_id}-body"
            write(first / "items" / f"{upstream_id}.json", item)
            stable_path.unlink()

            index_path = first / "index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            listed = next(value for value in index["items"] if value["id"] == stable_id)
            listed["id"] = upstream_id
            write(index_path, index)

            summary_path = first / "summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            cohort = next(
                value
                for value in summary["corpus"]["cohorts"]
                if value["kind"] == "distribution-v2"
            )
            cohort["membership"] = membership([upstream_id])
            write(summary_path, summary)

            second = root / "output-second"
            ingest(
                case.distribution, first, second, "2026-08-15T18:00:00Z",
                case.archive, case.release, case.tag_ref, case.rights, case.authority,
            )
            second_index = json.loads(
                (second / "index.json").read_text(encoding="utf-8")
            )
            projected = [
                value
                for value in second_index["items"]
                if value["sourceEntryNumber"] == 1
            ]
            self.assertEqual([value["id"] for value in projected], [stable_id])
            self.assertFalse((second / "items" / f"{upstream_id}.json").exists())
            self.assertEqual(validate_public_corpus(second), [])

    def test_partial_distribution_over_different_bases_cannot_share_a_prefix(self):
        corpus_ids = []
        with tempfile.TemporaryDirectory() as first_temp, tempfile.TemporaryDirectory() as second_temp:
            for position, temp in enumerate((first_temp, second_temp)):
                root = Path(temp)
                case = DistributionCase(root)
                base = base_corpus(root)
                if position:
                    legacy_path = base / "items" / "synthetic-legacy-entry-0002.json"
                    legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
                    legacy["segments"][0]["english"] = "Corrected synthetic legacy English."
                    write(legacy_path, legacy)
                activation = ingest(
                    case.distribution, base, root / "output", "2026-08-15T18:00:00Z",
                    case.archive, case.release, case.tag_ref, case.rights, case.authority,
                )
                corpus_ids.append(activation["corpusId"])
            self.assertNotEqual(corpus_ids[0], corpus_ids[1])


if __name__ == "__main__":
    unittest.main()
