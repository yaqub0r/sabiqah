#!/usr/bin/env python3
"""Build a byte-stable tar snapshot directly from a Git commit tree."""

from __future__ import annotations

import argparse
import io
import subprocess
import tarfile
from pathlib import Path, PurePosixPath


def git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def tree_entries(repository: Path, commit: str) -> list[tuple[bytes, str, str]]:
    output = git(repository, "ls-tree", "-rz", "--full-tree", commit)
    entries: list[tuple[bytes, str, str]] = []
    for record in output.split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, object_type, object_id = metadata.decode("ascii").split(" ")
        if object_type != "blob":
            raise ValueError(
                f"unsupported Git tree entry {path!r}: expected blob, received {object_type}"
            )
        entries.append((path, mode, object_id))
    return sorted(entries, key=lambda entry: entry[0])


def tar_info(name: str, mode: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    return info


def build(repository: Path, commit: str, output: Path) -> None:
    entries = tree_entries(repository, commit)
    directories = {
        str(parent)
        for path, _, _ in entries
        for parent in PurePosixPath(path.decode("utf-8", "surrogateescape")).parents
        if str(parent) != "."
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w", format=tarfile.PAX_FORMAT) as archive:
        for directory in sorted(directories, key=lambda item: (item.count("/"), item)):
            info = tar_info(f"{directory}/", 0o755)
            info.type = tarfile.DIRTYPE
            archive.addfile(info)

        for raw_path, git_mode, object_id in entries:
            path = raw_path.decode("utf-8", "surrogateescape")
            content = git(repository, "cat-file", "blob", object_id)
            if git_mode == "120000":
                info = tar_info(path, 0o777)
                info.type = tarfile.SYMTYPE
                info.linkname = content.decode("utf-8", "surrogateescape")
                archive.addfile(info)
                continue
            if git_mode not in {"100644", "100755"}:
                raise ValueError(f"unsupported Git mode for {path!r}: {git_mode}")
            info = tar_info(path, 0o755 if git_mode == "100755" else 0o644)
            info.type = tarfile.REGTYPE
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.repository, args.commit, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
