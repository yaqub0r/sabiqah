import hashlib
import importlib.util
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "canonical_archive", ROOT / "scripts" / "build_canonical_git_archive.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
build = MODULE.build


def run(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


class CanonicalGitArchiveTests(unittest.TestCase):
    def test_repeated_builds_are_identical_and_preserve_tree_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "source"
            repository.mkdir()
            run(repository, "init", "--quiet")
            run(repository, "config", "user.name", "Archive Test")
            run(repository, "config", "user.email", "archive@example.invalid")
            run(repository, "config", "core.autocrlf", "false")
            (repository / "nested").mkdir()
            (repository / "nested" / "source.txt").write_bytes(b"line one\nline two\n")
            (repository / "run.sh").write_bytes(b"#!/bin/sh\nexit 0\n")
            run(repository, "add", ".")
            run(repository, "update-index", "--chmod=+x", "run.sh")
            run(repository, "commit", "--quiet", "-m", "fixture")
            commit = run(repository, "rev-parse", "HEAD")

            first = root / "first.tar"
            second = root / "second.tar"
            build(repository, commit, first)
            build(repository, commit, second)
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).digest(),
                hashlib.sha256(second.read_bytes()).digest(),
            )

            with tarfile.open(first, "r") as archive:
                self.assertEqual(
                    archive.extractfile("nested/source.txt").read(),
                    b"line one\nline two\n",
                )
                self.assertEqual(archive.getmember("run.sh").mode, 0o755)
                self.assertTrue(all(member.mtime == 0 for member in archive.getmembers()))


if __name__ == "__main__":
    unittest.main()
