#!/usr/bin/env python3
"""Safely extract the narrowly-scoped Al-Isabah distribution archive."""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path, PurePosixPath


ALLOWED = re.compile(r"(?:manifest\.json|records/volume-\d{2}\.jsonl)")


def extract(archive: Path, output: Path) -> None:
    if output.exists():
        raise ValueError(f"output already exists: {output}")
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or "manifest.json" not in names:
            raise ValueError("archive inventory is duplicated or lacks manifest.json")
        for name in names:
            relative = PurePosixPath(name)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or "\\" in name
                or not ALLOWED.fullmatch(name)
            ):
                raise ValueError(f"archive contains an unsafe member: {name}")
        output.mkdir(parents=True)
        for name in sorted(names):
            target = output.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.read(name))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    extract(args.archive.resolve(), args.output.resolve())
    print("Al-Isabah distribution archive extracted safely.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
