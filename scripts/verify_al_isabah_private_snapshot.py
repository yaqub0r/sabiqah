#!/usr/bin/env python3
"""Verify the pinned private al-Isabah snapshot and review-corpus export."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_equal(label: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}, received {actual!r}")


def verify(manifest_path: Path, corpus: Path, archive: Path | None = None) -> None:
    policy = load(manifest_path)
    require_equal("classification", policy["classification"], "private-reference")
    require_equal("promotion status", policy["promotionStatus"], "blocked")

    corpus_policy = policy["reviewCorpus"]
    corpus_manifest_path = corpus / "manifest.json"
    corpus_summary_path = corpus / "summary.json"
    corpus_index_path = corpus / "index.json"
    for path in (corpus_manifest_path, corpus_summary_path, corpus_index_path):
        if not path.is_file():
            raise ValueError(f"required corpus file is missing: {path}")

    corpus_manifest = load(corpus_manifest_path)
    corpus_summary = load(corpus_summary_path)
    corpus_index = load(corpus_index_path)
    files = sorted(path for path in corpus.rglob("*") if path.is_file())

    require_equal("corpus id", corpus_manifest["corpusId"], corpus_policy["corpusId"])
    require_equal(
        "summary corpus id", corpus_summary["corpus"]["id"], corpus_policy["corpusId"]
    )
    require_equal(
        "source commit", corpus_manifest["sourceCommit"], policy["source"]["commit"]
    )
    require_equal(
        "summary source commit",
        corpus_summary["corpus"]["sourceCommit"],
        policy["source"]["commit"],
    )
    require_equal(
        "corpus manifest digest",
        sha256(corpus_manifest_path),
        corpus_policy["manifestSha256"],
    )
    require_equal("manifest object count", corpus_manifest["objectCount"], corpus_policy["manifestObjects"])
    require_equal("corpus file count", len(files), corpus_policy["files"])
    require_equal("corpus byte count", sum(path.stat().st_size for path in files), corpus_policy["bytes"])
    require_equal("corpus counts", corpus_summary["counts"], corpus_policy["counts"])
    require_equal(
        "index item count",
        len(corpus_index["items"]),
        corpus_policy["counts"]["translated"],
    )

    if archive is not None:
        if not archive.is_file():
            raise ValueError(f"research archive is missing: {archive}")
        require_equal("archive digest", sha256(archive), policy["archive"]["sha256"])
        require_equal("archive byte count", archive.stat().st_size, policy["archive"]["bytes"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    verify(args.manifest, args.corpus, args.archive)
    print("Private al-Isabah snapshot and review corpus match the pinned manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
