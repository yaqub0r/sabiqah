import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
REBUILD_SPEC = importlib.util.spec_from_file_location(
    "rebuild_al_isabah_public_corpus",
    ROOT / "scripts" / "rebuild_al_isabah_public_corpus.py",
)
REBUILD = importlib.util.module_from_spec(REBUILD_SPEC)
sys.modules["rebuild_al_isabah_public_corpus"] = REBUILD
assert REBUILD_SPEC.loader is not None
REBUILD_SPEC.loader.exec_module(REBUILD)

VALIDATE_SPEC = importlib.util.spec_from_file_location(
    "validate_public_corpus", ROOT / "scripts" / "validate_public_corpus.py"
)
VALIDATE = importlib.util.module_from_spec(VALIDATE_SPEC)
assert VALIDATE_SPEC.loader is not None
VALIDATE_SPEC.loader.exec_module(VALIDATE)


class PublicCorpusTests(unittest.TestCase):
    def test_compaction_removes_parenthetical_honorific_commas(self):
        self.assertEqual(
            REBUILD.compact_registry_aliases(
                "the Prophet, may God bless him and grant him peace.", "en"
            ),
            "the Prophet ﷺ.",
        )
        self.assertEqual(
            REBUILD.compact_registry_aliases(
                "the Prophet, may God bless him and grant him peace, said", "en"
            ),
            "the Prophet ﷺ said",
        )

    def test_source_authority_record_matches_the_pinned_contract(self):
        REBUILD.validate_source_authority_record(REBUILD.DEFAULT_SOURCE_AUTHORITY)

    def test_source_authority_record_rejects_a_false_facsimile_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            record = json.loads(
                REBUILD.DEFAULT_SOURCE_AUTHORITY.read_text(encoding="utf-8")
            )
            record["sourceBinding"]["sameEditionFacsimileApproved"] = True
            path = Path(temp) / "authority.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "sameEditionFacsimileApproved"):
                REBUILD.validate_source_authority_record(path)

    def legacy_entry(self) -> dict:
        return {
            "schemaVersion": "2.0.0",
            "corpusId": "private-test",
            "id": "isabah-entry-00010759",
            "kind": "entry",
            "sequence": 10759,
            "printedEntryNumber": 10759,
            "volume": 8,
            "title": {
                "en": "Asiya, sister of the Prophet—may Allah bless him and grant him peace",
                "ar": "آسية أخت النبي ﷺ",
            },
            "translationState": "translated",
            "machineAssessment": "passed",
            "humanReview": "unreviewed",
            "segments": [
                {
                    "id": "legacy-segment",
                    "arabic": "١٠٧٥٩- آسية أخت النبي ﷺ كانت من الصحابيات.",
                    "english": "10759—Asiya, sister of the Prophet—may Allah bless him and grant him peace\n\nShe was one of the Companions.",
                    "pages": [],
                    "machineState": "private",
                }
            ],
            "names": [],
            "unresolved": [],
            "workflowStages": [],
            "provenance": {
                "sourceArtifactId": "private:test",
                "sourceArtifactSha256": "0" * 64,
            },
        }

    def make_inputs(self, root: Path) -> tuple[Path, Path, str]:
        legacy = root / "legacy"
        items = legacy / "items"
        items.mkdir(parents=True)
        (items / "isabah-entry-00010759.json").write_text(
            json.dumps(self.legacy_entry(), ensure_ascii=False), encoding="utf-8"
        )
        passage = {
            "id": "isabah-passage-test-0001",
            "kind": "passage",
            "printedEntryNumber": None,
        }
        (items / "isabah-passage-test-0001.json").write_text(
            json.dumps(passage), encoding="utf-8"
        )
        openiti = root / "openiti.txt"
        openiti.write_text(
            "######OpenITI#\n\nPageV07P001\n"
            "### $$ 10753 آسية أخت النبي صلى الله عليه وسلم كانت من الصحابيات\n",
            encoding="utf-8",
        )
        digest = hashlib.sha256(openiti.read_bytes()).hexdigest()
        return legacy, openiti, digest

    def build(self, root: Path) -> Path:
        legacy, openiti, digest = self.make_inputs(root)
        output = root / "public"
        with patch.object(REBUILD, "SOURCE_SHA256", digest), patch.object(
            VALIDATE, "SOURCE_SHA256", digest
        ):
            summary = REBUILD.rebuild(
                legacy, openiti, output, "2026-08-12T00:00:00Z"
            )
            self.assertEqual(summary["counts"]["entries"], 1)
            self.assertEqual(summary["counts"]["quarantined"], 1)
            self.assertEqual(
                summary["exclusions"],
                {
                    "contextualPassagesPendingPublicSourceAlignment": 1,
                    "recordsPendingRemediation": 0,
                },
            )
            self.assertEqual(VALIDATE.validate(output), [])
        return output

    def test_rebuild_replaces_private_arabic_and_accounts_for_quarantine(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = self.build(root)
            item = json.loads(
                (output / "items" / "isabah-entry-00010759.json").read_text(
                    encoding="utf-8"
                )
            )
            displayed = item["title"]["ar"] + " " + item["segments"][0]["arabic"]
            self.assertIn("ﷺ", displayed)
            self.assertNotIn("صلى الله عليه وسلم", displayed)
            self.assertEqual(item["honorificPolicyVersion"], "1.0.0")
            self.assertTrue(
                any(
                    occurrence["accessibleText"]
                    == "may Allah bless him and grant him peace"
                    for occurrence in item["honorifics"]
                )
            )
            self.assertTrue(
                any(
                    occurrence["language"] == "ar"
                    and occurrence["observedForm"] == "صلى الله عليه وسلم"
                    and occurrence["renderedForm"] == "ﷺ"
                    for occurrence in item["honorifics"]
                )
            )
            quarantine = json.loads(
                (output / "quarantine.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                quarantine["records"][0]["reasonCodes"],
                ["no-approved-entry-alignment"],
            )
            self.assertEqual(
                quarantine["records"][0]["disposition"],
                "excluded-pending-public-source-alignment",
            )
            exclusions = json.loads(
                (output / "exclusions.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                exclusions["records"][0],
                {
                    "id": "isabah-passage-test-0001",
                    "kind": "passage",
                    "disposition": "excluded-pending-public-source-alignment",
                    "reasonCodes": ["no-approved-entry-alignment"],
                },
            )

    def test_rebuild_keeps_public_english_when_literal_honorific_counts_differ(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy, openiti, digest = self.make_inputs(root)
            item_path = legacy / "items" / "isabah-entry-00010759.json"
            item = json.loads(item_path.read_text(encoding="utf-8"))
            item["title"]["en"] = "Asiya, sister of the Prophet"
            item["segments"][0]["english"] = "She was one of the Companions."
            item_path.write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")
            output = root / "public"
            with patch.object(REBUILD, "SOURCE_SHA256", digest), patch.object(
                VALIDATE, "SOURCE_SHA256", digest
            ):
                summary = REBUILD.rebuild(
                    legacy, openiti, output, "2026-08-12T00:00:00Z"
                )
                self.assertEqual(summary["counts"]["entries"], 1)
                self.assertEqual(summary["counts"]["translated"], 1)
                self.assertEqual(summary["counts"]["quarantined"], 1)
                self.assertEqual(VALIDATE.validate(output), [])
            public = json.loads(
                (output / "items" / "isabah-entry-00010759.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(public["translationState"], "translated")
            self.assertEqual(public["title"]["en"], "Asiya, sister of the Prophet")
            self.assertEqual(
                public["segments"][0]["english"], "She was one of the Companions."
            )
            self.assertEqual(public["machineAssessment"], "needs_attention")
            self.assertEqual(public["remediation"]["englishExclusionReasonCodes"], [])
            self.assertEqual(
                public["remediation"]["honorificSemanticReview"],
                "needs_attention",
            )

    def test_exact_title_and_substantial_body_overlap_survive_edition_apparatus(self):
        legacy_length = 1000
        source_length = 1000
        title_score = 1.0
        body_score = 0.60
        short_exact_title = title_score >= 0.95 and min(
            legacy_length, source_length
        ) <= 150
        exact_title_with_substantial_body_overlap = (
            title_score >= 0.995 and body_score >= 0.60
        )
        self.assertFalse(short_exact_title)
        self.assertTrue(exact_title_with_substantial_body_overlap)

    def test_validator_rejects_an_untranslated_public_record(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = self.build(root)
            item_path = output / "items" / "isabah-entry-00010759.json"
            item = json.loads(item_path.read_text(encoding="utf-8"))
            item["translationState"] = "untranslated"
            item_path.write_text(json.dumps(item), encoding="utf-8")
            errors = VALIDATE.validate(output)
            self.assertTrue(
                any("must expose public working English" in error for error in errors)
            )

    def test_validator_rejects_a_private_locator(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = self.build(root)
            item_path = output / "items" / "isabah-entry-00010759.json"
            item = json.loads(item_path.read_text(encoding="utf-8"))
            item["segments"][0]["english"] += " https://usul.ai/private"
            item_path.write_text(json.dumps(item), encoding="utf-8")
            errors = VALIDATE.validate(output)
            self.assertTrue(any("private or unapproved" in error for error in errors))

    def test_validator_rejects_a_comma_before_a_compact_honorific(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = self.build(root)
            item_path = output / "items" / "isabah-entry-00010759.json"
            item = json.loads(item_path.read_text(encoding="utf-8"))
            item["segments"][0]["english"] = "The Prophet, ﷺ spoke."
            item_path.write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")
            errors = VALIDATE.validate(output)
            self.assertTrue(
                any(
                    "compact honorific is separated from its referent by a comma"
                    in error
                    for error in errors
                )
            )

    def test_validator_rejects_honorific_agreement_that_differs_from_registry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = self.build(root)
            item_path = output / "items" / "isabah-entry-00010759.json"
            item = json.loads(item_path.read_text(encoding="utf-8"))
            item["honorifics"][0]["agreement"] = {
                "number": "dual",
                "gender": "common",
            }
            item_path.write_text(json.dumps(item), encoding="utf-8")
            errors = VALIDATE.validate(output)
            self.assertTrue(
                any(
                    "honorific agreement differs from registry" in error
                    for error in errors
                )
            )

    def test_validator_rejects_section_content_that_differs_from_item(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = self.build(root)
            section_path = next((output / "sections").glob("*.json"))
            section = json.loads(section_path.read_text(encoding="utf-8"))
            section["items"][0]["segments"][0]["arabic"] = "ØºÙŠØ± Ù…Ø·Ø§Ø¨Ù‚"
            section_path.write_text(json.dumps(section), encoding="utf-8")
            errors = VALIDATE.validate(output)
            self.assertTrue(
                any("embedded item differs from detail" in error for error in errors)
            )


if __name__ == "__main__":
    unittest.main()
