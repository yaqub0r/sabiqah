import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_snapshot", ROOT / "scripts" / "verify_al_isabah_private_snapshot.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
verify = MODULE.verify


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8", newline="\n")


class PrivateSnapshotTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path, Path]:
        corpus = root / "corpus"
        source_commit = "a" * 40
        write_json(
            corpus / "summary.json",
            {
                "corpus": {"id": "corpus-v1", "sourceCommit": source_commit},
                "counts": {
                    "entries": 1,
                    "passages": 0,
                    "translated": 1,
                    "needsAttention": 0,
                    "unresolvedItems": 0,
                    "humanReviewed": 0,
                },
            },
        )
        write_json(corpus / "index.json", {"items": [{"id": "entry-1"}]})
        write_json(
            corpus / "manifest.json",
            {"corpusId": "corpus-v1", "sourceCommit": source_commit, "objectCount": 2},
        )
        archive = root / "snapshot.tar"
        archive.write_bytes(b"snapshot")
        files = list(corpus.rglob("*"))
        files = [path for path in files if path.is_file()]
        manifest = root / "policy.json"
        write_json(
            manifest,
            {
                "classification": "private-reference",
                "promotionStatus": "blocked",
                "source": {"commit": source_commit},
                "archive": {
                    "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                    "bytes": archive.stat().st_size,
                },
                "reviewCorpus": {
                    "corpusId": "corpus-v1",
                    "manifestSha256": hashlib.sha256((corpus / "manifest.json").read_bytes()).hexdigest(),
                    "manifestObjects": 2,
                    "files": len(files),
                    "bytes": sum(path.stat().st_size for path in files),
                    "counts": {
                        "entries": 1,
                        "passages": 0,
                        "translated": 1,
                        "needsAttention": 0,
                        "unresolvedItems": 0,
                        "humanReviewed": 0,
                    },
                },
            },
        )
        return manifest, corpus, archive

    def test_accepts_matching_private_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, corpus, archive = self.fixture(Path(directory))
            verify(manifest, corpus, archive)

    def test_rejects_changed_corpus_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, corpus, archive = self.fixture(Path(directory))
            (corpus / "index.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "corpus byte count"):
                verify(manifest, corpus, archive)


if __name__ == "__main__":
    unittest.main()
