import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "export_corpus", ROOT / "scripts" / "export_al_isabah_review_corpus.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ExportCorpusTests(unittest.TestCase):
    def test_entry_projection_preserves_review_and_uncertainty(self):
        entry = {
            "id": "isabah-entry-00010786",
            "printed_entry_number": 10786,
            "title": {"english": "Arnab", "arabic_observed": "أرنب"},
            "segments": [
                {
                    "id": "isabah-entry-00010786-segment-0001",
                    "volume": 8,
                    "printed_page": 6,
                    "reader_page": 3919,
                    "reader_url": "https://usul.ai/t/isaba-fi-tamyiz/3919",
                    "arabic": "أرنب",
                    "english": "Arnab",
                    "machine_state": "machine_validated_unresolved",
                }
            ],
            "names": [{"arabic": "أرنب", "english": "Arnab", "kind": "person"}],
            "unresolved": [
                {
                    "category": "vocalization",
                    "arabic_span": "أرنب",
                    "explanation": "Vocalization requires review.",
                    "human_review_priority": "normal",
                }
            ],
            "translation": {
                "state": "translated",
                "machine_assessment": "needs_attention",
                "human_review": "unreviewed",
            },
            "provenance": {
                "source_artifact_id": "firstlight:volume-08",
                "source_artifact_sha256": MODULE.ARTIFACT_SHA,
            },
        }
        projected = MODULE.entry_item(entry, ["volume-08"], {}, {}, {})
        self.assertEqual(projected["machineAssessment"], "needs_attention")
        self.assertEqual(projected["unresolved"][0]["category"], "vocalization")
        self.assertEqual(projected["segments"][0]["arabic"], "أرنب")

    def test_clean_output_replaces_generated_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "corpus"
            stale = output / "items" / "stale.json"
            stale.parent.mkdir(parents=True)
            stale.write_text("{}", encoding="utf-8")
            MODULE.clean_output(output)
            self.assertTrue(output.is_dir())
            self.assertFalse(stale.exists())

    def test_cohort_provenance_is_projected(self):
        entry = {
            "id": "isabah-entry-00001805",
            "printed_entry_number": 1805,
            "title": {"english": "Hakim ibn Hizam", "arabic_observed": "حكيم بن حزام"},
            "segments": [
                {
                    "id": "isabah-entry-00001805-segment-0001",
                    "volume": 2,
                    "printed_page": 269,
                    "reader_page": 788,
                    "reader_url": "https://usul.ai/t/isaba-fi-tamyiz/788",
                    "arabic": "حكيم بن حزام",
                    "english": "Hakim ibn Hizam",
                    "machine_state": "machine_validated_unreviewed",
                }
            ],
            "names": [],
            "unresolved": [],
            "translation": {
                "state": "translated",
                "machine_assessment": "passed",
                "human_review": "unreviewed",
            },
            "provenance": {
                "cohort_id": "khadijah-immediate",
                "source_sha256": "90ff486a9564ec6867a8bb0eecc58769bbe62ddf33935d1f0b54818d8d2873bf",
            },
        }
        projected = MODULE.entry_item(entry, ["khadijah-immediate"], {}, {}, {})
        self.assertEqual(
            projected["provenance"]["sourceArtifactId"],
            "al-isabah:cohort:khadijah-immediate:entry:1805",
        )

    def test_list_projection_never_contains_text(self):
        item = {
            "id": "isabah-entry-00010786",
            "kind": "entry",
            "sequence": 10786,
            "printedEntryNumber": 10786,
            "volume": "8",
            "title": {"en": "Arnab", "ar": "أرنب"},
            "translationState": "translated",
            "machineAssessment": "needs_attention",
            "humanReview": "unreviewed",
            "collectionIds": ["volume-08"],
            "segments": [{"arabic": "restricted", "english": "draft"}],
            "unresolved": [{"category": "vocalization"}],
        }
        listed = MODULE.list_item(item)
        serialized = json.dumps(listed)
        self.assertNotIn("restricted", serialized)
        self.assertNotIn("draft\"", serialized)
        self.assertEqual(listed["unresolvedCount"], 1)

    def test_context_projection_preserves_classified_arabic_and_workflow(self):
        result_id = "source-result-001"
        value = {
            "result_id": result_id,
            "source": {
                "relationship": "earliest believer",
                "rationale": "Preserves the qualified claim.",
                "source": {
                    "pages": [{"volume": "1", "page": 84, "index": 77}],
                    "text_sha256": "a" * 64,
                },
            },
            "english_text": "Khadijah was the first woman to embrace Islam.",
            "names": [],
            "unresolved": [],
            "decisions": [],
        }
        projected = MODULE.context_item(
            value,
            1,
            {result_id: {"english_text": "Khadijah was the first woman."}},
            {result_id: {"issues": []}},
            {result_id: {"relevant_arabic": "ومن النساء خديجة"}},
        )
        self.assertEqual(projected["segments"][0]["arabic"], "ومن النساء خديجة")
        self.assertEqual(
            [stage["stage"] for stage in projected["workflowStages"]],
            [
                "source_alignment",
                "blind_translation",
                "critique",
                "adjudication",
                "machine_validation",
                "human_review",
                "compliance_promotion",
            ],
        )


if __name__ == "__main__":
    unittest.main()
