"""Regression tests: values that cannot fit together must never be answered as 'checked'."""
import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app, parse


class ConsistencyTests(unittest.TestCase):
    def test_intersection_larger_than_marginal(self):
        # reported: P(A|B) = 2 was shown as "Checked against the notes"
        self.assertTrue(parse.parse("P(B)=0.2, P(A and B)=0.4. What is P(A|B)?")["problems"])
        r = app.handle({"action": "ask", "message": "P(B)=0.2, P(A and B)=0.4. What is P(A|B)?"})
        self.assertEqual("invalid", r["status"])

    def test_union_above_one(self):
        # reported: P(A∪B) = 1.4 was shown as checked
        i = parse.parse("P(A)=0.8, P(B)=0.7, P(A and B)=0.1. What is P(A or B)?")
        self.assertTrue(i["problems"])

    def test_form_uses_the_same_checks(self):
        # reported: the correction form accepted P(A∩B) = 0.25 > P(A) = 0.2
        i = parse.from_fields({"question_type": "independence",
                               "values": {"P(A)": "0.2", "P(B)": "0.3", "P(A∩B)": "0.25"}})
        self.assertTrue(i["problems"])

    def test_no_nan_reaches_the_page(self):
        for raw in ("P(A)=0.3, P(B)=0.4. Are A and B independent?", "abc", "1/0"):
            i = parse.from_fields({"question_type": "independence",
                                   "values": {"P(A)": "0.3", "P(B)": "0.4", "P(A∩B)": raw}})
            self.assertTrue(i["problems"])
            json.dumps(i, allow_nan=False)          # raises if NaN is still inside
        json.dumps(parse.parse("P(A and B)=1/0, P(B)=0.5. What is P(A|B)?"), allow_nan=False)

    def test_exclusive_with_nonzero_intersection(self):
        i = parse.from_fields({"question_type": "exclusive_and_independent",
                               "values": {"P(A)": "0.4", "P(B)": "0.5", "P(A∩B)": "0.2"}})
        self.assertTrue(i["problems"])

    def test_consistent_values_still_answered(self):
        self.assertEqual([], parse.parse("P(A)=0.3, P(B)=0.6, P(A and B)=0.18. Are A and B independent?")["problems"])
        self.assertEqual([], parse.parse("P(A)=0.4, P(B)=0.5. Can mutually exclusive events be independent?")["problems"])


if __name__ == "__main__":
    unittest.main()
