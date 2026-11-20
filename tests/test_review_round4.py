"""Cases from the fourth AI review (OpenAI Codex, on the first v1.4 patch), each reproduced first, and
from the testing that followed it."""
import contextlib, io, json, os, random, sys, tempfile, unittest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app, parse, tools


class ReviewRound4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(app, "FEEDBACK_LOG", os.path.join(self.tmp.name, "f.jsonl")),
                        patch.object(app, "CONTEXT_LOG", os.path.join(self.tmp.name, "c.jsonl")),
                        patch.object(tools, "LOG", os.path.join(self.tmp.name, "t.jsonl")),
                        patch.object(tools, "SCHEDULE", os.path.join(self.tmp.name, "s.json"))]
        for x in self.patches:
            x.start()
        app.LAST = {}

    def tearDown(self):
        for x in self.patches:
            x.stop()
        self.tmp.cleanup()

    def turn(self, message):
        with contextlib.redirect_stdout(io.StringIO()):
            d = app.handle({"action": "ask", "message": message})
        json.dumps(d, allow_nan=False)
        return d

    def status(self, message):
        d = self.turn(message)
        return d["status"], d.get("verdict")

    # 1. P(A|B) > 0 needs P(A∩B) > 0; no rounding allowance changes that
    def test_positive_conditional_with_a_zero(self):
        for q in ("P(A)=0, P(A|B)=0.5. What is P(A|B)?", "P(A∩B)=0, P(A|B)=0.5. What is P(A|B)?",
                  "A and B are mutually exclusive. P(A|B)=0.5. What is P(A∩B)?",
                  "P(A)=1, P(A|B)=0.4. What is P(A|B)?", "P(A∪B)=0, P(A|B)=0.5. What is P(A∩B)?"):
            self.assertEqual("invalid", self.turn(q)["status"], q)
        self.assertEqual(("checked", "0"), self.status("P(A)=0, P(A|B)=0. What is P(A|B)?"))

    # 2. rounding allowances never produce a probability outside [0, 1]
    def test_rounded_values_stay_in_range(self):
        # 0.9001 has four decimals, so it stands for at least 0.90005 > P(A) + P(B)
        self.assertEqual("invalid", self.turn("P(A)=0.4, P(B)=0.5, P(A∪B)=0.9001. What is P(A|B)?")["status"])
        self.assertEqual("invalid", self.turn("P(A)=0.5, P(B)=0.4, P(A∪B)=0.4999. What is P(A|B)?")["status"])
        d = self.turn("P(A)=1/3, P(B)=1/3, P(A∪B)=0.6667. Are A and B mutually exclusive?")
        self.assertEqual(("checked", "mutually exclusive"), (d["status"], d["verdict"]))
        self.assertIn("nearest possible value", " ".join(d["steps"]))
        # 0.667 stands for 2/3: P(A|B)P(B) = 0.3335 is just above P(A) = 1/3, so 1/3 is used
        self.assertEqual(("checked", "0.5"), self.status("P(A)=1/3, P(B)=0.5, P(A|B)=0.667. What is P(A∪B)?"))
        self.assertEqual("invalid", self.turn("P(A)=0.3, P(B)=0.4, P(A|B)=0.7502. What is P(A∪B)?")["status"])

    def test_every_numeric_answer_is_a_probability(self):
        random.seed(4)
        for _ in range(400):
            a, b = round(random.random(), 2), round(random.random(), 2)
            ab = random.uniform(max(0, a + b - 1), min(a, b))
            given = random.choice([("P(A∪B)", a + b - ab), ("P(A|B)", ab / b if b else 0)])
            text = "%.4f" % (given[1] + random.choice([-1, 0, 1]) * 4e-5)
            for ask in ("What is P(A|B)?", "What is P(A∪B)?", "What is P(A∩B)?"):
                d = self.turn("P(A)=%s, P(B)=%s, %s=%s. %s" % (a, b, given[0], text, ask))
                if d["status"] == "checked" and d.get("verdict") not in (None, "undefined"):
                    self.assertTrue(0 <= float(d["verdict"]) <= 1, (a, b, given, text, ask, d["verdict"]))

    # 3. small probabilities are not rounded away
    def test_small_probabilities(self):
        self.assertEqual(("checked", "not mutually exclusive"), self.status(
            "A and B are independent. P(A)=0.0000001, P(B)=0.0000001. Are A and B mutually exclusive?"))
        self.assertEqual(("checked", "not independent"), self.status(
            "P(A)=0.00000001, P(B)=0.00000001, P(A∩B)=0. Are A and B independent?"))
        self.assertEqual("invalid", self.turn("P(A)=1e-7, P(B)=1e-7, P(A∪B)=3e-7. What is P(A∪B)?")["status"])
        self.assertIn("too small", " ".join(self.turn("P(A)=1e-12, P(B)=0.5. Are A and B independent?")["needs"]))

    # 4. events other than A and B are never answered as A and B
    def test_other_event_names(self):
        for q in ("P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Are C and D independent?",
                  "P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Is A independent of C?",
                  "P(A)=0.3, P(I)=0.5. Are A and I independent?",
                  "P(A)=0.3, P(B)=0.5, P(A∩I)=0.15. Are A and B independent?",
                  "p(a)=0.3, p(b)=0.5, p(a∩b)=0.15. are c and d independent"):
            self.assertEqual("cannot_check", self.turn(q)["status"], q)
        # "I" as a pronoun and "a" as an article are not events
        self.assertEqual(("checked", "independent"), self.status(
            "I think P(A)=0.3, P(B)=0.5 and P(A∩B)=0.15. Are A and B independent?"))

    # 5. the question's word order, not the question mark, marks what is asked
    def test_question_without_question_mark(self):
        for q in ("A and B are independent. P(A)=0.3, P(B)=0.4. Are A and B mutually exclusive",
                  "A and B are independent. P(A)=0.3, P(B)=0.4. Are A and B mutually exclusive or not?"):
            d = self.turn(q)
            self.assertEqual("exclusive", d["interpretation"]["question_type"], q)
            self.assertEqual("not mutually exclusive", d.get("verdict"), q)

    # 6. a number is read whole or not at all
    def test_incomplete_numbers_are_reported(self):
        for q in ("P(A)=0.5/2, P(B)=0.5, P(A∩B)=0.125. Are A and B independent?",
                  "P(A)=0.3and P(B)=0.4. What is P(A∩B)?"):
            d = self.turn(q)
            self.assertEqual("invalid", d["status"], q)
            self.assertIn("couldn't read", " ".join(d["needs"]), q)
        self.assertEqual({"P(A∪B)": 0.2574, "P(A)": 0.06, "P(B)": 0.21, "P(A∩B)": 0.0126},
                         parse.parse("P(A)=6%, P(B)=21/100, P(A∩B)=1.26%, P(A∪B)=25.74%. Independent?")["values"])

    # 7. a stated "not ..." is checked against the values
    def test_negated_premises_are_checked(self):
        d = self.turn("A and B are not independent. P(A)=0.3, P(B)=0.4, P(A∩B)=0.12. What is P(A∪B)?")
        self.assertEqual("invalid", d["status"])
        d = self.turn("A and B are not mutually exclusive. P(A)=0.3, P(B)=0.4, P(A∩B)=0. What is P(A∪B)?")
        self.assertEqual("invalid", d["status"])
        # asked, the negation is the question, not a given
        self.assertEqual(("checked", "independent"), self.status(
            "P(A)=0.3, P(B)=0.4, P(A∩B)=0.12. Are A and B not independent?"))

    # 8. revision slots for different topics on the same day are both kept
    def test_slots_for_different_topics(self):
        call = {"name": "book_slot", "arguments": {"date": "2026-11-21", "minutes": 30, "topic": "Independence"}}
        first = tools.run(call)
        second = tools.run({"name": "book_slot", "arguments": dict(call["arguments"], topic="Conditional probability")})
        again = tools.run(call)
        self.assertTrue(first["id"] and second["id"])
        self.assertIsNone(again["id"])
        self.assertIn("already in your schedule", again["note"])


if __name__ == "__main__":
    unittest.main()
