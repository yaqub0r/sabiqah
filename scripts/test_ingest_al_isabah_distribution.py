import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from extract_al_isabah_distribution import extract


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "ingest_al_isabah_distribution",
    ROOT / "scripts" / "ingest_al_isabah_distribution.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["ingest_al_isabah_distribution"] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


class AlIsabahDistributionIngestionTests(unittest.TestCase):
    commit = "a" * 40

    def base_corpus(self, root: Path) -> Path:
        base = root / "base"
        summary = {
            "schemaVersion": "4.0.0",
            "work": {"slug": "al-isabah", "titleAr": "الإصابة", "titleEn": "Al-Isabah"},
            "corpus": {
                "id": "old-corpus",
                "sourceRepository": "https://github.com/OpenITI/0875AH",
                "sourceCommit": "5" * 40,
                "generatedAt": "2026-08-12T00:00:00Z",
                "promotionStatus": "blocked",
                "sourceAuthorityId": "old-authority",
                "sourceArtifactSha256": "b" * 64,
                "publicationStatus": "public-working",
                "license": {"spdx": "CC-BY-NC-SA-4.0", "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/"},
            },
            "counts": {"entries": 0, "passages": 0, "translated": 0, "needsAttention": 0, "unresolvedItems": 0, "humanReviewed": 0, "sourceInventory": 0, "quarantined": 0},
            "exclusions": {"contextualPassagesPendingPublicSourceAlignment": 0, "recordsPendingRemediation": 0},
            "volumes": [
                {"id": f"volume-{number:02d}", "number": number, "label": f"Volume {number}", "availability": "not_translated", "sourceItemCount": 0, "itemCount": 0, "sectionCount": 0, "firstPrintedPage": None, "lastPrintedPage": None, "description": "No public translation."}
                for number in range(1, 9)
            ],
        }
        write(base / "summary.json", summary)
        write(base / "index.json", {"schemaVersion": "4.0.0", "corpusId": "old-corpus", "items": []})
        write(base / "quarantine.json", {"schemaVersion": "4.0.0", "corpusId": "old-corpus", "sourceInventoryCount": 0, "publicItemCount": 0, "quarantinedCount": 0, "records": []})
        write(base / "exclusions.json", {"schemaVersion": "4.0.0", "corpusId": "old-corpus", "counts": summary["exclusions"], "records": []})
        return base

    def distribution(self, root: Path) -> Path:
        distribution = root / "distribution"
        records = []
        for ordinal in (1310, 1311):
            records.append({
                "schemaVersion": "1.0.0",
                "id": f"openiti-unit-{ordinal}",
                "kind": "entry",
                "workId": "ibn-hajar-al-isabah",
                "packetId": "test-packet",
                "sourceOrdinal": ordinal,
                "printedEntryNumber": 1311,
                "canonicalEntryId": None,
                "volume": 1,
                "pages": [{"volume": 1, "page": 500}],
                "title": {"arabic": f"اسم {ordinal}", "english": f"Name {ordinal}", "state": "ready", "method": "primary-name-candidate"},
                "arabic": f"نص {ordinal}",
                "english": f"Translation {ordinal}.",
                "precedingMaterial": [],
                "names": [],
                "unresolved": [],
                "formulas": [],
                "machineAssessment": "passed",
                "humanReview": "unreviewed",
                "source": {
                    "authorityId": "openiti-test-authority",
                    "repository": "https://github.com/OpenITI/0875AH",
                    "commit": "5" * 40,
                    "path": "data/source.mARkdown",
                    "artifactSha256": "b" * 64,
                    "exactTextSha256": hashlib.sha256(f"raw-{ordinal}".encode()).hexdigest(),
                    "lineStart": ordinal,
                    "lineEnd": ordinal,
                    "license": {"spdx": "CC-BY-NC-SA-4.0", "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/", "attribution": "OpenITI"},
                },
                "policy": {"bindingSha256": "c" * 64, "contracts": []},
            })
        shard = distribution / "records" / "volume-01.jsonl"
        shard.parent.mkdir(parents=True)
        shard.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
        data = shard.read_bytes()
        manifest = {
            "schemaVersion": "1.0.0",
            "distributionId": f"al-isabah-public-working-{self.commit[:12]}",
            "publicationStatus": "public-working",
            "canonicalPromotion": "blocked",
            "generatedAt": "2026-08-14T16:22:30Z",
            "repository": {"url": "https://github.com/yaqub0r/al-isabah", "commit": self.commit},
            "authorities": [{"sourceId": "openiti-test-authority", "sha256": "b" * 64, "license": {"spdx": "CC-BY-NC-SA-4.0"}}],
            "counts": {"entries": 2},
            "duplicatePrintedEntryNumbers": [{"printedEntryNumber": 1311, "recordIds": ["openiti-unit-1310", "openiti-unit-1311"]}],
            "files": [{"path": "records/volume-01.jsonl", "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "recordCount": 2, "volume": 1}],
        }
        write(distribution / "manifest.json", manifest)
        return distribution

    def test_ingestion_preserves_source_identity_when_printed_number_repeats(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "output"
            activation = MODULE.ingest(
                self.distribution(root),
                self.base_corpus(root),
                output,
                "2026-08-14T18:00:00Z",
            )
            index = json.loads((output / "index.json").read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in index["items"]], ["openiti-unit-1310", "openiti-unit-1311"])
            self.assertEqual([item["printedEntryNumber"] for item in index["items"]], [1311, 1311])
            self.assertEqual(activation["corpusId"], "al-isabah-public-openiti-5835c18-book-aaaaaaaaaaaa")
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["volumes"][0]["itemCount"], 2)
            self.assertEqual(summary["volumes"][0]["passageCount"], 0)

    def test_rejects_a_tampered_distribution_before_writing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            distribution = self.distribution(root)
            shard = distribution / "records" / "volume-01.jsonl"
            shard.write_text(shard.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
            output = root / "output"
            with self.assertRaisesRegex(MODULE.IngestionError, "checksum"):
                MODULE.ingest(distribution, self.base_corpus(root), output, "2026-08-14T18:00:00Z")
            self.assertFalse(output.exists())

    def test_archive_extraction_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "distribution.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("manifest.json", "{}")
                bundle.writestr("../outside.json", "{}")
            output = root / "output"
            with self.assertRaisesRegex(ValueError, "unsafe member"):
                extract(archive, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
