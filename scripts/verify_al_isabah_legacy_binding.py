#!/usr/bin/env python3
"""Verify the one-time Al-Isabah schema-4 provenance binding without network I/O."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SHA256 = re.compile(r"^[a-f0-9]{64}$")
ITEM_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,199}$")
BINDING_SCHEMA = "sabiqah.al-isabah-legacy-provenance-binding.v1"
LEGACY_SCHEMA = "4.0.0"
TARGET_SCHEMA = "5.0.0"
ALLOWED_SELECTOR = "source.alignment.method"
SCOPE_KEYS = (
    "schema", "bindingId", "status", "base", "source", "cohorts", "evidence",
    "allowedMigration", "nonClaims", "retirement",
)


class LegacyBindingError(RuntimeError):
    """Raised when the one-time legacy binding is incomplete or mismatched."""


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LegacyBindingError("legacy binding evidence is missing or invalid") from error
    if not isinstance(value, dict):
        raise LegacyBindingError("legacy binding evidence must be an object")
    return value


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    try:
        return digest_bytes(path.read_bytes())
    except OSError as error:
        raise LegacyBindingError("legacy binding evidence is missing") from error


def compact_json(value: Any) -> bytes:
    return (json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ) + "\n").encode("utf-8")


def scope_digest(binding: dict[str, Any]) -> str:
    return digest_bytes(compact_json({key: binding[key] for key in SCOPE_KEYS}))


def membership(item_ids: Iterable[str]) -> dict[str, Any]:
    ordered = sorted(item_ids)
    encoded = (json.dumps(ordered, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    return {
        "itemCount": len(ordered),
        "itemIdsSha256": digest_bytes(encoded),
        "itemIds": ordered,
    }


def git_blob_sha1(value: bytes) -> str:
    header = f"blob {len(value)}\0".encode("ascii")
    return hashlib.sha1(header + value).hexdigest()


def require_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise LegacyBindingError(f"{label} is missing or contains unknown fields")
    return value


def value_at(record: dict[str, Any], dotted_path: str) -> Any:
    value: Any = record
    for key in dotted_path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def verify_file_evidence(
    evidence: dict[str, Any], path: Path, label: str,
) -> None:
    require_keys(evidence, {"repository", "commit", "path", "gitBlobSha1", "sha256"}, label)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise LegacyBindingError(f"{label} is missing") from error
    if (
        evidence["path"] != path.as_posix()
        and not path.as_posix().endswith(str(evidence["path"]))
    ):
        raise LegacyBindingError(f"{label} path differs")
    canonical = raw if git_blob_sha1(raw) == evidence["gitBlobSha1"] else raw.replace(b"\r\n", b"\n")
    if (
        digest_bytes(canonical) != evidence["sha256"]
        or git_blob_sha1(canonical) != evidence["gitBlobSha1"]
    ):
        raise LegacyBindingError(f"{label} digest differs")


def verify_release(
    expected: dict[str, Any], release: dict[str, Any], tag_ref: dict[str, Any], label: str,
) -> None:
    require_keys(
        expected,
        {"repository", "releaseId", "tag", "commit", "assetId", "assetName", "assetBytes", "assetSha256"},
        label,
    )
    assets = release.get("assets")
    matching = [
        asset for asset in assets if isinstance(asset, dict) and asset.get("name") == expected["assetName"]
    ] if isinstance(assets, list) else []
    if len(matching) != 1:
        raise LegacyBindingError(f"{label} asset is missing or ambiguous")
    asset = matching[0]
    repository_api = expected["repository"].replace("https://github.com/", "https://api.github.com/repos/")
    if (
        release.get("url") != f"{repository_api}/releases/{expected['releaseId']}"
        or tag_ref.get("url") != f"{repository_api}/git/refs/tags/{expected['tag']}"
        or release.get("id") != expected["releaseId"]
        or release.get("tag_name") != expected["tag"]
        or release.get("target_commitish") != expected["commit"]
        or release.get("draft") is not False
        or release.get("prerelease") is not True
        or asset.get("id") != expected["assetId"]
        or asset.get("size") != expected["assetBytes"]
        or asset.get("digest") != f"sha256:{expected['assetSha256']}"
        or tag_ref.get("ref") != f"refs/tags/{expected['tag']}"
        or tag_ref.get("object", {}).get("type") != "commit"
        or tag_ref.get("object", {}).get("sha") != expected["commit"]
    ):
        raise LegacyBindingError(f"{label} identity or digest differs")


def verify_base_inventory(
    expected: dict[str, Any], base: Path, pointer_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    require_keys(
        expected,
        {
            "pointer", "pointerSha256", "corpusSchemaVersion", "coreObjects",
            "manifestSha256", "objectCount", "objectInventorySha256", "membership",
            "sectionCount", "sectionObjectsSha256", "counts", "state",
        },
        "legacy base binding",
    )
    pointer = load(pointer_path)
    if pointer != expected["pointer"] or digest_file(pointer_path) != expected["pointerSha256"]:
        raise LegacyBindingError("active pointer differs from the approved legacy binding")
    summary = load(base / "summary.json")
    index = load(base / "index.json")
    manifest_path = base / "manifest.json"
    manifest = load(manifest_path)
    if set(expected["coreObjects"]) != {
        "summary.json", "index.json", "quarantine.json", "exclusions.json"
    }:
        raise LegacyBindingError("legacy core-object binding is incomplete or unknown")
    if (
        summary.get("schemaVersion") != expected["corpusSchemaVersion"]
        or summary.get("schemaVersion") != LEGACY_SCHEMA
        or index.get("schemaVersion") != LEGACY_SCHEMA
        or manifest.get("schemaVersion") != LEGACY_SCHEMA
        or summary.get("corpus", {}).get("id") != pointer.get("corpusId")
        or index.get("corpusId") != pointer.get("corpusId")
        or manifest.get("corpusId") != pointer.get("corpusId")
    ):
        raise LegacyBindingError("legacy pointer, corpus, or schema differs")
    if digest_file(manifest_path) != expected["manifestSha256"]:
        raise LegacyBindingError("legacy corpus manifest digest differs")
    distribution = manifest.get("distribution", {})
    if (
        distribution.get("id") != pointer.get("distributionId")
        or distribution.get("commit") != pointer.get("distributionCommit")
        or distribution.get("manifestSha256") != pointer.get("distributionManifestSha256")
    ):
        raise LegacyBindingError("legacy distribution claim differs from the active pointer")
    for relative, expected_hash in expected["coreObjects"].items():
        if digest_file(base / relative) != expected_hash:
            raise LegacyBindingError("legacy core-object digest differs")
    files = manifest.get("files")
    if not isinstance(files, list) or files != sorted(files, key=lambda value: value.get("path", "")):
        raise LegacyBindingError("legacy object inventory is absent or unordered")
    if manifest.get("objectCount") != len(files) or len(files) != expected["objectCount"]:
        raise LegacyBindingError("legacy object count differs")
    if digest_bytes(compact_json(files)) != expected["objectInventorySha256"]:
        raise LegacyBindingError("legacy object inventory digest differs")
    by_path: dict[str, dict[str, Any]] = {}
    for file in files:
        if not isinstance(file, dict) or set(file) != {"path", "sha256", "bytes"}:
            raise LegacyBindingError("legacy object inventory is malformed")
        relative = file.get("path")
        digest = file.get("sha256")
        parts = PurePosixPath(relative).parts if isinstance(relative, str) else ()
        if (
            not isinstance(relative, str)
            or relative.startswith(("/", ".."))
            or "\\" in relative
            or not relative.endswith(".json")
            or not parts
            or any(part in {"", ".", ".."} for part in parts)
            or relative in by_path
            or not isinstance(digest, str)
            or not SHA256.fullmatch(digest)
        ):
            raise LegacyBindingError("legacy object inventory is unsafe or duplicated")
        path = base / relative
        try:
            path.resolve().relative_to(base.resolve())
        except ValueError as error:
            raise LegacyBindingError("legacy object inventory escapes the corpus root") from error
        if not path.is_file() or path.stat().st_size != file.get("bytes") or digest_file(path) != digest:
            raise LegacyBindingError("legacy object content or digest differs")
        by_path[relative] = file
    actual_paths = {
        path.relative_to(base).as_posix()
        for path in base.rglob("*.json")
        if path.name != "manifest.json"
    }
    if set(by_path) != actual_paths:
        raise LegacyBindingError("legacy object inventory has missing or extra members")
    items = index.get("items")
    if not isinstance(items, list):
        raise LegacyBindingError("legacy index membership is missing")
    item_ids = [item.get("id") for item in items if isinstance(item, dict)]
    if (
        len(item_ids) != len(items)
        or any(not isinstance(item_id, str) or not ITEM_ID.fullmatch(item_id) for item_id in item_ids)
        or len(item_ids) != len(set(item_ids))
    ):
        raise LegacyBindingError("legacy member IDs are invalid or duplicated")
    expected_membership = expected["membership"]
    actual_membership = membership(item_ids)
    if {
        key: actual_membership[key] for key in ("itemCount", "itemIdsSha256")
    } != {
        key: expected_membership.get(key) for key in ("itemCount", "itemIdsSha256")
    }:
        raise LegacyBindingError("legacy member count or ID digest differs")
    item_objects = []
    for item_id in sorted(item_ids):
        record = by_path.get(f"items/{item_id}.json")
        if record is None:
            raise LegacyBindingError("legacy item object is missing")
        item_objects.append({"id": item_id, "bytes": record["bytes"], "sha256": record["sha256"]})
    if digest_bytes(compact_json(item_objects)) != expected_membership["itemObjectsSha256"]:
        raise LegacyBindingError("legacy member content digest differs")
    section_objects = [
        {"id": Path(path).stem, "bytes": record["bytes"], "sha256": record["sha256"]}
        for path, record in sorted(by_path.items()) if path.startswith("sections/")
    ]
    if (
        len(section_objects) != expected["sectionCount"]
        or digest_bytes(compact_json(section_objects)) != expected["sectionObjectsSha256"]
    ):
        raise LegacyBindingError("legacy section inventory or digest differs")
    if summary.get("counts") != expected["counts"]:
        raise LegacyBindingError("legacy completeness or review counts differ")
    corpus = summary.get("corpus", {})
    if {
        "publicationStatus": corpus.get("publicationStatus"),
        "promotionStatus": corpus.get("promotionStatus"),
    } != expected["state"]:
        raise LegacyBindingError("legacy publication or promotion state differs")
    return summary, index, by_path


def verify_evidence(
    binding: dict[str, Any], source_authority_path: Path, content_license_path: Path,
    notice_path: Path, attribution_path: Path, rights_matrix_path: Path,
    legacy_release_path: Path, legacy_tag_ref_path: Path, approval_issue_path: Path,
    approval_comment_path: Path, activation_run_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence = require_keys(
        binding["evidence"],
        {
            "sourceAuthority", "contentLicense", "notice", "attribution",
            "rightsMatrix", "legacyRelease", "activationRun",
        },
        "legacy evidence index",
    )
    verify_file_evidence(evidence["sourceAuthority"], source_authority_path, "source authority evidence")
    verify_file_evidence(evidence["contentLicense"], content_license_path, "content license evidence")
    verify_file_evidence(evidence["notice"], notice_path, "notice evidence")
    verify_file_evidence(evidence["attribution"], attribution_path, "attribution evidence")
    try:
        rights_bytes = rights_matrix_path.read_bytes()
    except OSError as error:
        raise LegacyBindingError("rights matrix evidence is missing") from error
    rights_evidence = require_keys(
        evidence["rightsMatrix"], {"repository", "commit", "path", "gitBlobSha1", "sha256"},
        "rights matrix evidence",
    )
    if (
        git_blob_sha1(rights_bytes) != rights_evidence["gitBlobSha1"]
        or digest_bytes(rights_bytes) != rights_evidence["sha256"]
    ):
        raise LegacyBindingError("rights matrix evidence digest differs")
    rights_matrix = load(rights_matrix_path)
    source_authority = load(source_authority_path)
    verify_release(
        evidence["legacyRelease"], load(legacy_release_path), load(legacy_tag_ref_path),
        "legacy release evidence",
    )
    if (
        binding["base"]["pointer"].get("distributionCommit")
        != evidence["legacyRelease"]["commit"]
    ):
        raise LegacyBindingError("legacy release differs from the active pointer")
    run = load(activation_run_path)
    expected_run = evidence["activationRun"]
    for key, expected in expected_run.items():
        if run.get(key) != expected:
            raise LegacyBindingError("legacy activation-run evidence differs")
    approval = require_keys(
        binding["approval"],
        {
            "repository", "issueNumber", "nodeId", "actor", "recordedAt", "decision",
            "bodySha256", "scopeSha256", "comment",
        },
        "legacy approval",
    )
    actor = require_keys(
        approval["actor"], {"login", "id", "authority"}, "legacy approval actor",
    )
    comment_binding = require_keys(
        approval["comment"], {"id", "nodeId", "createdAt", "bodySha256"},
        "legacy approval comment",
    )
    issue = load(approval_issue_path)
    comment = load(approval_comment_path)
    issue_body = issue.get("body")
    repository_api = approval["repository"].replace(
        "https://github.com/", "https://api.github.com/repos/"
    )
    repository_owner = approval["repository"].removeprefix("https://github.com/").split("/", 1)[0]
    if (
        approval["repository"] != evidence["contentLicense"]["repository"]
        or actor["authority"] != "repository-owner"
        or actor["login"] != repository_owner
        or issue.get("repository_url") != repository_api
        or issue.get("url") != f"{repository_api}/issues/{approval['issueNumber']}"
        or issue.get("number") != approval["issueNumber"]
        or issue.get("node_id") != approval["nodeId"]
        or issue.get("created_at") != approval["recordedAt"]
        or issue.get("user", {}).get("login") != actor.get("login")
        or issue.get("user", {}).get("id") != actor.get("id")
        or not isinstance(issue_body, str)
        or digest_bytes(issue_body.encode("utf-8")) != approval["bodySha256"]
        or approval["scopeSha256"] != scope_digest(binding)
        or approval["decision"] != "approved-one-time-compatibility-migration"
        or comment.get("id") != comment_binding["id"]
        or comment.get("node_id") != comment_binding["nodeId"]
        or comment.get("created_at") != comment_binding["createdAt"]
        or comment.get("issue_url") != issue.get("url")
        or comment.get("user", {}).get("login") != actor["login"]
        or comment.get("user", {}).get("id") != actor["id"]
        or not isinstance(comment.get("body"), str)
        or digest_bytes(comment["body"].encode("utf-8")) != comment_binding["bodySha256"]
    ):
        raise LegacyBindingError("legacy approval identity or decision differs")
    return source_authority, rights_matrix


def verify_target(
    expected: dict[str, Any], manifest: dict[str, Any], release: dict[str, Any],
    tag_ref: dict[str, Any], target_schema: str,
) -> None:
    require_keys(expected, {"schemaVersion", "release", "oneTime", "reusePolicy"}, "migration target")
    if (
        target_schema != TARGET_SCHEMA
        or expected["schemaVersion"] != TARGET_SCHEMA
        or expected["oneTime"] is not True
        or expected["reusePolicy"] != "exact-active-schema-4-pointer-only"
    ):
        raise LegacyBindingError("legacy binding target or reuse policy differs")
    verify_release(expected["release"], release, tag_ref, "migration target release")
    if (
        manifest.get("schemaVersion") != "2.0.0"
        or manifest.get("repository", {}).get("url") != expected["release"]["repository"]
        or manifest.get("repository", {}).get("commit") != expected["release"]["commit"]
    ):
        raise LegacyBindingError("legacy binding target distribution differs")


def verify_legacy_binding(
    binding_path: Path, base: Path, pointer_path: Path, legacy_release_path: Path,
    legacy_tag_ref_path: Path, rights_matrix_path: Path, source_authority_path: Path,
    content_license_path: Path, notice_path: Path, attribution_path: Path,
    approval_issue_path: Path, approval_comment_path: Path, activation_run_path: Path,
    target_manifest_path: Path, target_release_path: Path, target_tag_ref_path: Path,
    target_schema: str = TARGET_SCHEMA,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    binding = load(binding_path)
    require_keys(
        binding,
        {
            "schema", "bindingId", "status", "base", "source", "cohorts", "evidence",
            "approval", "allowedMigration", "nonClaims", "retirement",
        },
        "legacy provenance binding",
    )
    if binding["schema"] != BINDING_SCHEMA or binding["status"] != "approved-one-time":
        raise LegacyBindingError("legacy provenance binding schema or status differs")
    if not isinstance(binding["nonClaims"], list) or len(binding["nonClaims"]) < 6:
        raise LegacyBindingError("legacy provenance binding non-claims are incomplete")
    summary, index, objects = verify_base_inventory(binding["base"], base, pointer_path)
    source_authority, rights_matrix = verify_evidence(
        binding, source_authority_path, content_license_path, notice_path, attribution_path,
        rights_matrix_path, legacy_release_path, legacy_tag_ref_path, approval_issue_path,
        approval_comment_path, activation_run_path,
    )
    if (
        load(base / "manifest.json").get("distribution", {}).get("repository")
        != binding["evidence"]["legacyRelease"]["repository"]
    ):
        raise LegacyBindingError("legacy release repository differs from the corpus manifest")
    target_manifest = load(target_manifest_path)
    verify_target(
        binding["allowedMigration"], target_manifest, load(target_release_path),
        load(target_tag_ref_path), target_schema,
    )
    source = require_keys(
        binding["source"],
        {"authorityId", "repository", "commit", "artifactSha256", "arabicRights"},
        "legacy source binding",
    )
    machine_text = source_authority.get("machineText", {})
    matrix_license = rights_matrix.get("public_content_license", {})
    matrix_attribution = rights_matrix.get("attribution", [])
    expected_license = {"spdx": matrix_license.get("spdx"), "url": matrix_license.get("url")}
    require_keys(source["arabicRights"], {"license", "attribution"}, "legacy Arabic rights")
    require_keys(source["arabicRights"]["license"], {"spdx", "url"}, "legacy Arabic license")
    if (
        source_authority.get("authorityId") != source["authorityId"]
        or source_authority.get("assessment", {}).get("status") != "approved-for-publication"
        or machine_text.get("repository") != source["repository"]
        or machine_text.get("commit") != source["commit"]
        or machine_text.get("sha256") != source["artifactSha256"]
        or {key: machine_text.get("license", {}).get(key) for key in ("spdx", "url")} != expected_license
        or source["arabicRights"].get("license") != expected_license
        or len(matrix_attribution) < 2
        or source["arabicRights"].get("attribution") != matrix_attribution[1]
    ):
        raise LegacyBindingError("legacy Arabic source or rights claim differs from evidence")
    matrix = {
        "id": rights_matrix.get("matrix_id"),
        "schema": rights_matrix.get("schema"),
        "decision": rights_matrix.get("publication_decision", {}).get("public_reuse"),
        "reviewedOn": rights_matrix.get("reviewed_on"),
        "followUp": rights_matrix.get("follow_up_review", {}).get("status"),
    }
    cohorts = binding["cohorts"]
    if not isinstance(cohorts, list) or len(cohorts) != 2:
        raise LegacyBindingError("legacy cohort binding is incomplete")
    if matrix != cohorts[0].get("rights", {}).get("matrix"):
        raise LegacyBindingError("legacy rights-matrix claim differs from evidence")
    items_by_id = {
        item["id"]: load(base / "items" / f"{item['id']}.json")
        for item in index["items"]
    }
    assigned: set[str] = set()
    result: list[dict[str, Any]] = []
    for cohort in cohorts:
        require_keys(
            cohort,
            {"id", "selector", "membership", "source", "rights", "state", "evidenceKind"},
            "legacy cohort",
        )
        selector = cohort["selector"]
        require_keys(selector, {"field", "equals"}, "legacy cohort selector")
        if selector.get("field") != ALLOWED_SELECTOR:
            raise LegacyBindingError("legacy cohort selector is unsupported")
        member_ids = sorted(
            item_id for item_id, item in items_by_id.items()
            if value_at(item, selector["field"]) == selector["equals"]
        )
        if assigned.intersection(member_ids):
            raise LegacyBindingError("legacy cohort membership overlaps")
        assigned.update(member_ids)
        actual_membership = membership(member_ids)
        expected_membership = cohort["membership"]
        if {
            key: actual_membership[key] for key in ("itemCount", "itemIdsSha256")
        } != {
            key: expected_membership.get(key) for key in ("itemCount", "itemIdsSha256")
        }:
            raise LegacyBindingError("legacy cohort count or member digest differs")
        item_objects = [
            {
                "id": item_id,
                "bytes": objects[f"items/{item_id}.json"]["bytes"],
                "sha256": objects[f"items/{item_id}.json"]["sha256"],
            }
            for item_id in member_ids
        ]
        if digest_bytes(compact_json(item_objects)) != expected_membership.get("itemObjectsSha256"):
            raise LegacyBindingError("legacy cohort content digest differs")
        cohort_source = cohort["source"]
        rights = cohort["rights"]
        if (
            cohort["evidenceKind"] not in {"sabiqah-authored", "al-isabah-project-authored"}
            or set(rights) != {"arabicSource", "englishTranslation", "matrix", "excludedMaterial"}
            or set(rights.get("arabicSource", {})) != {"license", "attribution"}
            or set(rights.get("englishTranslation", {})) != {"license", "attribution"}
        ):
            raise LegacyBindingError("legacy cohort rights evidence kind is unknown")
        english = rights.get("englishTranslation", {})
        expected_english_attribution = (
            "Sabiqah contributors" if cohort["evidenceKind"] == "sabiqah-authored"
            else matrix_attribution[0]
        )
        if (
            set(cohort_source) != {"producerAuthorityId"}
            or english.get("license") != expected_license
            or english.get("attribution") != expected_english_attribution
            or rights.get("arabicSource") != source["arabicRights"]
            or rights.get("matrix") != matrix
            or not rights.get("excludedMaterial")
            or cohort["state"] != {
                "publicationStatus": "public-working",
                "promotionStatus": "blocked",
                "completeness": "carried-forward",
            }
        ):
            raise LegacyBindingError("legacy cohort rights or state claim differs from evidence")
        for item_id in member_ids:
            item = items_by_id[item_id]
            item_source = item.get("source", {})
            provenance = item.get("provenance", {})
            if (
                item.get("schemaVersion") != LEGACY_SCHEMA
                or item.get("corpusId") != summary["corpus"]["id"]
                or item.get("humanReview") != "unreviewed"
                or item.get("publicEligibility") != "eligible"
                or item.get("translationState") != "translated"
                or item_source.get("authorityId") != source["authorityId"]
                or item_source.get("license") != expected_license
                or provenance.get("sourceAuthorityId") != source["authorityId"]
                or provenance.get("sourceArtifactSha256") != source["artifactSha256"]
            ):
                raise LegacyBindingError("legacy record claim differs from bound evidence")
        result.append({
            "id": cohort["id"],
            "kind": "legacy-schema-4",
            "source": {
                "authorityId": source["authorityId"],
                "producerAuthorityId": cohort_source["producerAuthorityId"],
                "repository": source["repository"],
                "commit": source["commit"],
                "artifactSha256": source["artifactSha256"],
            },
            "rights": rights,
            "state": cohort["state"],
            "membership": actual_membership,
            "upstream": {"corpusId": summary["corpus"]["id"], "schemaVersion": LEGACY_SCHEMA},
        })
    if assigned != set(items_by_id):
        raise LegacyBindingError("legacy cohort membership has missing or extra records")
    binding_bytes = binding_path.read_bytes().replace(b"\r\n", b"\n")
    return result, {"id": binding["bindingId"], "sha256": digest_bytes(binding_bytes)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding", required=True, type=Path)
    parser.add_argument("--base-corpus", required=True, type=Path)
    parser.add_argument("--pointer", required=True, type=Path)
    parser.add_argument("--legacy-release-metadata", required=True, type=Path)
    parser.add_argument("--legacy-tag-ref", required=True, type=Path)
    parser.add_argument("--rights-matrix", required=True, type=Path)
    parser.add_argument("--source-authority", required=True, type=Path)
    parser.add_argument("--content-license", required=True, type=Path)
    parser.add_argument("--notice", required=True, type=Path)
    parser.add_argument("--attribution", required=True, type=Path)
    parser.add_argument("--approval-issue", required=True, type=Path)
    parser.add_argument("--approval-comment", required=True, type=Path)
    parser.add_argument("--activation-run", required=True, type=Path)
    parser.add_argument("--target-manifest", required=True, type=Path)
    parser.add_argument("--target-release-metadata", required=True, type=Path)
    parser.add_argument("--target-tag-ref", required=True, type=Path)
    args = parser.parse_args()
    verify_legacy_binding(
        args.binding.resolve(), args.base_corpus.resolve(), args.pointer.resolve(),
        args.legacy_release_metadata.resolve(), args.legacy_tag_ref.resolve(),
        args.rights_matrix.resolve(), args.source_authority.resolve(),
        args.content_license.resolve(), args.notice.resolve(), args.attribution.resolve(),
        args.approval_issue.resolve(), args.approval_comment.resolve(),
        args.activation_run.resolve(),
        args.target_manifest.resolve(), args.target_release_metadata.resolve(),
        args.target_tag_ref.resolve(),
    )
    print("Legacy schema-4 provenance binding is valid for the one-time schema-5 migration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
