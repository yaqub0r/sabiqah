#!/usr/bin/env python3
"""Resolve and validate the active Al-Isabah reader-corpus pointer."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


CORPUS_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,199}")


def resolve_pointer(value: Any) -> str:
    if not isinstance(value, dict) or value.get("schemaVersion") != "1.0.0":
        raise ValueError("active corpus pointer has an unsupported schema")
    corpus_id = value.get("corpusId")
    if not isinstance(corpus_id, str) or not CORPUS_ID.fullmatch(corpus_id):
        raise ValueError("active corpus pointer has an invalid corpus ID")
    expected = f"public-corpora/al-isabah/{corpus_id}"
    if value.get("prefix") != expected:
        raise ValueError("active corpus pointer has an inconsistent prefix")
    return expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pointer", type=Path)
    args = parser.parse_args()
    value = json.loads(args.pointer.read_text(encoding="utf-8"))
    print(resolve_pointer(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
