#!/usr/bin/env python3
"""Validate, package, upload, and round-trip verify private research evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence


BUCKET = "sabiqah-assets-dev"
PROFILE = "sabiqah-r2-dev"
PREFIX = "research-evidence"
ALLOWED_CLASSIFICATIONS = {
    "private-reference",
    "permission-required",
    "unresolved",
}
EVIDENCE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[a-z0-9-]*[a-z0-9])?$")
COLLECTION_PATTERN = EVIDENCE_ID_PATTERN
ACCOUNT_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


class EvidenceError(RuntimeError):
    """Raised when evidence is unsafe, ambiguous, or cannot be verified."""


@dataclass(frozen=True)
class EvidenceBundle:
    source: Path
    evidence_id: str
    classification: str
    files: tuple[Path, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_mapping(document: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = document.get(key)
    if not isinstance(value, Mapping) or not value:
        raise EvidenceError(f"manifest field '{key}' must be a non-empty object")
    return value


def _safe_relative_path(name: Any) -> PurePosixPath:
    if not isinstance(name, str) or not name or "\\" in name:
        raise EvidenceError("each manifest file name must be a POSIX relative path")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise EvidenceError(f"unsafe manifest file path: {name!r}")
    if name == "manifest.json":
        raise EvidenceError("manifest.json is packaged automatically and must not list itself")
    return path


def validate_bundle(source: Path) -> EvidenceBundle:
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise EvidenceError("source must be an evidence directory")

    manifest_path = source / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise EvidenceError("source must contain a regular manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvidenceError(f"manifest.json is not valid UTF-8 JSON: {error}") from error
    if not isinstance(manifest, Mapping):
        raise EvidenceError("manifest root must be an object")
    if manifest.get("schemaVersion") != 1:
        raise EvidenceError("manifest schemaVersion must be 1")

    evidence_id = manifest.get("evidenceId")
    if not isinstance(evidence_id, str) or not EVIDENCE_ID_PATTERN.fullmatch(evidence_id):
        raise EvidenceError("manifest evidenceId must be a safe lowercase identifier")
    classification = manifest.get("classification")
    if classification not in ALLOWED_CLASSIFICATIONS:
        raise EvidenceError("manifest classification is not eligible for private ingestion")
    if manifest.get("publicationEligibility") != "blocked":
        raise EvidenceError("publicationEligibility must be 'blocked'")
    acquired_at = manifest.get("acquiredAt")
    if not isinstance(acquired_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", acquired_at):
        raise EvidenceError("manifest acquiredAt must use YYYY-MM-DD")
    purpose = manifest.get("purpose")
    if not isinstance(purpose, str) or not purpose.strip():
        raise EvidenceError("manifest purpose must be non-empty")
    _required_mapping(manifest, "provenance")
    _required_mapping(manifest, "rights")

    declared = manifest.get("files")
    if not isinstance(declared, list) or not declared:
        raise EvidenceError("manifest files must be a non-empty array")

    declared_names: set[str] = set()
    verified_files: list[Path] = []
    for entry in declared:
        if not isinstance(entry, Mapping):
            raise EvidenceError("each manifest file entry must be an object")
        relative = _safe_relative_path(entry.get("name"))
        relative_name = relative.as_posix()
        if relative_name in declared_names:
            raise EvidenceError(f"duplicate manifest file: {relative_name}")
        declared_names.add(relative_name)
        path = source.joinpath(*relative.parts)
        if path.is_symlink() or not path.is_file():
            raise EvidenceError(f"declared file is missing or is a link: {relative_name}")
        if not path.resolve().is_relative_to(source):
            raise EvidenceError(f"declared file escapes the source directory: {relative_name}")
        expected_bytes = entry.get("bytes")
        expected_sha256 = entry.get("sha256")
        if not isinstance(expected_bytes, int) or expected_bytes < 0:
            raise EvidenceError(f"invalid byte count for {relative_name}")
        if not isinstance(expected_sha256, str) or not re.fullmatch(
            r"[a-f0-9]{64}", expected_sha256
        ):
            raise EvidenceError(f"invalid SHA-256 for {relative_name}")
        if path.stat().st_size != expected_bytes:
            raise EvidenceError(f"byte-count mismatch for {relative_name}")
        if sha256_file(path) != expected_sha256:
            raise EvidenceError(f"SHA-256 mismatch for {relative_name}")
        verified_files.append(path)

    actual_names: set[str] = set()
    for path in source.rglob("*"):
        if path.is_symlink():
            raise EvidenceError(f"links are not allowed in evidence: {path.relative_to(source)}")
        if path.is_file() and path != manifest_path:
            actual_names.add(path.relative_to(source).as_posix())
    if actual_names != declared_names:
        unlisted = sorted(actual_names - declared_names)
        missing = sorted(declared_names - actual_names)
        raise EvidenceError(f"manifest inventory mismatch; unlisted={unlisted}, missing={missing}")

    return EvidenceBundle(source, evidence_id, classification, tuple(verified_files))


def build_deterministic_archive(bundle: EvidenceBundle, destination: Path) -> tuple[str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    members = [bundle.source / "manifest.json", *bundle.files]
    members.sort(key=lambda path: path.relative_to(bundle.source).as_posix())
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in members:
            name = path.relative_to(bundle.source).as_posix()
            info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
            info.create_system = 3
            info.external_attr = 0o100600 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    return sha256_file(destination), destination.stat().st_size


class R2Client:
    def __init__(
        self,
        account_id: str,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        if not ACCOUNT_ID_PATTERN.fullmatch(account_id):
            raise EvidenceError("Cloudflare account ID must be 32 lowercase hexadecimal characters")
        self.endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        self.runner = runner

    def _run(self, arguments: Sequence[str], *, allow_missing: bool = False) -> str | None:
        environment = os.environ.copy()
        for name in (
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "AWS_PROFILE",
            "AWS_DEFAULT_PROFILE",
        ):
            environment.pop(name, None)
        command = [
            "aws",
            *arguments,
            "--endpoint-url",
            self.endpoint,
            "--profile",
            PROFILE,
            "--region",
            "auto",
            "--no-cli-pager",
        ]
        try:
            result = self.runner(
                command,
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
        except FileNotFoundError as error:
            raise EvidenceError("AWS CLI is required but was not found") from error
        if result.returncode == 0:
            return result.stdout
        diagnostic = f"{result.stdout}\n{result.stderr}"
        if allow_missing and any(
            marker in diagnostic for marker in ("(404)", "Not Found", "NoSuchKey")
        ):
            return None
        concise = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "unknown error"
        raise EvidenceError(f"R2 operation failed: {concise}")

    def head(self, key: str) -> Mapping[str, Any] | None:
        output = self._run(
            ["s3api", "head-object", "--bucket", BUCKET, "--key", key],
            allow_missing=True,
        )
        if output is None:
            return None
        try:
            document = json.loads(output)
        except json.JSONDecodeError as error:
            raise EvidenceError("R2 head-object returned invalid JSON") from error
        if not isinstance(document, Mapping):
            raise EvidenceError("R2 head-object returned an invalid response")
        return document

    def put(self, key: str, archive: Path, archive_sha256: str) -> None:
        self._run(
            [
                "s3api",
                "put-object",
                "--bucket",
                BUCKET,
                "--key",
                key,
                "--body",
                str(archive),
                "--content-type",
                "application/zip",
                "--metadata",
                f"sha256={archive_sha256}",
            ]
        )

    def get(self, key: str, destination: Path) -> None:
        self._run(
            ["s3api", "get-object", "--bucket", BUCKET, "--key", key, str(destination)]
        )


def preserve(
    source: Path,
    collection: str,
    *,
    dry_run: bool,
    account_id: str | None = None,
    client: R2Client | None = None,
    runtime_directory: Path = Path(".runtime/private-evidence"),
) -> Mapping[str, Any]:
    if not COLLECTION_PATTERN.fullmatch(collection):
        raise EvidenceError("collection must be a safe lowercase identifier")
    bundle = validate_bundle(source)
    archive = runtime_directory / f"{bundle.evidence_id}.zip"
    archive_sha256, archive_bytes = build_deterministic_archive(bundle, archive)
    key = f"{PREFIX}/{collection}/{bundle.evidence_id}/{bundle.evidence_id}.zip"
    result: dict[str, Any] = {
        "status": "validated",
        "evidenceId": bundle.evidence_id,
        "classification": bundle.classification,
        "fileCount": len(bundle.files),
        "archiveBytes": archive_bytes,
        "archiveSha256": archive_sha256,
    }
    if dry_run:
        return result
    if client is None:
        if account_id is None:
            raise EvidenceError("--account-id is required unless --dry-run is used")
        client = R2Client(account_id)

    existing = client.head(key)
    if existing is not None:
        metadata = existing.get("Metadata", {})
        remote_sha256 = metadata.get("sha256") if isinstance(metadata, Mapping) else None
        remote_bytes = existing.get("ContentLength")
        if remote_sha256 != archive_sha256 or remote_bytes != archive_bytes:
            raise EvidenceError("destination exists with different content; refusing to overwrite")
        result["status"] = "verified-existing"
    else:
        client.put(key, archive, archive_sha256)
        result["status"] = "uploaded"

    runtime_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f"{bundle.evidence_id}-", suffix=".download", dir=runtime_directory, delete=False
    ) as temporary:
        download = Path(temporary.name)
    try:
        client.get(key, download)
        if download.stat().st_size != archive_bytes or sha256_file(download) != archive_sha256:
            raise EvidenceError("R2 round-trip verification failed")
    finally:
        download.unlink(missing_ok=True)

    receipt = {
        **result,
        "bucket": BUCKET,
        "objectKey": key,
        "verification": "round-trip-sha256",
    }
    receipt_path = runtime_directory / f"{bundle.evidence_id}.receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--account-id")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        result = preserve(
            arguments.source,
            arguments.collection,
            dry_run=arguments.dry_run,
            account_id=arguments.account_id,
        )
    except (EvidenceError, OSError) as error:
        print(f"private evidence ingestion failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
