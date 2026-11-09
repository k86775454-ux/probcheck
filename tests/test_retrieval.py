"""Retrieval over the probability notes: provenance, currency reranking and the empty case."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import retrieve


class RetrievalTests(unittest.TestCase):
    def test_every_hit_keeps_provenance(self):
        for h in retrieve.retrieve("what does independent mean", k=3):
            for key in ("id", "source", "section", "date", "score", "superseded", "text"):
                self.assertIn(key, h)

    def test_superseded_never_ranks_first(self):
        raw = retrieve.retrieve("can two events be mutually exclusive and independent", k=3, rerank=False)
        self.assertTrue(raw[0]["superseded"])          # the Lab 4 failure, reproduced
        hits = retrieve.retrieve("can two events be mutually exclusive and independent", k=20)
        self.assertFalse(hits[0]["superseded"])         # fixed by reranking
        old = [h for h in hits if h["superseded"]]
        self.assertTrue(old and "replaced_by" in old[0])

    def test_unrelated_question_scores_zero(self):
        self.assertEqual(0, retrieve.retrieve("what is a markov chain", k=1)[0]["score"])


if __name__ == "__main__":
    unittest.main()
