"""Regression tests for the second round of reviews (v1.2-a2): each case below was reproduced first.

T1 implied P(A∩B) = 0 for mutually exclusive events; T2 a rounded result removed by the verifier;
T3 a given P(A∪B) that contradicts the other values; T4 the correction form dropping 'mutually
exclusive'; T5 infinity in the form; T6 a tiny product read as zero; plus negative values.
"""
import contextlib, io, json, os, sys, tempfile, unittest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app, checker, parse, verify


class ReviewRound2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(app, "FEEDBACK_LOG", os.path.join(self.tmp.name, "f.jsonl")),
                        patch.object(app, "CONTEXT_LOG", os.path.join(self.tmp.name, "c.jsonl"))]
        for x in self.patches:
            x.start()
        app.LAST = {}

    def tearDown(self):
        for x in self.patches:
            x.stop()
        self.tmp.cleanup()

    def turn(self, **payload):
        with contextlib.redirect_stdout(io.StringIO()):
            d = app.handle(payload)
        json.dumps(d, allow_nan=False)                 # the page must always receive valid JSON
        return d

    def test_t1_exclusive_sum_above_one_is_invalid_in_both_paths(self):
        d = self.turn(message="A and B are mutually exclusive. P(A)=0.8, P(B)=0.7. What is P(A∪B)?")
        self.assertEqual("invalid", d["status"])
        self.assertIn("P(A) + P(B) ≤ 1", " ".join(d["needs"]))
        d = self.turn(action="correct", fields={"question_type": "union", "mutually_exclusive": True,
                                                "values": {"P(A)": "0.8", "P(B)": "0.7"}})
        self.assertEqual("invalid", d["status"])

    def test_t1_exclusive_sum_within_one_still_answered(self):
        d = self.turn(message="A and B are mutually exclusive with P(A)=0.4 and P(B)=0.5. What is P(A∪B)?")
        self.assertEqual("checked", d["status"])
        self.assertEqual("0.9", d["verdict"])

    def test_t2_rounded_result_is_kept_and_marked_approximate(self):
        d = self.turn(message="P(A∩B)=0.1, P(B)=0.3. What is P(A|B)?")
        self.assertEqual("checked", d["status"])
        self.assertEqual([], d["removed"])
        self.assertIn("≈ 0.3333", d["steps"][0])
        self.assertTrue(any("0.3333" in s["text"] for s in d["sentences"]))

    def test_t2_rounding_is_the_only_tolerance(self):
        # 0.3333 is how the page shows 1/3; 0.33 is not, so it is still refused
        self.assertTrue(verify.number_allowed(0.3333, [1 / 3]))
        self.assertFalse(verify.number_allowed(0.33, [1 / 3]))

    def test_t3_given_union_must_match(self):
        d = self.turn(message="P(A)=0.4, P(B)=0.5, P(A∩B)=0.2, P(A∪B)=0.8. What is P(A∪B)?")
        self.assertEqual("invalid", d["status"])
        self.assertIn("does not match", " ".join(d["needs"]))
        d = self.turn(message="P(A)=0.4, P(B)=0.5, P(A∩B)=0.2, P(A∪B)=0.7. What is P(A∪B)?")
        self.assertEqual("checked", d["status"])

    def test_given_conditional_must_match(self):
        i = parse.parse("P(A∩B)=0.1, P(B)=0.4, P(A|B)=0.5. Is that right?")
        self.assertTrue(i["problems"])

    def test_t4_form_keeps_mutually_exclusive(self):
        d = self.turn(message="A and B are mutually exclusive with P(A)=0.4 and P(B)=0.5. What is P(A∪B)?")
        self.assertTrue(d["interpretation"]["mutually_exclusive"])
        # resubmitting the form unchanged (the page now sends the checkbox) keeps the meaning
        d = self.turn(action="correct", fields={"question_type": "union", "mutually_exclusive": True,
                                                "values": {"P(A)": "0.4", "P(B)": "0.5", "P(A∩B)": ""}})
        self.assertEqual("checked", d["status"])
        self.assertEqual("0.9", d["verdict"])

    def test_t5_infinity_and_division_by_zero_in_the_form(self):
        for raw in ("inf", "-inf", "1/0", "nan"):
            d = self.turn(action="correct", fields={"question_type": "conditional",
                                                    "values": {"P(B)": raw, "P(A∩B)": "0.1"}})
            self.assertEqual("invalid", d["status"])
            self.assertNotIn("P(B)", d["interpretation"]["values"])

    def test_t6_tiny_positive_probabilities_are_not_zero(self):
        d = self.turn(message="Can mutually exclusive events be independent? P(A)=0.000001, P(B)=0.000001.")
        self.assertEqual("not independent", d["verdict"])
        self.assertNotIn("0 = 0", " ".join(d["steps"]))
        self.assertEqual([], d["removed"])

    def test_negative_value_is_rejected_not_ignored(self):
        i = parse.parse("P(A)=-0.2, P(B)=0.5. Are A and B independent?")
        self.assertEqual(-0.2, i["values"]["P(A)"])
        self.assertTrue(i["problems"])

    def test_typed_division_by_zero_is_reported(self):
        i = parse.parse("P(A)=1/0, P(B)=0.5. Are A and B independent?")
        self.assertTrue(any("not a number" in p for p in i["problems"]))

    def test_fmt_and_eq(self):
        self.assertEqual(("0.3333", "≈"), (checker.fmt(1 / 3), checker.eq(1 / 3)))
        self.assertEqual(("0.3", "="), (checker.fmt(0.1 + 0.2), checker.eq(0.1 + 0.2)))
        self.assertEqual("1e-12", checker.fmt(1e-12))

    def test_full_context_is_logged(self):
        self.turn(message="P(A∩B)=0.1, P(B)=0.4. What is P(A|B)?")
        with open(app.CONTEXT_LOG, encoding="utf-8") as f:
            entry = json.loads(f.readline())
        self.assertEqual(4, len(entry["parts"]))
        self.assertIn("CHECKED FACTS", entry["parts"][2]["content"])


if __name__ == "__main__":
    unittest.main()
