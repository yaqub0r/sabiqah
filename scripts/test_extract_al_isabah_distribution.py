import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_al_isabah_distribution import extract, is_safe_member  # noqa: E402


class AlIsabahDistributionExtractionTests(unittest.TestCase):
    def write_archive(self, root: Path, members: list[tuple[str, bytes]]) -> Path:
        archive = root / "distribution.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            for name, content in members:
                bundle.writestr(name, content)
        return archive

    def test_extracts_exact_schema_v2_inventory_shapes(self):
        members = [
            ("manifest.json", b"manifest\n"),
            ("release-closure.json", b"closure\n"),
            ("records/volume-01.jsonl", b"record\n"),
            ("reviews/issue-0026.json", b"review one\n"),
            ("reviews/issue-0070.json", b"review two\n"),
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "output"
            extract(self.write_archive(root, members), output)

            self.assertEqual(
                sorted(
                    path.relative_to(output).as_posix()
                    for path in output.rglob("*")
                    if path.is_file()
                ),
                sorted(name for name, _ in members),
            )
            for name, content in members:
                self.assertEqual((output / name).read_bytes(), content)

    def test_rejects_unsafe_or_unregistered_member_shapes(self):
        invalid_names = [
            "../release-closure.json",
            "/release-closure.json",
            "release-closure.json.bak",
            "reviews/issue-1.json",
            "reviews/issue-00001.json",
            "reviews/issue-0001.json/extra",
            "reviews\\issue-0001.json",
            "records/volume-1.jsonl",
            "unexpected.json",
        ]
        for name in invalid_names:
            with self.subTest(name=name):
                self.assertFalse(is_safe_member(name))
            if "\\" in name:
                continue
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                archive = self.write_archive(
                    root,
                    [("manifest.json", b"{}\n"), (name, b"unsafe\n")],
                )
                with self.assertRaisesRegex(ValueError, "unsafe member"):
                    extract(archive, root / "output")

    def test_rejects_duplicate_members_and_missing_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                duplicate = self.write_archive(
                    root,
                    [("manifest.json", b"one\n"), ("manifest.json", b"two\n")],
                )
            with self.assertRaisesRegex(ValueError, "duplicated or lacks manifest"):
                extract(duplicate, root / "duplicate-output")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            missing = self.write_archive(
                root,
                [("release-closure.json", b"closure\n")],
            )
            with self.assertRaisesRegex(ValueError, "duplicated or lacks manifest"):
                extract(missing, root / "missing-output")


if __name__ == "__main__":
    unittest.main()
