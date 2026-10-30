"""Run the actual Streamlit script and interact with its rendered widgets."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from engine import load_packs, pack_by_id
from ledger import export_progress, import_progress
from test_core import Journey, NOW

APP = Path(__file__).resolve().parents[1] / 'app.py'


class AppTests(unittest.TestCase):
    def app(self, family='distribution'):
        at = AppTest.from_file(str(APP), default_timeout=10)
        at.session_state['family'] = family
        return at.run()

    def button(self, at, label):
        next(b for b in at.button if b.label == label).click().run()
        self.assertEqual(len(at.exception), 0, str(list(at.exception)))

    def radio(self, at, label, value):
        next(r for r in at.radio if r.label == label).set_value(value)

    def stage(self, at, family='distribution'):
        return at.session_state['labs'][family]['stage']

    def complete(self, family):
        pack = pack_by_id(load_packs(), family)
        at = self.app(family)
        self.radio(at, 'Your answer', pack['faulty_rule_id']); self.button(at, 'Lock prediction →')
        self.radio(at, 'Why did you choose that answer?', pack['faulty_rule_id'])
        self.button(at, 'Test my reasoning →')
        at.number_input[0].set_value(1)
        self.radio(at, 'Will the original and rewrite have equal values?', 'They will agree')
        self.button(at, 'Run test →')
        self.assertEqual(self.stage(at, family), 'INSPECT_CONTRADICTION')
        expected = {'distribution': ('9', '5'), 'square': ('9', '5'), 'negative': ('-3', '1')}[family]
        self.assertEqual(tuple(m.value for m in at.metric), expected)
        at.slider[0].set_value(2).run()
        self.assertNotEqual(tuple(m.value for m in at.metric), expected)
        self.button(at, 'Repair the rule →')
        self.radio(at, 'Your answer', pack['correct_rule_id'])
        self.radio(at, 'Complete the explanation', pack['correct_rule_id'])
        self.button(at, 'Verify repair →')
        self.assertEqual(self.stage(at, family), 'REPAIR_VERIFIED')
        self.button(at, 'Try the Transfer Challenge →')
        self.assertEqual(at.session_state['navigation'], 'Transfer Challenge')
        self.radio(at, 'Your answer', 'correct'); self.button(at, 'Submit check →')
        # The first result must not teach the answer before the second check.
        self.assertFalse(any('Reviewed answer' in c.value for c in at.caption))
        self.button(at, 'Next: change of representation →')
        self.radio(at, 'Your answer', 'correct'); self.button(at, 'Submit check →')
        self.assertTrue(any(s.value == 'Transfer checks passed' for s in at.success))
        self.button(at, 'Save outcome to ledger →')
        self.assertEqual(at.session_state['navigation'], 'Repair Ledger')
        record = at.session_state['progress']['records'][0]
        self.assertEqual(record['status'], 'transfer_passed')
        self.assertEqual(record['family_id'], family)
        return at

    def test_complete_actual_ui_all_families(self):
        for family in ('distribution', 'square', 'negative'):
            with self.subTest(family=family):
                at = self.complete(family)
                self.assertEqual(len(at.exception), 0)

    def test_navigation_keeps_partial_lab_and_reset_clears_progress(self):
        at = self.app()
        self.radio(at, 'Your answer', 'multiply_first_only'); self.button(at, 'Lock prediction →')
        at.radio(key='navigation').set_value('Repair Ledger').run()
        at.radio(key='navigation').set_value('Debug Lab').run()
        self.assertEqual(self.stage(at), 'SELECT_REASON')
        self.button(at, 'Reset all progress')
        self.assertEqual(self.stage(at), 'PREDICT')
        self.assertEqual(at.session_state['progress']['records'], [])

    def test_invalid_form_preserves_stage_and_reports_error(self):
        at = self.app(); self.button(at, 'Lock prediction →')
        self.assertEqual(self.stage(at), 'PREDICT')
        self.assertTrue(at.error)
        self.assertFalse(at.session_state['progress']['attempts'])

    def test_unclear_actual_ui_has_guided_example(self):
        at = self.app()
        self.radio(at, 'Your answer', 'correct'); self.button(at, 'Lock prediction →')
        self.radio(at, 'Why did you choose that answer?', 'unsure'); self.button(at, 'Test my reasoning →')
        self.assertEqual(self.stage(at), 'PROBE')
        self.radio(at, 'Your answer', 'other'); self.radio(at, 'Why did you choose that answer?', 'unsure')
        self.button(at, 'Submit probe →')
        self.assertEqual(self.stage(at), 'UNCLEAR')
        self.button(at, 'Explore a guided example →')
        self.assertEqual(self.stage(at), 'TEST_RULE')
        self.assertTrue(any('not an inferred diagnosis' in i.value for i in at.info))

    def test_help_on_transfer_prevents_unassisted_gate(self):
        at = self.app()
        self.radio(at, 'Your answer', 'correct'); self.button(at, 'Lock prediction →')
        self.radio(at, 'Why did you choose that answer?', 'multiply_every_term')
        self.button(at, 'Test my reasoning →')
        self.assertEqual(self.stage(at), 'TRANSFER')
        self.button(at, 'Show next hint')
        self.radio(at, 'Your answer', 'correct'); self.button(at, 'Submit check →')
        self.button(at, 'Next: change of representation →')
        self.radio(at, 'Your answer', 'correct'); self.button(at, 'Submit check →')
        self.assertTrue(any('Assisted check' in w.value for w in at.warning))
        self.assertNotEqual(at.session_state['progress']['records'][0]['status'], 'transfer_passed')

    def test_future_preview_does_not_change_evidence_or_reveal_delayed_question(self):
        at = self.complete('distribution')
        before = deepcopy(at.session_state['progress'])
        next(c for c in at.checkbox if 'Preview a future' in c.label).check().run()
        self.assertEqual(before, at.session_state['progress'])
        self.assertTrue(any('actual delayed question stays hidden' in c.value for c in at.caption))
        self.assertEqual(import_progress(export_progress(before), load_packs()), before)

    def test_due_review_actual_ui_and_reopen(self):
        j = Journey(); j.complete()
        at = AppTest.from_file(str(APP), default_timeout=10)
        at.session_state['progress'] = j.progress
        at.session_state['navigation'] = 'Repair Ledger'
        with patch('ledger.clock', return_value=NOW + timedelta(days=1)):
            # app imports ledger.clock on each script run.
            at.run()
            self.radio(at, 'Review answer', 'other')
            self.radio(at, 'Review reasoning', 'multiply_every_term')
            self.button(at, 'Submit due review')
        self.assertEqual(at.session_state['progress']['records'][0]['status'], 'reopened')
        self.assertEqual(len(at.exception), 0)

    def test_no_network_needed_for_complete_journey(self):
        with patch('socket.create_connection', side_effect=OSError('Network unavailable')):
            self.complete('distribution')

    def test_ledger_hides_pending_transfer_grade_then_shows_both_answers(self):
        at = self.app()
        self.radio(at, 'Your answer', 'correct'); self.button(at, 'Lock prediction →')
        self.radio(at, 'Why did you choose that answer?', 'multiply_every_term')
        self.button(at, 'Test my reasoning →')
        self.radio(at, 'Your answer', 'correct'); self.button(at, 'Submit check →')
        at.radio(key='navigation').set_value('Repair Ledger').run()
        self.assertEqual(len(at.table), 0)
        self.assertTrue(any('Complete both checks' in c.value for c in at.caption))
        self.button(at, 'Continue recommended action →')
        self.assertEqual(at.session_state['navigation'], 'Transfer Challenge')
        self.button(at, 'Next: change of representation →')
        self.radio(at, 'Your answer', 'correct'); self.button(at, 'Submit check →')
        self.button(at, 'Save outcome to ledger →')
        self.assertEqual(len(at.table), 1)
        self.assertEqual(list(at.table[0].value['Selected answer']), ['5t + 15', '4y + 12'])


if __name__ == '__main__':
    unittest.main()
