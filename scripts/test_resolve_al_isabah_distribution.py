import unittest

from resolve_al_isabah_distribution import resolve_pointer


class AlIsabahDistributionPointerTests(unittest.TestCase):
    def test_accepts_a_consistent_pointer(self):
        corpus_id = "al-isabah-public-openiti-5835c18-book-aaaaaaaaaaaa"
        self.assertEqual(
            resolve_pointer({
                "schemaVersion": "1.0.0",
                "corpusId": corpus_id,
                "prefix": f"public-corpora/al-isabah/{corpus_id}",
            }),
            f"public-corpora/al-isabah/{corpus_id}",
        )

    def test_rejects_a_prefix_outside_the_corpus_root(self):
        with self.assertRaisesRegex(ValueError, "inconsistent prefix"):
            resolve_pointer({
                "schemaVersion": "1.0.0",
                "corpusId": "valid-corpus",
                "prefix": "research-evidence/private",
            })


if __name__ == "__main__":
    unittest.main()
