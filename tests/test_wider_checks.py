"""Regression tests for the rest of the third review round and for the wider testing before v1.4-a2.

Each case was reproduced first. The wider cases come from the harnesses in scripts/wide_tests/, which
compare ProbCheck with a ground truth it does not share (see README, Development record).
"""
import contextlib, io, json, os, sys, tempfile, unittest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app, parse


class WiderChecksTests(unittest.TestCase):
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

    def turn(self, message=None, **payload):
        if message is not None:
            payload = dict(action="ask", message=message, **payload)
        with contextlib.redirect_stdout(io.StringIO()):
            d = app.handle(payload)
        json.dumps(d, allow_nan=False)
        return d

    def answer(self, message):
        d = self.turn(message)
        return d["interpretation"]["question_type"], d["status"], d.get("verdict")

    # ---- reading the question ----
    def test_fractions_are_kept_exact(self):
        # rounding 1/3 to six decimals once made these 'not independent' (0.1667 ≠ 0.1667)
        self.assertEqual(("independence", "checked", "independent"),
                         self.answer("P(A)=1/3, P(B)=1/2, P(A∩B)=1/6. Are A and B independent?"))

    def test_question_asked_decides_the_type(self):
        cases = {
            "A and B are independent. P(A)=0.3, P(B)=0.4. Are A and B mutually exclusive?":
                ("exclusive", "checked", "not mutually exclusive"),
            "P(A)=0.7, P(B)=0.6. Are A and B mutually exclusive?": ("exclusive", "checked", "not mutually exclusive"),
            "P(A)=0.5, P(B)=0.6. Can A and B be mutually exclusive?": ("exclusive", "checked", "not mutually exclusive"),
            "P(A)=0.3, P(B)=0.4, P(A∩B)=0.12. Are A and B dependent?": ("independence", "checked", "independent"),
            "P(A)=0.3, P(B)=0.4, P(A∩B)=0.12. Is A independent of B?": ("independence", "checked", "independent"),
            "A and B are independent. Find P(A and B) if P(A)=0.2, P(B)=0.5.": ("intersection", "checked", "0.1"),
            "If A and B are independent with P(A)=0.3 and P(B)=0.4, what is P(A∪B)?": ("union", "checked", "0.58"),
        }
        for q, want in cases.items():
            self.assertEqual(want, self.answer(q), q)

    def test_given_values_do_not_make_a_conditional_question(self):
        # "given P(A)=..." once turned this into P(A|B) = 0.25; the question asks for P(A∪B)
        self.assertEqual(("union", "checked", "0.6"), self.answer(
            "What is the probability of A or B, given P(A)=0.3, P(B)=0.4, P(A and B)=0.1?"))
        self.assertEqual(("conditional", "checked", "0.4"), self.answer(
            "What is the probability of A given B if P(A∩B)=0.2 and P(B)=0.5?"))

    def test_lowercase_notation_names_the_events(self):
        d = self.turn("p(a)=0.3, p(b)=0.4, p(a∩b)=0.12. are a and b independent?")
        self.assertEqual("A and B", d["interpretation"]["events"])
        self.assertEqual(("checked", "independent"), (d["status"], d.get("verdict")))

    def test_other_events_are_not_swapped_for_a_and_b(self):
        for q in ("P(A)=0.3, P(B)=0.4, P(C)=0.5. Are A and C independent?",
                  "P(A∩B)=0.1, P(A)=0.3. What is P(B|A)?"):
            d = self.turn(q)
            self.assertEqual("cannot_check", d["status"], q)
            self.assertIsNone(d.get("verdict"), q)

    # ---- checking the numbers ----
    def test_derived_intersection_is_screened_without_removals(self):
        cases = {
            "P(A)=0.3, P(B)=0.4, P(A∪B)=0.7. Are A and B mutually exclusive?": "mutually exclusive",   # 0.3+0.4-0.7 is 5.6e-17
            "P(A)=0.3, P(B)=0.4, P(A∪B)=0.6. What is P(A|B)?": "0.25",
            "P(A)=0.3, P(B)=0.4, P(A|B)=0.25. What is P(A∪B)?": "0.6",
            "P(A)=0.0001, P(B)=0.0002. A and B are independent. What is P(A∩B)?": "2e-08",
        }
        for q, want in cases.items():
            d = self.turn(q)
            self.assertEqual(("checked", want), (d["status"], d.get("verdict")), q)
            self.assertEqual([], d["removed"], q)

    def test_value_given_for_the_asked_quantity_is_shown_back(self):
        d = self.turn("P(A)=0.4, P(A∩B)=0.1655, P(A|B)=0.8563. What is P(A|B)?")
        self.assertEqual(("checked", "0.8563"), (d["status"], d.get("verdict")))

    def test_impossible_value_sets_are_rejected(self):
        cases = [({"P(A∩B)": 0.7, "P(A∪B)": 0.2}, False, False),            # P(A∪B) < P(A∩B)
                 ({"P(A∩B)": 1, "P(A|B)": 0.9}, False, False),              # P(A|B) < P(A∩B)
                 ({"P(A)": 0.97, "P(A∩B)": 0.1, "P(A|B)": 0.61}, False, False),  # forces P(B) ≈ 0.16
                 ({"P(A)": 0, "P(A∪B)": 1, "P(A|B)": 1}, False, False),     # forces P(A∩B) = P(B) > 0 = P(A)
                 ({"P(A∩B)": 0.5, "P(A∪B)": 0.5}, False, True),             # independent: no P(A), P(B) fit
                 ({"P(A)": 1, "P(A|B)": 0.4}, False, True)]                 # independent: P(A|B) = P(A)
        for values, exclusive, independent in cases:
            self.assertTrue(parse.check_values(dict(values), exclusive, independent), values)

    def test_possible_value_sets_are_accepted(self):
        cases = [({"P(A)": 0.427443, "P(B)": 0.574565, "P(A|B)": 0.743942}, False, False),  # at a bound, rounded
                 ({"P(A∩B)": 0.25, "P(A∪B)": 0.75}, False, True),
                 ({"P(A)": 1 / 3, "P(B)": 1 / 3, "P(A∪B)": 0.6667}, True, False),
                 ({"P(A)": 0.4, "P(A∩B)": 0.1655, "P(A|B)": 0.8563}, False, False)]
        for values, exclusive, independent in cases:
            self.assertEqual([], parse.check_values(dict(values), exclusive, independent), values)

    def test_form_with_bad_values_field_does_not_crash(self):
        for fields in ({"question_type": "union", "values": "0.3"}, {"question_type": "union", "values": None},
                       {"question_type": "union", "values": {"P(A)": "1/0"}}, "not a dict"):
            d = self.turn(action="correct", fields=fields)
            self.assertIn(d["status"], ("depends", "invalid", "checked", "cannot_check"))


if __name__ == "__main__":
    unittest.main()
