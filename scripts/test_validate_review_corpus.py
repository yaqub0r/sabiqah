import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_corpus", ROOT / "scripts" / "validate_review_corpus.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ValidateCorpusTests(unittest.TestCase):
    def make_corpus(self, root: Path) -> None:
        item_id = "isabah-entry-00010759"
        detail = {
            "id": item_id,
            "corpusId": "al-isabah-reading-a3b76bf-v3",
            "unresolved": [],
        }
        index = {
            "corpusId": "al-isabah-reading-a3b76bf-v3",
            "items": [
                {
                    "id": item_id,
                    "unresolvedCount": 0,
                    "machineAssessment": "passed",
                    "volume": 8,
                    "sectionId": "volume-08-pages-0001-0025",
                }
            ],
        }
        summary = {
            "corpus": {
                "id": "al-isabah-reading-a3b76bf-v3",
                "promotionStatus": "blocked",
            },
            "counts": {
                "entries": 1,
                "passages": 0,
                "unresolvedItems": 0,
                "needsAttention": 0,
            },
            "volumes": [
                {
                    "number": 8,
                    "sectionCount": 1,
                    "itemCount": 1,
                }
            ],
        }
        section = {
            "id": "volume-08-pages-0001-0025",
            "corpusId": "al-isabah-reading-a3b76bf-v3",
            "items": [detail],
        }
        paths = {
            "summary.json": summary,
            "index.json": index,
            f"items/{item_id}.json": detail,
            "sections/volume-08-pages-0001-0025.json": section,
        }
        records = []
        for relative, value in paths.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value), encoding="utf-8")
            records.append(
                {
                    "path": relative,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "bytes": path.stat().st_size,
                }
            )
        (root / "manifest.json").write_text(
            json.dumps(
                {
                    "corpusId": "al-isabah-reading-a3b76bf-v3",
                    "objectCount": len(records),
                    "files": records,
                }
            ),
            encoding="utf-8",
        )

    def test_valid_corpus_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_corpus(root)
            self.assertEqual(MODULE.validate(root), [])

    def test_tampered_detail_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_corpus(root)
            detail = next((root / "items").glob("*.json"))
            detail.write_text('{"tampered":true}', encoding="utf-8")
            errors = MODULE.validate(root)
            self.assertTrue(any("hash mismatch" in error for error in errors))

    def test_eligible_summary_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_corpus(root)
            summary = json.loads((root / "summary.json").read_text())
            summary["corpus"]["promotionStatus"] = "eligible"
            (root / "summary.json").write_text(json.dumps(summary))
            errors = MODULE.validate(root)
            self.assertIn("summary: promotion status must remain blocked", errors)


if __name__ == "__main__":
    unittest.main()
