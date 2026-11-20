"""Regression tests from the second wider-testing pass before v1.4-a2: notation, number formats,
answers that follow from the bounds, and odd requests to the server. Each case was reproduced first.
"""
import contextlib, io, json, os, sys, tempfile, threading, unittest, urllib.error, urllib.request
from http.server import HTTPServer
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app


class MoreInputsTests(unittest.TestCase):
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

    # ---- numbers and notation ----
    def test_decimal_comma_is_not_read_as_zero(self):
        # 0,3 was read as 0, and all-zero values were then "checked: independent"
        d = self.turn("P(A)=0,3, P(B)=0,4, P(A∩B)=0,12. Are A and B independent?")
        self.assertEqual("invalid", d["status"])
        self.assertIn("decimal", " ".join(d["needs"]))

    def test_other_number_formats(self):
        for q in ("P(A)=30 percent, P(B)=40 percent, P(A∩B)=12 percent. Are A and B independent?",
                  "P(A) equals 0.3, P(B) equals 0.4, P(A∩B) equals 0.12. Are A and B independent?",
                  "P(A)=3e-1, P(B)=4e-1, P(A∩B)=1.2e-1. Are A and B independent?"):
            d = self.turn(q)
            self.assertEqual({"P(A)": 0.3, "P(B)": 0.4, "P(A∩B)": 0.12},
                             {k: round(x, 12) for k, x in d["interpretation"]["values"].items()}, q)
            self.assertEqual(("checked", "independent"), (d["status"], d.get("verdict")), q)

    def test_other_notation(self):
        for q in ("Pr(A)=0.3, Pr(B)=0.4, Pr(A∩B)=0.12. Are A and B independent?",
                  "P(A ⋂ B)=0.12, P(A)=0.3, P(B)=0.4. Are A and B independent?",
                  "P(A intersect B)=0.12, P(A)=0.3, P(B)=0.4. Independent?"):
            self.assertEqual(("independence", "checked", "independent"), self.answer(q), q)
        self.assertEqual(("intersection", "checked", "0.2"),
                         self.answer("P(A union B)=0.5, P(A)=0.3, P(B)=0.4. What is P(A∩B)?"))
        self.assertEqual(("intersection", "checked", "0.15"), self.answer("P(A|B)=0.3, P(B)=0.5. P(A∩B)=?"))

    def test_a_value_given_twice(self):
        d = self.turn("P(A)=0.3, P(A)=0.4, P(B)=0.5. What is P(A∪B)?")
        self.assertEqual("invalid", d["status"])
        self.assertIn("more than once", " ".join(d["needs"]))
        self.assertEqual("checked", self.turn("P(A)=0.3, P(A)=0.3, P(B)=0.2, P(A∩B)=0.1. What is P(A∪B)?")["status"])

    def test_complements_and_reversed_conditionals_are_declined(self):
        for q in ("P(A')=0.7, P(B)=0.4. A and B are independent. What is P(A∩B)?",
                  "P(B|A)=0.5, P(A)=0.4. What is P(A∩B)?", "P(A^c)=0.7. What is P(A)?"):
            d = self.turn(q)
            self.assertEqual("cannot_check", d["status"], q)

    def test_bare_and_dependent_questions(self):
        self.assertEqual(("independence", "checked", "independent"),
                         self.answer("P(A)=0.3, P(B)=0.4, P(A∩B)=0.12. Independent?"))
        self.assertEqual("exclusive_and_independent", self.answer("Are mutually exclusive events always dependent?")[0])

    # ---- answers that follow from the bounds or a premise ----
    def test_bounds_decide_when_a_probability_is_0_or_1(self):
        cases = {"P(A)=0, P(B)=0.5. Are A and B independent?": "independent",
                 "P(A)=1, P(B)=0.4. Are A and B independent?": "independent",
                 "P(A)=1, P(B)=0.4. What is P(A∪B)?": "1",
                 "P(A)=1, P(B)=0.4. What is P(A|B)?": "1"}
        for q, want in cases.items():
            d = self.turn(q)
            self.assertEqual(("checked", want), (d["status"], d.get("verdict")), q)
            self.assertEqual([], d["removed"], q)

    def test_conditional_edge_cases(self):
        cases = {"P(A)=0.3, P(B)=0. What is P(A|B)?": ("checked", "undefined"),
                 "P(A)=0.3. What is P(A|B) if A and B are independent?": ("checked", "0.3"),
                 "A and B are mutually exclusive. What is P(A|B)?": ("checked", "0"),
                 "P(A)=0.3. What is P(A|B)?": ("depends", None),       # was "checked" with no answer
                 "What is P(A|B)?": ("checked", None)}                  # no numbers: the definition
        for q, want in cases.items():
            d = self.turn(q)
            self.assertEqual(want, (d["status"], d.get("verdict")), q)

    # ---- the server ----
    def test_odd_request_fields_do_not_raise(self):
        for payload in ({"action": "report", "index": None}, {"action": "report", "index": [1]},
                        {"action": "report", "index": float("inf")},
                        {"action": "correct", "fields": {"question_type": ["union"]}},
                        {"action": "correct", "fields": {"question_type": {"a": 1}}}):
            self.turn(**payload)

    def test_server_error_is_reported_not_dropped(self):
        server = HTTPServer(("127.0.0.1", 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = "http://127.0.0.1:%d/" % server.server_address[1]
            with patch.object(app, "handle", side_effect=RuntimeError("boom")), \
                    contextlib.redirect_stderr(io.StringIO()):
                req = urllib.request.Request(url, data=b'{"action": "ask", "message": "x"}',
                                             headers={"Content-Type": "application/json"})
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req, timeout=5)
            self.assertEqual(500, ctx.exception.code)
            self.assertIn("error", json.loads(ctx.exception.read()))
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
