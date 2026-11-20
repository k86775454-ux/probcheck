"""Regression tests for the third round of reviews (v1.3-a2); each case was reproduced first.

C1 'not mutually exclusive' was read as mutually exclusive, giving a wrong P(A∪B) = 0.9;
C2 a stated 'mutually exclusive' was not used for P(A|B); B1 the correction form had no field for
P(A∪B) or P(A|B), so resubmitting it silently dropped a value that contradicted the others.
"""
import contextlib, io, json, os, sys, tempfile, unittest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app, parse

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ReviewRound3Tests(unittest.TestCase):
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
        json.dumps(d, allow_nan=False)
        return d

    def test_c1_negated_exclusive_is_not_assumed(self):
        for q in ("A and B are not mutually exclusive. P(A)=0.4, P(B)=0.5. What is P(A∪B)?",
                  "A and B aren't mutually exclusive. P(A)=0.4, P(B)=0.5. What is P(A∪B)?",
                  "A and B are not necessarily disjoint. P(A)=0.4, P(B)=0.5. What is P(A∪B)?"):
            d = self.turn(message=q)
            self.assertFalse(d["interpretation"]["mutually_exclusive"], q)
            self.assertIn("not mutually exclusive", d["interpretation"]["events"])
            self.assertEqual("depends", d["status"])             # P(A∪B) needs P(A∩B) here
            self.assertEqual(["P(A∩B)"], d["needs"])

    def test_c1_plain_exclusive_still_read(self):
        i = parse.parse("A and B are mutually exclusive. P(A)=0.4, P(B)=0.5. What is P(A∪B)?")
        self.assertTrue(i["mutually_exclusive"])
        i = parse.parse("Can mutually exclusive events be independent? They are not independent, I think.")
        self.assertTrue(i["mutually_exclusive"])                 # 'not independent' is not a negated exclusive

    def test_c2_exclusive_conditional_uses_zero_intersection(self):
        d = self.turn(message="A and B are mutually exclusive and P(B)=0.4. What is P(A|B)?")
        self.assertEqual("checked", d["status"])
        self.assertEqual("0", d["verdict"])
        self.assertEqual([], d["removed"])

    def test_b1_form_has_every_value_field(self):
        with open(os.path.join(HERE, "index.html"), encoding="utf-8") as f:
            html = f.read()
        self.assertIn('["P(A)","P(B)","P(A∩B)","P(A∪B)","P(A|B)"]', html)

    def test_b1_resubmitting_a_contradiction_stays_invalid(self):
        d = self.turn(message="P(A)=0.4, P(B)=0.5, P(A∩B)=0.2, P(A∪B)=0.8. What is P(A∪B)?")
        self.assertEqual("invalid", d["status"])
        vals = {"P(A)": "0.4", "P(B)": "0.5", "P(A∩B)": "0.2", "P(A∪B)": "0.8", "P(A|B)": ""}
        d = self.turn(action="correct", fields={"question_type": "union", "values": vals})
        self.assertEqual("invalid", d["status"])                 # unchanged form: still contradicts
        vals["P(A∪B)"] = "0.7"
        d = self.turn(action="correct", fields={"question_type": "union", "values": vals})
        self.assertEqual("checked", d["status"])                 # corrected by the student
        vals["P(A∪B)"] = ""
        d = self.turn(action="correct", fields={"question_type": "union", "values": vals})
        self.assertEqual("0.7", d["verdict"])                    # cleared: recalculated

    def test_b1_conditional_value_in_form_is_checked(self):
        vals = {"P(B)": "0.4", "P(A∩B)": "0.1", "P(A|B)": "0.5"}
        d = self.turn(action="correct", fields={"question_type": "conditional", "values": vals})
        self.assertEqual("invalid", d["status"])


if __name__ == "__main__":
    unittest.main()
