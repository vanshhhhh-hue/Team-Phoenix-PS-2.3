from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import unittest
from uuid import uuid4

from engine import (DomainError, evaluate, find_counterexample, load_packs, pack_by_id,
                    question_by_id, validate_content)
from ledger import (MAX_IMPORT_BYTES, delayed_question, export_progress, get_record, import_progress,
                    new_progress, recommend_next, review, transfer_outcome)
from workflow import current_question, new_lab, request_help, submit_response

NOW = datetime(2026, 10, 30, 14, 30, tzinfo=timezone.utc)


class Journey:
    def __init__(self, family='distribution'):
        self.content = load_packs()
        self.pack = pack_by_id(self.content, family)
        self.lab = new_lab(family)
        self.progress = new_progress()
        self.now = NOW

    def send(self, **response):
        self.lab, self.progress = submit_response(self.lab, response, self.lab['token'], self.now,
                                                  self.progress, self.content)

    def diagnostic(self, answer=None, reason=None):
        self.send(selected_option_id=answer or self.pack['faulty_rule_id'])
        self.send(reason_id=reason or self.pack['faulty_rule_id'])

    def repair(self):
        self.diagnostic()
        self.send(x=1, predict_equal=True)
        self.send(action='repair')
        self.send(selected_option_id=self.pack['correct_rule_id'], reason_id=self.pack['correct_rule_id'])
        self.send(action='transfer')

    def transfer(self, choices=(True, True), assisted=False):
        for i, correct in enumerate(choices):
            q = current_question(self.lab, self.content)
            if assisted and i == 0:
                self.lab = request_help(self.lab, self.content)
            option = q['correct_option_id'] if correct else next(o['id'] for o in q['options'] if o['id'] != q['correct_option_id'])
            self.send(selected_option_id=option)
            self.send(action='next')

    def complete(self):
        self.repair(); self.transfer()
        return get_record(self.progress, self.pack['id'])


class EngineTests(unittest.TestCase):
    def test_reference_values_and_counterexample_order(self):
        expected = {'distribution': (9, 5, 0), 'square': (9, 5, 1), 'negative': (-3, 1, 0)}
        for pack in load_packs()['packs']:
            with self.subTest(pack=pack['id']):
                original, faulty, first = expected[pack['id']]
                self.assertEqual(evaluate(pack['id'], 'original', pack['parameters'], 1), original)
                self.assertEqual(evaluate(pack['id'], 'faulty', pack['parameters'], 1), faulty)
                self.assertEqual(find_counterexample(pack['id'], pack['parameters'])['x'], first)

    def test_correct_rule_regression_over_bounded_parameters(self):
        for fid in ('distribution', 'square', 'negative'):
            for b in range(-5, 6):
                for a in range(-5, 6):
                    params = {'a': a, 'b': b} if fid == 'distribution' else {'b': b}
                    for x in range(-5, 6):
                        self.assertEqual(evaluate(fid, 'original', params, x), evaluate(fid, 'correct', params, x))

    def test_matching_test_does_not_imply_equivalence(self):
        self.assertEqual(evaluate('square', 'original', {'b': 2}, 0), evaluate('square', 'faulty', {'b': 2}, 0))
        self.assertIsNotNone(find_counterexample('square', {'b': 2}))
        self.assertIsNone(find_counterexample('distribution', {'a': 1, 'b': 2}))

    def test_bounded_input_rejects_bools_strings_and_unknown_templates(self):
        for x in (True, 1.5, '1', 6, None):
            with self.assertRaises(DomainError):
                evaluate('distribution', 'original', {'a': 3, 'b': 2}, x)
        for params in ({'a': True, 'b': 2}, {'a': 3}, {'a': 3, 'b': 2, 'extra': 0}):
            with self.assertRaises(DomainError):
                evaluate('distribution', 'original', params, 1)
        with self.assertRaises(DomainError):
            evaluate('__import__', 'original', {}, 1)

    def test_content_validator_rejects_bad_keys_and_references(self):
        mutations = [lambda d: d['questions'][0].update(correct_option_id='missing'),
                     lambda d: d['questions'][1].update(id=d['questions'][0]['id']),
                     lambda d: d['packs'][0].update(probe_question_id='missing'),
                     lambda d: d['packs'][0]['parameters'].update(a=1),
                     lambda d: d['packs'][1]['parameters'].update(b=0),
                     lambda d: d['packs'][0].update(transfer_question_ids=['dist_1', 'dist_5']),
                     lambda d: d['packs'][0].update(hint_ids=['missing', 'missing'])]
        for mutate in mutations:
            d = load_packs(); mutate(d)
            with self.assertRaises(DomainError):
                validate_content(d)


class WorkflowTests(unittest.TestCase):
    def test_full_journey_all_families_and_roundtrip(self):
        for fid in ('distribution', 'square', 'negative'):
            with self.subTest(family=fid):
                j = Journey(fid); record = j.complete()
                self.assertEqual(j.lab['stage'], 'LEDGER')
                self.assertEqual(record['status'], 'transfer_passed')
                self.assertEqual(datetime.fromisoformat(record['next_check_at']), NOW + timedelta(days=1))
                self.assertEqual(len(j.progress['attempts']), 4)
                self.assertEqual(import_progress(export_progress(j.progress), j.content), j.progress)

    def test_correct_initial_answer_skips_diagnosis(self):
        j = Journey(); j.diagnostic('correct', j.pack['correct_rule_id'])
        self.assertEqual(j.lab['stage'], 'TRANSFER')
        self.assertIsNone(get_record(j.progress, 'distribution')['original_rule_id'])
        j.transfer()
        self.assertEqual(get_record(j.progress, 'distribution')['status'], 'transfer_passed')

    def test_conflicting_correct_answer_probes_and_unclear_guides(self):
        j = Journey(); j.diagnostic('correct', j.pack['faulty_rule_id'])
        self.assertEqual(j.lab['stage'], 'PROBE')
        j.send(selected_option_id='other', reason_id='unsure')
        self.assertEqual(j.lab['stage'], 'UNCLEAR')
        j.send(action='guided'); j.send(x=1, predict_equal=False)
        r = get_record(j.progress, 'distribution')
        self.assertEqual(r['status'], 'unclear')
        self.assertIsNone(r['original_rule_id'])

    def test_probe_can_support_candidate_or_correct_route(self):
        for correct in (False, True):
            j = Journey(); j.diagnostic('other', 'unsure')
            j.send(selected_option_id='correct' if correct else j.pack['faulty_rule_id'],
                   reason_id=j.pack['correct_rule_id'] if correct else j.pack['faulty_rule_id'])
            self.assertEqual(j.lab['stage'], 'TRANSFER' if correct else 'TEST_RULE')

    def test_duplicate_token_noop_and_stale_token_rejected(self):
        j = Journey(); j.send(selected_option_id=j.pack['faulty_rule_id'])
        token = j.lab['token']; j.send(reason_id=j.pack['faulty_rule_id'])
        lab, progress = submit_response(j.lab, {'reason_id': j.pack['faulty_rule_id']}, token,
                                        NOW, j.progress, j.content)
        self.assertEqual(lab, j.lab); self.assertEqual(progress, j.progress)
        with self.assertRaises(DomainError):
            submit_response(j.lab, {}, 'stale', NOW, j.progress, j.content)

    def test_invalid_submission_is_atomic(self):
        j = Journey(); before = deepcopy(j.lab)
        with self.assertRaises(DomainError):
            j.send(selected_option_id='unknown')
        self.assertEqual(j.lab, before)
        self.assertEqual(j.progress, new_progress())

    def test_repair_needs_correct_rule_and_reason(self):
        j = Journey(); j.diagnostic(); j.send(x=1, predict_equal=True); j.send(action='repair')
        j.send(selected_option_id=j.pack['correct_rule_id'], reason_id=j.pack['faulty_rule_id'])
        self.assertEqual(j.lab['stage'], 'REPAIR_RULE')
        self.assertIsNone(get_record(j.progress, 'distribution')['repaired_rule_id'])
        for _ in range(5):
            j.lab = request_help(j.lab, j.content)
        self.assertEqual(max(j.lab['help_counts'].values()), 3)
        j.send(selected_option_id=j.pack['correct_rule_id'], reason_id=j.pack['correct_rule_id'])
        self.assertEqual(j.lab['stage'], 'REPAIR_VERIFIED')
        self.assertTrue(j.progress['attempts'][-1]['help_used'])

    def test_transfer_outcomes_and_assistance_gate(self):
        for choices, assisted, expected in [((True, True), False, 'Transfer checks passed'),
                ((True, False), False, 'Repair needs transfer practice'),
                ((False, True), False, 'Repair needs practice'),
                ((True, True), True, 'Assisted check')]:
            j = Journey(); j.repair(); j.transfer(choices, assisted)
            label, passed = transfer_outcome(j.lab['transfer_results'])
            self.assertTrue(label.startswith(expected))
            self.assertEqual(get_record(j.progress, 'distribution')['status'] == 'transfer_passed', passed)

    def test_repeated_transfer_items_cannot_be_new_unassisted_evidence(self):
        j = Journey(); j.complete()
        j.lab = new_lab('distribution'); j.repair(); j.transfer()
        self.assertTrue(all(r['help_used'] for r in j.lab['transfer_results']))
        self.assertEqual(len(j.progress['records']), 1)
        self.assertGreater(len(j.progress['records'][0]['events']), 4)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey(); self.j.complete()

    def answer_review(self, now, correct=True, help_used=False):
        j = self.j; r = get_record(j.progress, 'distribution'); q = delayed_question(r, j.content)
        option = q['correct_option_id'] if correct else next(o['id'] for o in q['options'] if o['id'] != q['correct_option_id'])
        j.progress = review(j.progress, 'distribution', {'selected_option_id': option,
                            'reason_id': j.pack['correct_rule_id'], 'help_used': help_used},
                            str(uuid4()), now, j.content)
        return get_record(j.progress, 'distribution')

    def test_due_intervals_three_then_seven_and_import(self):
        now = NOW + timedelta(days=1)
        r = self.answer_review(now)
        self.assertEqual(datetime.fromisoformat(r['next_check_at']), now + timedelta(days=3))
        now += timedelta(days=3); r = self.answer_review(now)
        self.assertEqual(datetime.fromisoformat(r['next_check_at']), now + timedelta(days=7))
        now += timedelta(days=7); r = self.answer_review(now)
        self.assertEqual(r['successful_delayed_checks'], 3)
        self.assertEqual(import_progress(export_progress(self.j.progress), self.j.content), self.j.progress)

    def test_failed_or_assisted_due_review_reopens_and_recommends(self):
        for correct, helped in ((False, False), (True, True)):
            j = Journey(); j.complete(); self.j = j
            old = len(j.progress['records'][0]['events'])
            r = self.answer_review(NOW + timedelta(days=1), correct, helped)
            self.assertEqual(r['status'], 'reopened')
            self.assertIsNone(r['next_check_at'])
            self.assertGreater(len(r['events']), old)
            self.assertEqual(recommend_next(j.progress, NOW + timedelta(days=1))[0], 'distribution')

    def test_future_review_rejected_and_preview_noop(self):
        j = self.j; q = delayed_question(j.progress['records'][0], j.content)
        response = {'selected_option_id': q['correct_option_id'], 'reason_id': j.pack['correct_rule_id']}
        with self.assertRaises(DomainError):
            review(j.progress, 'distribution', response, 'early', NOW, j.content)
        self.assertEqual(review(j.progress, 'distribution', response, 'preview', NOW, j.content, preview=True), j.progress)

    def test_review_duplicate_submission_noop(self):
        j = self.j; q = delayed_question(j.progress['records'][0], j.content)
        response = {'selected_option_id': q['correct_option_id'], 'reason_id': j.pack['correct_rule_id']}
        p = review(j.progress, 'distribution', response, 'token', NOW + timedelta(days=1), j.content)
        self.assertEqual(review(p, 'distribution', response, 'token', NOW + timedelta(days=1), j.content), p)

    def test_recommendation_priority_and_empty(self):
        self.assertEqual(recommend_next(new_progress(), NOW)[0], 'distribution')
        self.assertEqual(recommend_next(self.j.progress, NOW)[0], 'square')
        self.assertEqual(recommend_next(self.j.progress, NOW + timedelta(days=1))[0], 'distribution')

    def test_malformed_imports_and_invariants(self):
        j = self.j
        mutations = [lambda d: d.update(schema_version=True),
            lambda d: d.update(secret='not permitted'),
            lambda d: d['attempts'].append(deepcopy(d['attempts'][0])),
            lambda d: d['attempts'][0].update(question_id='unknown'),
            lambda d: d['attempts'][0].update(help_used='false'),
            lambda d: d['attempts'][0].update(submitted_at='2026-10-30T12:00:00'),
            lambda d: d['records'][0].update(status='mastered'),
            lambda d: d['records'][0].update(successful_delayed_checks=True),
            lambda d: d['records'][0]['counterexample'].update(original_value=999),
            lambda d: d['records'][0]['attempt_ids'].append('missing'),
            lambda d: d['records'][0]['events'][0].update(attempt_id='missing'),
            lambda d: d['records'][0].update(next_check_at=None)]
        for mutation in mutations:
            data = deepcopy(j.progress); mutation(data)
            with self.assertRaises(DomainError):
                import_progress(json.dumps(data), j.content)
        for text in ('not json', '[]', '{}', '\ufeff{}', '[' * 1500, ' ' * (MAX_IMPORT_BYTES + 1)):
            with self.assertRaises(DomainError):
                import_progress(text, j.content)
        self.assertEqual(j.progress['records'][0]['status'], 'transfer_passed')


if __name__ == '__main__':
    unittest.main()
