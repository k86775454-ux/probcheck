"""Cases from the final independent check (OpenAI Codex, on v1.4-a2), each reproduced first."""
import contextlib, io, json, os, sys, tempfile, unittest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app, parse


class ReviewRound5Tests(unittest.TestCase):
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

    def ask(self, message):
        return self.turn(action="ask", message=message)

    # A. "I" and "P" are events wherever only an event fits; elsewhere a pronoun and a probability
    def test_events_named_i_and_p(self):
        for q in ("P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Are I and B independent?",
                  "P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Is A independent of P?",
                  "P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Are A and I mutually exclusive",
                  "I and B are independent. P(A)=0.3. What is P(A∩B)?",
                  "What is the probability of I or B if P(B)=0.5?",
                  "Event P has probability 0.3. Is it independent of B?"):
            self.assertEqual("cannot_check", self.ask(q)["status"], q)
        for q in ("I think P(A)=0.3, P(B)=0.5 and P(A∩B)=0.15. Are A and B independent?",
                  "Can I check whether A and B are independent? P(A)=0.3, P(B)=0.5, P(A∩B)=0.15.",
                  "Are A and B independent? I have P(A)=0.3, P(B)=0.5, P(A∩B)=0.15"):
            d = self.ask(q)
            self.assertEqual(("checked", "independent"), (d["status"], d.get("verdict")), q)

    # B. a stated "dependent" is "not independent"; a stated "not dependent" is "independent"
    def test_stated_dependence(self):
        d = self.ask("A and B are dependent. P(A)=0.3, P(B)=0.4, P(A∩B)=0.12. What is P(A∪B)?")
        self.assertEqual("invalid", d["status"])
        self.assertIn("not independent", " ".join(d["needs"]))
        d = self.ask("A and B are dependent. P(A)=0.3, P(B)=0.4, P(A∩B)=0.2. What is P(A∪B)?")
        self.assertEqual(("checked", "0.5"), (d["status"], d.get("verdict")))
        d = self.ask("A and B are not dependent. P(A)=0.3, P(B)=0.4. What is P(A∩B)?")
        self.assertEqual(("checked", "0.12"), (d["status"], d.get("verdict")))
        # asked, "dependent" is the question, not a given
        for q in ("P(A)=0.3, P(B)=0.4, P(A∩B)=0.12. Are A and B dependent?",
                  "P(A)=0.3, P(B)=0.4, P(A∩B)=0.12. Is A dependent on B?"):
            d = self.ask(q)
            self.assertEqual(("checked", "independent"), (d["status"], d.get("verdict")), q)
        self.assertFalse(parse.parse("Are mutually exclusive events with P(A)=0 and P(B)=0.3 always dependent?")
                         ["problems"])

    # C. resubmitting the correction form keeps a stated "not ..." until the student unticks it
    def test_form_keeps_negated_premises(self):
        d = self.ask("A and B are not independent. P(A)=0.3, P(B)=0.4, P(A∩B)=0.12. What is P(A∪B)?")
        self.assertEqual("invalid", d["status"])
        i = d["interpretation"]
        self.assertTrue(i["not_independent"])
        fields = {"question_type": i["question_type"], "mutually_exclusive": i["mutually_exclusive"],
                  "independent": i["independent"], "not_mutually_exclusive": i["not_mutually_exclusive"],
                  "not_independent": i["not_independent"], "values": {k: repr(v) for k, v in i["values"].items()}}
        again = self.turn(action="correct", fields=fields)
        self.assertEqual("invalid", again["status"])
        self.assertIn("stated not independent", again["interpretation"]["events"])
        dropped = self.turn(action="correct", fields=dict(fields, not_independent=False))
        self.assertEqual(("checked", "0.58"), (dropped["status"], dropped.get("verdict")))
        both = self.turn(action="correct", fields=dict(fields, independent=True))
        self.assertIn("untick one", " ".join(both["needs"]))
        d = self.ask("A and B are not mutually exclusive. P(A)=0.3, P(B)=0.4, P(A∩B)=0. What is P(A∪B)?")
        i = d["interpretation"]
        fields = {"question_type": "union", "not_mutually_exclusive": i["not_mutually_exclusive"],
                  "values": {k: repr(v) for k, v in i["values"].items()}}
        self.assertEqual("invalid", self.turn(action="correct", fields=fields)["status"])
        # only true booleans count, so a crafted request cannot add a premise by accident
        self.assertEqual("checked", self.turn(action="correct", fields=dict(fields, not_mutually_exclusive="no"))["status"])


if __name__ == "__main__":
    unittest.main()
