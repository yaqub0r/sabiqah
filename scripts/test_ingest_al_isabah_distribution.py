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

from ingest_al_isabah_distribution import IngestionError, ingest  # noqa: E402
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
    volumes = [
        {
            "id": f"volume-{number:02d}",
            "number": number,
            "label": f"Volume {number}",
            "availability": "not_translated",
            "sourceItemCount": 0,
            "itemCount": 0,
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
                "generatedAt": "2026-08-12T00:00:00Z",
                "promotionStatus": "blocked",
                "publicationStatus": "public-working",
            },
            "counts": {"entries": 0, "passages": 0, "translated": 0, "needsAttention": 0, "unresolvedItems": 0, "humanReviewed": 0},
            "exclusions": {"contextualPassagesPendingPublicSourceAlignment": 0, "recordsPendingRemediation": 0},
            "volumes": volumes,
        },
    )
    write(base / "index.json", {"schemaVersion": "4.0.0", "corpusId": "old-corpus", "items": []})
    write(base / "quarantine.json", {"records": []})
    write(base / "exclusions.json", {"counts": {"contextualPassagesPendingPublicSourceAlignment": 0, "recordsPendingRemediation": 0}, "records": []})
    return base


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
            self.assertEqual(summary["corpus"]["rights"]["matrix"]["id"], "al-isabah-rights-synthetic")
            self.assertIn("arabicSource", summary["corpus"]["rights"])
            self.assertIn("englishTranslation", summary["corpus"]["rights"])
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


if __name__ == "__main__":
    unittest.main()
