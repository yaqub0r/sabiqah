#!/usr/bin/env python3
"""Offline, fail-closed verification for Al-Isabah public distributions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


REPOSITORY = "https://github.com/yaqub0r/al-isabah"
REPOSITORY_API = "https://api.github.com/repos/yaqub0r/al-isabah"
WORK_ID = "ibn-hajar-al-isabah"
PRODUCER_SOURCE_ID = "openiti-jk000533-5835c183"
MATRIX_SOURCE_ID = "openiti-cleaned-arabic-comparison"
PRODUCER_SOURCE_ATTRIBUTION = (
    "OpenITI, JK000533 transcription of Ibn Hajar al-Asqalani's "
    "al-Isabah fi Tamyiz al-Sahabah"
)
CONTENT_LICENSE = {
    "spdx": "CC-BY-NC-SA-4.0",
    "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
}
SHA256 = re.compile(r"^[a-f0-9]{64}$")
COMMIT = re.compile(r"^[a-f0-9]{40}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,199}$")
UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
TAG = re.compile(r"^public-working-([a-f0-9]{40})$")
MANIFEST_KEYS = {
    "schemaVersion", "distributionId", "publicationStatus", "canonicalPromotion",
    "work", "repository", "generatedAt", "rights", "packets", "authorities",
    "counts", "duplicatePrintedEntryNumbers", "files",
}
RECORD_KEYS = {
    "schemaVersion", "id", "kind", "workId", "packetId", "sourceOrdinal",
    "printedEntryNumber", "canonicalEntryId", "volume", "pages", "title",
    "arabic", "english", "precedingMaterial", "names", "unresolved", "formulas",
    "machineAssessment", "humanReview", "source", "policy",
}
SOURCE_KEYS = {"authorityId", "commit", "artifactSha256", "exactTextSha256", "license"}
PRIVATE_FIELDS = {
    "api", "api_url", "bucket", "credential", "endpoint", "local_path", "object_key",
    "private_path", "private_url", "schema_path", "source_path", "storage_location", "token",
    "prompt", "critique", "model_trace", "witness_result", "raw_packet",
}
PRIVATE_MARKERS = (
    "firstlight", "elixir", "usul.ai", "lastpass", "r2.cloudflarestorage.com",
    "aws_access_key_id", "aws_secret_access_key", "/api/",
)


class CompatibilityError(RuntimeError):
    """Raised without echoing distribution content or secret-like values."""


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CompatibilityError("required verification input is unreadable") from error
    if not isinstance(value, dict):
        raise CompatibilityError("required verification input is not an object")
    return value


def digest_file(path: Path) -> str:
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
    except OSError as error:
        raise CompatibilityError("required verification input is unreadable") from error
    return hasher.hexdigest()


def exact_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise CompatibilityError(f"{label} fields do not match the public contract")


def public_boundary(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.casefold() in PRIVATE_FIELDS:
                raise CompatibilityError("distribution contains a prohibited internal field")
            public_boundary(child)
    elif isinstance(value, list):
        for child in value:
            public_boundary(child)
    elif isinstance(value, str):
        folded = value.casefold()
        if any(marker in folded for marker in PRIVATE_MARKERS):
            raise CompatibilityError("distribution contains prohibited private material")


def verify_release(
    manifest: dict[str, Any], archive: Path, release: dict[str, Any], tag_ref: dict[str, Any]
) -> dict[str, Any]:
    match = TAG.fullmatch(str(release.get("tag_name", "")))
    if not match:
        raise CompatibilityError("release tag does not follow the immutable contract")
    commit = match.group(1)
    if release.get("draft") is not False or release.get("prerelease") is not True:
        raise CompatibilityError("release is not an immutable public-working prerelease")
    if release.get("target_commitish") != commit:
        raise CompatibilityError("release target does not match its immutable tag")
    ref = tag_ref.get("object", {})
    if ref.get("type") != "commit" or ref.get("sha") != commit:
        raise CompatibilityError("release tag does not resolve to its named commit")
    if manifest.get("repository") != {"url": REPOSITORY, "commit": commit}:
        raise CompatibilityError("manifest producer binding does not match the release")
    if manifest.get("distributionId") != f"al-isabah-public-working-{commit[:12]}":
        raise CompatibilityError("distribution identity does not match the release commit")
    assets = release.get("assets")
    expected_name = f"al-isabah-public-distribution-{commit}.zip"
    if not isinstance(assets, list) or len(assets) != 1:
        raise CompatibilityError("release must contain exactly one distribution asset")
    asset = assets[0]
    if asset.get("name") != expected_name or archive.name != expected_name:
        raise CompatibilityError("distribution asset identity does not match the release")
    try:
        archive_size = archive.stat().st_size
    except OSError as error:
        raise CompatibilityError("distribution archive is unreadable") from error
    if asset.get("size") != archive_size:
        raise CompatibilityError("distribution asset byte count does not match the release")
    archive_sha = digest_file(archive)
    if asset.get("digest") != f"sha256:{archive_sha}":
        raise CompatibilityError("distribution asset digest does not match the release")
    return {"tag": release["tag_name"], "asset": expected_name, "sha256": archive_sha}


def verify_archive_matches_distribution(archive: Path, root: Path) -> None:
    try:
        with zipfile.ZipFile(archive) as bundle:
            members = {item.filename for item in bundle.infolist() if not item.is_dir()}
            expected = {"manifest.json"} | {
                path.relative_to(root).as_posix() for path in root.glob("records/*.jsonl")
            }
            if members != expected:
                raise CompatibilityError("archive inventory does not match the extracted distribution")
            for member in members:
                if bundle.read(member) != (root / member).read_bytes():
                    raise CompatibilityError("archive bytes do not match the extracted distribution")
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        raise CompatibilityError("distribution archive is unreadable") from error


def verify_rights(
    manifest: dict[str, Any], matrix: dict[str, Any], source_authority: dict[str, Any]
) -> dict[str, Any]:
    if matrix.get("schema") != "al-isabah.book-rights-matrix.v1":
        raise CompatibilityError("rights matrix version is unsupported")
    rights = manifest.get("rights", {})
    public_license = matrix.get("public_content_license", {})
    if (
        rights.get("matrixId") != matrix.get("matrix_id")
        or rights.get("license") != CONTENT_LICENSE
        or public_license.get("spdx") != CONTENT_LICENSE["spdx"]
        or public_license.get("url") != CONTENT_LICENSE["url"]
        or rights.get("softwareLicenseGranted") is not False
        or public_license.get("software_license_granted") is not False
        or rights.get("attribution") != matrix.get("attribution")
        or rights.get("excludedMaterial") != matrix.get("exclusions")
    ):
        raise CompatibilityError("manifest rights do not match the pinned rights matrix")
    decision = matrix.get("publication_decision", {})
    follow_up = matrix.get("follow_up_review", {})
    if (
        decision.get("public_reading") != "approved-noncommercial-with-attribution-and-share-alike"
        or decision.get("public_reuse") != "approved-under-cc-by-nc-sa-4.0"
        or decision.get("canonical_promotion") != "separately-gated"
        or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(matrix.get("reviewed_on", "")))
        or follow_up.get("status") != "required-on-change"
        or not follow_up.get("triggers")
    ):
        raise CompatibilityError("rights decision or review policy is incomplete")
    machine = source_authority.get("machineText", {})
    source_rows = [
        row for row in matrix.get("source_editions", [])
        if row.get("publication_role") == "arabic-publication-base"
    ]
    authorities = manifest.get("authorities", [])
    if len(source_rows) != 1 or len(authorities) != 1:
        raise CompatibilityError("distribution source authority is ambiguous")
    row, authority = source_rows[0], authorities[0]
    expected_source = {
        "sourceId": PRODUCER_SOURCE_ID,
        "commit": machine.get("commit"),
        "sha256": machine.get("sha256"),
        "license": {
            "spdx": machine.get("license", {}).get("spdx"),
            "url": machine.get("license", {}).get("url"),
            "attribution": PRODUCER_SOURCE_ATTRIBUTION,
        },
    }
    matrix_attribution = matrix.get("attribution")
    if (
        source_authority.get("authorityId") != "al-isabah-openiti-5835c18-aco-v1"
        or source_authority.get("assessment", {}).get("status") != "approved-for-publication"
        or row.get("source_id") != MATRIX_SOURCE_ID
        or row.get("source_revision") != machine.get("commit")
        or row.get("sha256") != machine.get("sha256")
        or authority != expected_source
        or not isinstance(matrix_attribution, list)
        or len(matrix_attribution) < 2
        or matrix_attribution[-1]
        != f"{PRODUCER_SOURCE_ATTRIBUTION}, commit {machine.get('commit')}"
    ):
        raise CompatibilityError("source authority does not match the approved pinned source")
    return {
        "sourceAuthorityId": source_authority["authorityId"],
        "producerAuthorityId": authority["sourceId"],
        "sourceRepository": machine["repository"],
        "sourceCommit": machine["commit"],
        "sourcePath": machine["path"],
        "sourceArtifactSha256": machine["sha256"],
        "sourceLicense": CONTENT_LICENSE,
        "sourceAttribution": authority["license"]["attribution"],
        "englishLicense": CONTENT_LICENSE,
        "englishAttribution": matrix_attribution[0],
        "rightsMatrix": {
            "id": matrix["matrix_id"],
            "schema": matrix["schema"],
            "decision": decision["public_reuse"],
            "reviewedOn": matrix["reviewed_on"],
            "followUp": follow_up["status"],
        },
        "excludedMaterial": matrix["exclusions"],
    }


def verify_records(root: Path, manifest: dict[str, Any], binding: dict[str, Any]) -> list[dict[str, Any]]:
    authorities = {item["sourceId"]: item for item in manifest["authorities"]}
    packet_counts = {item.get("packetId"): item.get("entryCount") for item in manifest.get("packets", [])}
    if not packet_counts or any(not SHA256.fullmatch(str(item.get("sha256", ""))) for item in manifest.get("packets", [])):
        raise CompatibilityError("packet inventory is invalid")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    actual_paths: set[str] = set()
    packet_actual: dict[str, int] = defaultdict(int)
    needs_attention = 0
    human_reviewed = 0
    for file in manifest.get("files", []):
        relative = file.get("path")
        if not isinstance(relative, str) or not re.fullmatch(r"records/volume-\d{2}\.jsonl", relative):
            raise CompatibilityError("distribution contains an unsafe shard path")
        actual_paths.add(relative)
        path = root / relative
        if not path.is_file() or digest_file(path) != file.get("sha256"):
            raise CompatibilityError("distribution shard checksum differs")
        if path.stat().st_size != file.get("bytes"):
            raise CompatibilityError("distribution shard byte count differs")
        try:
            shard = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        except (UnicodeError, json.JSONDecodeError) as error:
            raise CompatibilityError("distribution shard is unreadable") from error
        if len(shard) != file.get("recordCount"):
            raise CompatibilityError("distribution shard record count differs")
        previous: tuple[int, str] | None = None
        for record in shard:
            exact_keys(record, RECORD_KEYS, "record")
            exact_keys(record.get("source"), SOURCE_KEYS, "record source")
            exact_keys(record.get("policy"), {"bindingSha256"}, "record policy")
            public_boundary(record)
            record_id = record.get("id")
            if not isinstance(record_id, str) or not IDENTIFIER.fullmatch(record_id) or record_id in seen:
                raise CompatibilityError("distribution contains an invalid or duplicate stable record ID")
            seen.add(record_id)
            order = (int(record.get("sourceOrdinal", 0)), record_id)
            if previous is not None and order <= previous:
                raise CompatibilityError("distribution shard is not in stable source order")
            previous = order
            if (
                record.get("schemaVersion") != "2.0.0"
                or record.get("kind") != "entry"
                or record.get("workId") != WORK_ID
                or record.get("source", {}).get("authorityId") != binding["producerAuthorityId"]
                or record.get("source", {}).get("commit") != binding["sourceCommit"]
                or record.get("source", {}).get("artifactSha256") != binding["sourceArtifactSha256"]
                or record.get("source", {}).get("license") != authorities[binding["producerAuthorityId"]]["license"]
                or not SHA256.fullmatch(str(record.get("source", {}).get("exactTextSha256", "")))
                or not SHA256.fullmatch(str(record.get("policy", {}).get("bindingSha256", "")))
                or not str(record.get("arabic", "")).strip()
                or not str(record.get("english", "")).strip()
            ):
                raise CompatibilityError("record does not match the verified public contract")
            packet_id = record.get("packetId")
            if packet_id not in packet_counts:
                raise CompatibilityError("record refers to an undeclared packet")
            packet_actual[packet_id] += 1
            needs_attention += record.get("machineAssessment") == "needs_attention"
            human_reviewed += record.get("humanReview") in {"reviewed", "verified"}
            records.append(record)
    disk_paths = {path.relative_to(root).as_posix() for path in root.glob("records/*.jsonl")}
    if disk_paths != actual_paths or packet_actual != packet_counts:
        raise CompatibilityError("distribution file or packet inventory differs")
    counts = manifest.get("counts", {})
    if (
        counts.get("entries") != len(records)
        or counts.get("machinePassed") != len(records) - needs_attention
        or counts.get("needsAttention") != needs_attention
        or counts.get("humanReviewed") != human_reviewed
    ):
        raise CompatibilityError("distribution aggregate counts differ")
    duplicates: dict[int, list[str]] = defaultdict(list)
    for record in records:
        duplicates[int(record["printedEntryNumber"])].append(record["id"])
    expected_duplicates = [
        {"printedEntryNumber": number, "recordIds": ids}
        for number, ids in sorted(duplicates.items()) if len(ids) > 1
    ]
    if expected_duplicates != manifest.get("duplicatePrintedEntryNumbers"):
        raise CompatibilityError("duplicate printed-entry accounting differs")
    return records


def verify_distribution(
    root: Path,
    archive: Path,
    release_path: Path,
    tag_ref_path: Path,
    rights_matrix_path: Path,
    source_authority_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    manifest = load(root / "manifest.json")
    version = str(manifest.get("schemaVersion", ""))
    if version == "1.0.0":
        raise CompatibilityError("Al-Isabah schema v1 is rollback-only; restore a previously verified corpus pointer")
    if version != "2.0.0":
        raise CompatibilityError("unsupported Al-Isabah distribution major version")
    exact_keys(manifest, MANIFEST_KEYS, "manifest")
    if manifest.get("publicationStatus") != "public-working" or manifest.get("canonicalPromotion") != "blocked":
        raise CompatibilityError("distribution public-working or promotion status is unsafe")
    exact_keys(manifest.get("work"), {"id", "titleArabic", "titleEnglish"}, "work")
    exact_keys(manifest.get("repository"), {"url", "commit"}, "repository")
    exact_keys(
        manifest.get("rights"),
        {"matrixId", "license", "softwareLicenseGranted", "attribution", "excludedMaterial"},
        "rights",
    )
    exact_keys(manifest.get("counts"), {"entries", "machinePassed", "needsAttention", "humanReviewed"}, "counts")
    for packet in manifest.get("packets", []):
        exact_keys(packet, {"packetId", "sha256", "entryCount"}, "packet")
    for authority in manifest.get("authorities", []):
        exact_keys(authority, {"sourceId", "commit", "sha256", "license"}, "authority")
        exact_keys(authority.get("license"), {"spdx", "url", "attribution"}, "authority license")
    for file in manifest.get("files", []):
        exact_keys(file, {"path", "sha256", "bytes", "recordCount", "volume"}, "file")
    if manifest["work"].get("id") != WORK_ID:
        raise CompatibilityError("distribution work identity is not Al-Isabah")
    generated_at = manifest.get("generatedAt")
    if not isinstance(generated_at, str) or not UTC_TIMESTAMP.fullmatch(generated_at):
        raise CompatibilityError("distribution timestamp must use UTC Z form")
    try:
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise CompatibilityError("distribution timestamp is invalid") from error
    public_boundary(manifest)
    release_binding = verify_release(manifest, archive, load(release_path), load(tag_ref_path))
    verify_archive_matches_distribution(archive, root)
    rights_binding = verify_rights(manifest, load(rights_matrix_path), load(source_authority_path))
    records = verify_records(root, manifest, rights_binding)
    return manifest, records, {**release_binding, **rights_binding}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify an extracted Al-Isabah distribution offline.")
    parser.add_argument("--distribution", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--release-metadata", required=True, type=Path)
    parser.add_argument("--tag-ref", required=True, type=Path)
    parser.add_argument("--rights-matrix", required=True, type=Path)
    parser.add_argument("--source-authority", required=True, type=Path)
    args = parser.parse_args()
    verify_distribution(
        args.distribution.resolve(), args.archive.resolve(), args.release_metadata.resolve(),
        args.tag_ref.resolve(), args.rights_matrix.resolve(), args.source_authority.resolve(),
    )
    print("Al-Isabah schema v2 distribution is compatible.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
