"""Consumer boundary tests use invented text, never private book evidence."""

import copy
import io
import json
import unittest
import warnings
import zipfile

import ingest_bukhari_distribution as consumer


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def fixture():
    record = {
        "sourceUnitId": "bukhari-l000001", "sourceOrdinal": 1,
        "bookSection": "opening", "printedHadithNumber": 1, "kind": "report",
        "arabic": "abc", "english": "Synthetic test only", "arabicSha256": consumer.digest(b"abc"),
        "humanReview": "unreviewed", "machineState": "agent_complete",
        "segments": [{"start": 0, "end": 3, "kind": "matn", "arabic": "abc"}],
        "isnad": {"status": "complete", "note": "Synthetic",
                  "nodes": [{"id": "n1", "start": 0, "end": 1, "arabic": "a"},
                            {"id": "n2", "start": 2, "end": 3, "arabic": "c"}],
                  "edges": [{"id": "e1", "from": "n1", "to": "n2", "start": 1, "end": 2, "arabicWording": "b"}],
                  "paths": [{"id": "p1", "nodeIds": ["n1", "n2"], "edgeIds": ["e1"]}],
                  "reports": [{"id": "r1", "start": 0, "end": 3, "pathIds": ["p1"]}]},
        "uncertainties": [],
    }
    # A closed synthetic schema exercises the generic validator independently
    # from the exact reviewed production schema bound by schemaSha256.
    def schema_for(value):
        if isinstance(value, dict):
            return {"type": "object", "properties": {key: schema_for(item) for key, item in value.items()},
                    "required": list(value), "additionalProperties": False}
        if isinstance(value, list):
            return {"type": "array", "items": schema_for(value[0]) if value else {"type": "string"}}
        return {"type": "integer" if type(value) is int else "string"}
    schema = {**schema_for(record), "$defs": {}}
    manifest = {
        "version": 1, "contractId": "sahih-al-bukhari-distribution-1",
        "repository": "yaqub0r/sahih-al-bukhari", "repositoryCommit": "a" * 40,
        "releaseId": "synthetic", "releaseClass": "public-working",
        "publicationEligible": True, "canonicalPromotion": "unused", "recordCount": 1,
        "reviewCounts": {"human-reviewed": 0, "unreviewed": 1},
        "proposal": {"scope": {"includedUnitIds": [record["sourceUnitId"]]}},
    }
    pin = {"repository": manifest["repository"], "commit": manifest["repositoryCommit"],
           "releaseId": "synthetic", "tag": "synthetic", "recordCount": 1, "reportCount": 1,
           "uncertaintyCount": 0}
    return record, manifest, schema, pin


def package(record, manifest, schema, pin, extra=None):
    manifest = copy.deepcopy(manifest)
    files = {"record-schema.json": encoded(schema), "records.jsonl": encoded(record) + b"\n",
             "reader.html": b"<p>Synthetic, never rendered by Sabiqah</p>"}
    metadata = lambda data: {"bytes": len(data), "sha256": consumer.digest(data)}
    manifest["artifacts"] = {key: metadata(data) for key, data in files.items()}
    manifest["proposalSha256"] = consumer.digest(encoded({**manifest["proposal"], "records": [record]}))
    files["manifest.json"] = encoded(manifest)
    files["release-closure.json"] = encoded({"version": 1, "releaseId": pin["releaseId"],
        "repositoryCommit": pin["commit"], "previousReleaseId": None,
        "artifacts": {key: metadata(data) for key, data in files.items()}})
    if extra:
        files.update(extra)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    data = output.getvalue()
    pin = {**pin, "archiveBytes": len(data), "archiveSha256": consumer.digest(data),
           "manifestSha256": consumer.digest(files["manifest.json"]),
           "schemaSha256": consumer.digest(files["record-schema.json"]),
           "closureSha256": consumer.digest(files["release-closure.json"])}
    return data, pin, files["manifest.json"]


class DistributionTests(unittest.TestCase):
    def test_verified_release_preserves_text(self):
        parts = fixture()
        result = consumer.verify_archive(*package(*parts))
        self.assertEqual(result["records"], [parts[0]])

    def test_archive_tampering_is_rejected(self):
        data, pin, manifest = package(*fixture())
        with self.assertRaisesRegex(ValueError, "checksum"):
            consumer.verify_archive(data + b"!", pin, manifest)

    def test_extra_traversing_member_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "members"):
            consumer.verify_archive(*package(*fixture(), extra={"../escape": b"x"}))

    def test_duplicate_and_symlink_members_are_rejected(self):
        for symlink in (False, True):
            data, pin, manifest = package(*fixture())
            buffer = io.BytesIO() if symlink else io.BytesIO(data)
            with warnings.catch_warnings(), zipfile.ZipFile(buffer, "w" if symlink else "a") as archive:
                warnings.simplefilter("ignore", UserWarning)
                if symlink:
                    with zipfile.ZipFile(io.BytesIO(data)) as original:
                        for name in original.namelist():
                            info = zipfile.ZipInfo(name)
                            info.create_system = 3
                            info.external_attr = (0o120777 if name == "reader.html" else 0o100644) << 16
                            archive.writestr(info, original.read(name))
                else:
                    archive.writestr("records.jsonl", b"synthetic")
            altered = buffer.getvalue()
            pin.update(archiveBytes=len(altered), archiveSha256=consumer.digest(altered))
            with self.subTest(symlink=symlink), self.assertRaises(ValueError):
                consumer.verify_archive(altered, pin, manifest)

    def test_closure_binds_every_artifact(self):
        with self.assertRaisesRegex(ValueError, "Artifact digest"):
            consumer.verify_archive(*package(*fixture(), extra={"reader.html": b"altered"}))

    def test_unknown_contract_and_ineligible_release_are_rejected(self):
        for key, value in (("contractId", "sahih-al-bukhari-distribution-2"), ("publicationEligible", False),
                           ("repositoryCommit", "b" * 40)):
            record, manifest, schema, pin = fixture()
            manifest[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "identity|publication"):
                consumer.verify_archive(*package(record, manifest, schema, pin))

    def test_incomplete_or_reordered_records_are_rejected(self):
        record, manifest, schema, pin = fixture()
        with self.assertRaisesRegex(ValueError, "order"):
            consumer.validate_records([record, record], manifest, schema, pin)
        manifest["proposal"]["scope"]["includedUnitIds"] = ["different"]
        with self.assertRaisesRegex(ValueError, "scope"):
            consumer.validate_records([record], manifest, schema, pin)

    def test_invented_review_and_missing_disclosures_are_rejected(self):
        record, manifest, schema, pin = fixture()
        record["humanReview"] = "human-reviewed"
        with self.assertRaisesRegex(ValueError, "review claim"):
            consumer.validate_records([record], manifest, schema, pin)
        record["humanReview"] = "unreviewed"
        pin["uncertaintyCount"] = 1
        with self.assertRaisesRegex(ValueError, "disclosure"):
            consumer.validate_records([record], manifest, schema, pin)

    def test_omitted_source_text_and_unknown_fields_are_rejected(self):
        record, manifest, schema, pin = fixture()
        record["segments"][0]["arabic"] = "ab"
        with self.assertRaisesRegex(ValueError, "source mismatch"):
            consumer.validate_records([record], manifest, schema, pin)
        record["privateTrace"] = "must never enter reader"
        with self.assertRaisesRegex(ValueError, "unexpected"):
            consumer.validate_records([record], manifest, schema, pin)

    def test_duplicate_keys_and_unsupported_schema_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            consumer.strict_json('{"x":1,"x":2}')
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            consumer.validate_schema("test", {"type": "string", "unsupported": True}, {})
        with self.assertRaisesRegex(ValueError, "type"):
            consumer.validate_schema(True, {"type": "integer"}, {})

    def test_chain_order_references_and_source_wording_are_bound(self):
        for mutate in (
            lambda r: r["isnad"]["paths"][0]["nodeIds"].reverse(),
            lambda r: r["isnad"]["edges"][0].update(to="absent"),
            lambda r: r["isnad"]["edges"][0].update(arabicWording="x"),
            lambda r: r["isnad"]["nodes"][0].update(arabic="x"),
            lambda r: r["isnad"]["reports"][0].update(pathIds=["absent"]),
        ):
            record, manifest, schema, pin = fixture()
            mutate(record)
            with self.assertRaises(ValueError):
                consumer.validate_records([record], manifest, schema, pin)


if __name__ == "__main__":
    unittest.main()
