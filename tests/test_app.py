"""End-to-end turns through app.handle(), with the simulated model. Logs go to a temp folder."""
import contextlib, datetime, io, json, os, sys, tempfile, unittest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app, tools

TEST_A = "Can two events be mutually exclusive and independent? Let P(A)=0.4 and P(B)=0.5."
TEST_B = "Are they independent? I don't have the numbers."


def turn(**payload):
    with contextlib.redirect_stdout(io.StringIO()):   # hide CONTEXT lines
        return app.handle(payload)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = lambda n: os.path.join(self.tmp.name, n)
        self.patches = [patch.object(app, "FEEDBACK_LOG", p("feedback.jsonl")),
                        patch.object(app, "CONTEXT_LOG", p("context.jsonl")),
                        patch.object(tools, "LOG", p("tool_log.jsonl")),
                        patch.object(tools, "SCHEDULE", p("schedule.json")),
                        patch.object(app, "today", lambda: datetime.date(2026, 11, 9))]
        for x in self.patches:
            x.start()
        app.LAST, app.PENDING_TOOL = {}, None

    def tearDown(self):
        for x in self.patches:
            x.stop()
        self.tmp.cleanup()

    def test_test_a_checked_with_sources_and_steps(self):
        d = turn(message=TEST_A)
        self.assertEqual("checked", d["status"])
        self.assertIn("I screened", d["cue_text"])
        self.assertIn("not the meaning", d["cue_text"])      # the cue must not overstate the check
        self.assertTrue(all(s["passage_id"] for s in d["sentences"]))
        ids = {e["id"] for e in d["evidence"]}
        self.assertTrue(all(s["passage_id"] in ids for s in d["sentences"]))
        self.assertIn("0.4 × 0.5 = 0.2", " ".join(d["steps"]))
        self.assertEqual([], d["removed"])
        self.assertIn("stale_note", d)                 # 2024 notes shown, labelled, not used

    def test_test_b_asks_instead_of_guessing(self):
        d = turn(message=TEST_B)
        self.assertEqual("clarify", d["status"])
        self.assertEqual([], d["sentences"])
        self.assertEqual(3, len(d["options"]))
        self.assertTrue(all("not checked against your events" in e["note"] for e in d["evidence"]))

    def test_clarify_choice_gives_conditional_answer(self):
        turn(message=TEST_B)
        d = turn(action="clarify", choice="exclusive_and_independent")
        self.assertEqual("depends", d["status"])
        self.assertIn("P(A) and P(B)", d["cue_text"])

    def test_correction_replaces_interpretation(self):
        turn(message=TEST_B)
        d = turn(action="correct", fields={"question_type": "independence",
                                           "values": {"P(A)": "0.3", "P(B)": "0.5", "P(A∩B)": "0.2"}})
        self.assertEqual(("checked", "not independent"), (d["status"], d["verdict"]))
        self.assertTrue(d["interpretation"]["corrected"])

    def test_overconfident_model_sentences_are_removed(self):
        d = turn(message=TEST_A, simulate_overclaim=True)
        self.assertEqual(2, len(d["removed"]))
        reasons = " ".join(r["why"] for r in d["removed"])
        self.assertIn("superseded", reasons)
        self.assertNotIn("always dependent", " ".join(s["text"] for s in d["sentences"]))

    def test_malformed_model_reply(self):
        with patch.dict(os.environ, {"IIS_MOCK_BREAK": "1"}):
            d = turn(message=TEST_A)
        self.assertEqual("error", d["status"])
        self.assertEqual([], d["sentences"])

    def test_out_of_scope_declines(self):
        d = turn(message="What is a Markov chain?")
        self.assertEqual("cannot_check", d["status"])
        self.assertIn("tutor", d["reply"])

    def test_impossible_values_ask_for_correction(self):
        d = turn(message="P(A)=1.4, P(B)=0.2. Are A and B independent?")
        self.assertEqual("invalid", d["status"])
        self.assertTrue(d["open_correction"])

    def test_report_is_logged_and_rechecked(self):
        turn(message=TEST_A)
        d = turn(action="report", index=2, reason="the notes don't mention 0.2")
        self.assertEqual("saved", d["report"]["status"])
        self.assertTrue(d["report"]["recheck"]["supported"])
        self.assertIn(0.2, d["report"]["recheck"]["numbers_from_calculation"])
        with open(app.FEEDBACK_LOG, encoding="utf-8") as f:
            self.assertEqual("r1", json.loads(f.readline())["id"])

    def test_slot_needs_confirmation_and_reports_tool_result(self):
        turn(message=TEST_A)
        p = turn(action="propose_slot")["tool"]
        self.assertEqual("awaiting_confirmation", p["status"])
        self.assertIn("Tue 10 Nov 2026", p["describe"])
        self.assertFalse(os.path.exists(tools.SCHEDULE))
        done = turn(action="confirm_slot")["tool"]
        self.assertEqual("ok", done["result"]["status"])
        self.assertTrue(os.path.exists(tools.SCHEDULE))

    def test_cancel_and_invalid_slot_do_not_run(self):
        turn(message=TEST_A)
        turn(action="propose_slot")
        self.assertEqual("cancelled", turn(action="cancel_slot")["tool"]["result"]["status"])
        self.assertFalse(os.path.exists(tools.SCHEDULE))
        ok, reason = tools.valid({"name": "book_slot", "arguments": {"date": "2026-11-10", "minutes": 900}})
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
