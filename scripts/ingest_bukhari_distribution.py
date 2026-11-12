"""Verify the reviewed immutable Bukhari release; emit build-only reader data.

No upstream code or HTML is executed. Only the five fixed archive members are
read in memory, and only validated book data is projected into ignored storage.
"""

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = ROOT / "evidence/releases/bukhari-opening-faith-working-1.pin.json"
MANIFEST_PATH = ROOT / "evidence/releases/bukhari-opening-faith-working-1.manifest.json"
MEMBERS = {"manifest.json", "record-schema.json", "records.jsonl", "reader.html", "release-closure.json"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(data):
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda _: require(False, "Non-finite JSON"))


def validate_schema(value, schema, definitions):
    """The pinned closed schema uses this small, explicit JSON Schema subset."""
    allowed = {"$ref", "$defs", "$id", "$schema", "title", "type", "properties",
               "required", "additionalProperties", "items", "minLength", "minimum",
               "pattern", "enum", "anyOf"}
    require(set(schema) <= allowed, "Unsupported schema keyword")
    if "$ref" in schema:
        ref = schema["$ref"]
        require(ref.startswith("#/$defs/") and ref[8:] in definitions, "Unknown schema reference")
        return validate_schema(value, definitions[ref[8:]], definitions)
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            try:
                validate_schema(value, option, definitions)
                return
            except ValueError:
                pass
        raise ValueError("Value does not match schema alternatives")
    types = {"object": dict, "array": list, "string": str, "integer": int, "null": type(None)}
    require(schema.get("type") in types and type(value) is types[schema["type"]], "Invalid record field type")
    if "enum" in schema:
        require(value in schema["enum"], "Invalid enumerated field")
    if isinstance(value, dict):
        properties = schema["properties"]
        require(schema.get("additionalProperties") is False, "Open record schema")
        require(set(schema["required"]) <= set(value) <= set(properties), "Missing or unexpected record field")
        for key, field in value.items():
            validate_schema(field, properties[key], definitions)
    elif isinstance(value, list):
        for item in value:
            validate_schema(item, schema["items"], definitions)
    elif isinstance(value, str):
        require(len(value) >= schema.get("minLength", 0), "Empty record string")
        if "pattern" in schema:
            require(re.search(schema["pattern"], value) is not None, "Invalid field pattern")
    elif type(value) is int:
        require(value >= schema.get("minimum", value), "Field below minimum")


def validate_records(records, manifest, schema, pin):
    ids = []
    numbers = []
    previous = 0
    sections = []
    for record in records:
        validate_schema(record, schema, schema["$defs"])
        require(record["sourceOrdinal"] > previous, "Record order is not increasing")
        previous = record["sourceOrdinal"]
        ids.append(record["sourceUnitId"])
        sections.append(record["bookSection"])
        require(record["humanReview"] == "unreviewed", "Unexpected review claim")
        require(digest(record["arabic"].encode()) == record["arabicSha256"], "Arabic digest mismatch")
        if record["printedHadithNumber"] is not None:
            require(record["kind"] == "report", "Number on non-report")
            numbers.append(record["printedHadithNumber"])
        cursor = 0
        for segment in record["segments"]:
            require(segment["start"] == cursor and segment["end"] > cursor, "Invalid segment order")
            require(record["arabic"][cursor:segment["end"]] == segment["arabic"], "Segment source mismatch")
            cursor = segment["end"]
        require(cursor == len(record["arabic"]), "Incomplete Arabic segmentation")
        chain = record["isnad"]
        nodes = {node["id"]: node for node in chain["nodes"]}
        edges = {edge["id"]: edge for edge in chain["edges"]}
        paths = {path["id"]: path for path in chain["paths"]}
        reports = {report["id"]: report for report in chain["reports"]}
        for key, collection in (("nodes", nodes), ("edges", edges), ("paths", paths), ("reports", reports)):
            require(len(collection) == len(chain[key]), "Duplicate chain identity")
        for node in nodes.values():
            if node["start"] is not None or node["end"] is not None:
                require(type(node["start"]) is int and type(node["end"]) is int and
                        0 <= node["start"] < node["end"] <= len(record["arabic"]) and
                        record["arabic"][node["start"]:node["end"]] == node["arabic"], "Invalid narrator source span")
        for edge in edges.values():
            require(edge["from"] in nodes and edge["to"] in nodes, "Unknown chain node")
            if edge["start"] is not None or edge["end"] is not None:
                require(type(edge["start"]) is int and type(edge["end"]) is int and
                        0 <= edge["start"] < edge["end"] <= len(record["arabic"]) and
                        record["arabic"][edge["start"]:edge["end"]] == edge["arabicWording"], "Invalid transmission source span")
        for path in paths.values():
            require(all(node in nodes for node in path["nodeIds"]), "Unknown path node")
            require(len(path["edgeIds"]) == max(0, len(path["nodeIds"]) - 1), "Incomplete path edges")
            for index, edge_id in enumerate(path["edgeIds"]):
                require(edge_id in edges and edges[edge_id]["from"] == path["nodeIds"][index] and
                        edges[edge_id]["to"] == path["nodeIds"][index + 1], "Unordered path edge")
        require({node for path in paths.values() for node in path["nodeIds"]} == set(nodes), "Unassigned chain node")
        require({edge for path in paths.values() for edge in path["edgeIds"]} == set(edges), "Unassigned chain edge")
        for report in reports.values():
            require(0 <= report["start"] < report["end"] <= len(record["arabic"]), "Invalid report span")
            require(all(path in paths for path in report["pathIds"]), "Unknown report path")
        for uncertainty in record["uncertainties"]:
            require(uncertainty["reportId"] is None or uncertainty["reportId"] in reports, "Unknown uncertainty report")
    require(len(records) == pin["recordCount"] == manifest["recordCount"], "Record count mismatch")
    require(len(ids) == len(set(ids)) and ids == manifest["proposal"]["scope"]["includedUnitIds"], "Release scope mismatch")
    require(numbers == list(range(1, pin["reportCount"] + 1)), "Report coverage mismatch")
    require(sections == sorted(sections, key={"opening": 0, "faith": 1}.get), "Book sections out of order")
    require(sum(len(record["uncertainties"]) for record in records) == pin["uncertaintyCount"], "Uncertainty disclosure mismatch")
    require(manifest["reviewCounts"] == {"human-reviewed": 0, "unreviewed": len(records)}, "Review totals mismatch")


def verify_archive(data, pin, approved_manifest):
    require(len(data) == pin["archiveBytes"] and digest(data) == pin["archiveSha256"], "Archive checksum mismatch")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        require(len(entries) == len(MEMBERS) and {entry.filename for entry in entries} == MEMBERS, "Unexpected archive members")
        for entry in entries:
            mode = entry.external_attr >> 16
            require(not entry.is_dir() and not stat.S_ISLNK(mode) and
                    (not stat.S_IFMT(mode) or stat.S_ISREG(mode)), "Non-regular archive member")
            require(entry.file_size < 2_000_000 and entry.flag_bits & 1 == 0, "Unsafe archive member")
        files = {entry.filename: archive.read(entry) for entry in entries}
    require(digest(files["manifest.json"]) == pin["manifestSha256"] == digest(approved_manifest), "Unapproved manifest")
    require(digest(files["record-schema.json"]) == pin["schemaSha256"], "Unapproved schema")
    require(digest(files["release-closure.json"]) == pin["closureSha256"], "Unapproved closure")
    manifest = strict_json(files["manifest.json"])
    closure = strict_json(files["release-closure.json"])
    require(manifest == strict_json(approved_manifest), "Manifest differs from approved release")
    require(manifest["version"] == 1 and manifest["contractId"] == "sahih-al-bukhari-distribution-1" and
            manifest["publicationEligible"] is True and manifest["releaseClass"] == "public-working" and
            manifest["canonicalPromotion"] == "unused" and manifest["repository"] == pin["repository"] and
            manifest["repositoryCommit"] == pin["commit"] and manifest["releaseId"] == pin["releaseId"], "Unsupported release identity or publication state")
    require(closure["version"] == 1 and closure["releaseId"] == pin["releaseId"] and
            closure["repositoryCommit"] == pin["commit"] and closure["previousReleaseId"] is None, "Invalid release closure")
    for inventory, expected in ((closure["artifacts"], MEMBERS - {"release-closure.json"}),
                                (manifest["artifacts"], MEMBERS - {"manifest.json", "release-closure.json"})):
        require(set(inventory) == expected, "Incomplete artifact inventory")
        for name, metadata in inventory.items():
            require(metadata == {"bytes": len(files[name]), "sha256": digest(files[name])}, "Artifact digest mismatch")
    records = [strict_json(line) for line in files["records.jsonl"].decode("utf-8").splitlines()]
    proposal_bytes = json.dumps({**manifest["proposal"], "records": records}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    require(digest(proposal_bytes) == manifest["proposalSha256"], "Proposal digest mismatch")
    validate_records(records, manifest, strict_json(files["record-schema.json"]), pin)
    return {"manifest": manifest, "records": records, "releaseUrl":
            f'https://github.com/{pin["repository"]}/releases/tag/{pin["tag"]}'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    pin = strict_json(PIN_PATH.read_bytes())
    cache = ROOT / ".runtime/bukhari-intake" / pin["archive"]
    archive_path = args.archive or cache
    if not archive_path.exists():
        require(args.archive is None, "Supplied archive does not exist")
        url = f'https://github.com/{pin["repository"]}/releases/download/{pin["tag"]}/{pin["archive"]}'
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read(pin["archiveBytes"] + 1)
    else:
        data = archive_path.read_bytes()
    result = verify_archive(data, pin, MANIFEST_PATH.read_bytes())
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.exists():
        cache.write_bytes(data)
    output = ROOT / ".runtime/bukhari-reader.json"
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    temporary.replace(output)
    print(f'Bukhari release verified: {pin["recordCount"]} records, {pin["reportCount"]} reports, {pin["uncertaintyCount"]} disclosures.')


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, zipfile.BadZipFile, OSError):
        raise SystemExit("Bukhari ingestion failed: pinned release verification did not pass.")
