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


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


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
        update(value)
        path = self.distribution / "records" / "volume-01.jsonl"
        path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        data = path.read_bytes()
        self.update_manifest(
            lambda manifest: manifest["files"][0].update(
                sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)
            )
        )

    def finalize(self) -> None:
        if self.archive.exists():
            self.archive.unlink()
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(self.distribution / "manifest.json", "manifest.json")
            bundle.write(
                self.distribution / "records" / "volume-01.jsonl",
                "records/volume-01.jsonl",
            )
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

    def verify(self):
        return verify_distribution(
            self.distribution,
            self.archive,
            self.release,
            self.tag_ref,
            self.rights,
            self.authority,
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
            item = json.loads((root / "output" / "items" / "synthetic-entry-0001.json").read_text(encoding="utf-8"))
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
            self.assertEqual(item["source"]["producerAuthorityId"], "openiti-jk000533-5835c183")
            self.assertIn("englishRights", item["source"])
            self.assertEqual(validate_public_corpus(root / "output"), [])
            self.assertEqual(activation["rollback"]["previousCorpusId"], "old-corpus")
            first_plan = copy.deepcopy(activation)
            shutil.rmtree(root / "output")
            (root / "activation.json").unlink()
            second_plan = ingest(*args)
            self.assertEqual(first_plan, second_plan)

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

    def test_same_id_correction_records_explicit_supersession(self):
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
                lambda record: record["precedingMaterial"].append(
                    synthetic_preceding_material(record["id"])
                )
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
                "items/synthetic-entry-0001.json",
                "items/synthetic-legacy-entry-0002.json",
            ):
                self.assertEqual((first / relative).read_bytes(), (second / relative).read_bytes())

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
