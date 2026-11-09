"""Isolated deterministic tests for the final integrated app."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app
import retrieve
import tools


class Lab4Tests(unittest.TestCase):
    def tearDown(self):
        app.PENDING_TOOL = None

    def test_retrieval_source(self):
        d = app.turn('When is coursework 1 due?')
        self.assertIn('14 November at 12:00', d['reply'])
        self.assertEqual('Module Handbook 2026–27', d['evidence'][0]['source'])
        self.assertIn('score', d['evidence'][0])
        self.assertIn('date', d['evidence'][0])

    def test_stale_rule_does_not_override_current(self):
        d = app.turn('What is the late-submission penalty?')
        self.assertTrue(d['evidence'][0]['superseded'])
        self.assertIn('five marks per working day', d['reply'])
        self.assertIn('superseded', d['stale_warning'])

    def test_unanswerable_no_evidence(self):
        d = app.turn('Can I use an AI assistant for the project?')
        self.assertEqual([], d['evidence'])
        self.assertIsNone(d['action'])
        self.assertIn('module lead', d['reply'])

    def test_vlm_answer_and_refusal(self):
        good = app.turn('__poster__')
        bad = app.turn('__noticeboard__')
        self.assertEqual(0.86, good['image']['confidence'])
        self.assertTrue(bad['image']['refused'])
        self.assertNotIn('confidence', bad['image'])

    def test_validation_and_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(tools, 'LOG', os.path.join(tmp, 'tool_log.jsonl')), \
                 patch.object(tools, 'SCHEDULE', os.path.join(tmp, 'schedule.json')):
                invalid = app.turn('__invalid_tool__')
                self.assertEqual('refused', invalid['tool_result']['status'])
                self.assertNotIn('tool_confirmation', invalid)
                self.assertFalse(os.path.exists(tools.SCHEDULE))
                proposed = app.turn('book a revision slot')
                self.assertIn('2026', proposed['tool_confirmation'])
                self.assertFalse(os.path.exists(tools.SCHEDULE))
                result = app.turn('__confirm_tool__')
                self.assertEqual('ok', result['tool_result']['status'])
                self.assertTrue(os.path.exists(tools.SCHEDULE))
                import json
                with open(tools.LOG, encoding='utf-8') as file:
                    entries = [json.loads(s) for s in file]
                self.assertEqual([False, True], [e['confirmed'] for e in entries])

    def test_cancel_cannot_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(tools, 'LOG', os.path.join(tmp, 'log.jsonl')), \
                 patch.object(tools, 'SCHEDULE', os.path.join(tmp, 'schedule.json')):
                app.turn('book a revision slot')
                result = app.turn('__cancel_tool__')
                self.assertEqual('cancelled', result['tool_result']['status'])
                self.assertFalse(os.path.exists(tools.SCHEDULE))

    def test_malformed_mock_reply_fallback(self):
        with patch.dict(os.environ, {'IIS_MOCK_BREAK': '1'}):
            result = app.turn('when is coursework 1 due')
        self.assertIn('could not read', result['reply'])
        self.assertEqual([], result['options'])
        self.assertIsNone(result['action'])

    def test_invalid_calendar_date(self):
        ok, reason = tools.valid({'name':'book_slot', 'arguments': {'date':'2026-02-30','minutes':90}})
        self.assertFalse(ok)
        self.assertIn('valid calendar date', reason)


if __name__ == '__main__':
    unittest.main()
