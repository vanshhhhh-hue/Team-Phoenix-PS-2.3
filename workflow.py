"""Explicit workflow transitions, atomic submissions and assistance tracking."""
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from engine import evaluate, find_counterexample, pack_by_id, question_by_id, require
from ledger import ensure_record, event, record_event, stamp, transfer_outcome


def new_lab(family_id):
    return {'family_id': family_id, 'stage': 'PREDICT', 'session_id': str(uuid4()),
            'token': str(uuid4()), 'consumed_tokens': [], 'pending_answer': None,
            'evidence': None, 'candidate': False, 'test_result': None, 'help_counts': {},
            'transfer_results': [], 'transfer_index': 0, 'feedback': None}


def current_question(lab, content):
    pack = pack_by_id(content, lab['family_id'])
    stage = lab['stage']
    field = {'PREDICT': 'diagnostic_question_id', 'SELECT_REASON': 'diagnostic_question_id',
             'PROBE': 'probe_question_id', 'REPAIR_RULE': 'repair_question_id'}.get(stage)
    if field:
        return question_by_id(content, pack[field])
    if stage == 'TRANSFER':
        return question_by_id(content, pack['transfer_question_ids'][lab['transfer_index']])
    return None


def request_help(lab, content):
    require(lab['stage'] in ('PROBE', 'REPAIR_RULE', 'TRANSFER'), 'Help is not available in this stage.',
            'invalid_transition')
    updated = deepcopy(lab)
    q = current_question(lab, content)
    updated['help_counts'][q['id']] = min(updated['help_counts'].get(q['id'], 0) + 1, 3)
    return updated


def _attempt(lab, q, response, token, now, progress, reason=None):
    selected = response.get('selected_option_id')
    require(selected in {o['id'] for o in q['options']}, 'Choose one of the available answers.')
    assisted = lab['help_counts'].get(q['id'], 0) > 0
    # A retry of an already graded transfer item is practice, not a new unassisted test.
    if q['role'] == 'transfer' and any(a['question_id'] == q['id'] for a in progress['attempts']):
        assisted = True
    attempt = {'attempt_id': token, 'question_id': q['id'], 'selected_option_id': selected,
               'reason_id': reason, 'context': q['role'], 'help_used': assisted,
               'submitted_at': stamp(now), 'session_id': lab['session_id']}
    progress['attempts'].append(attempt)
    return attempt


def submit_response(state, response, token, now, progress, content):
    """Return (lab, progress); failures never mutate either input."""
    if token in state['consumed_tokens'] or any(a['attempt_id'] == token for a in progress['attempts']):
        return deepcopy(state), deepcopy(progress)
    require(token == state['token'], 'This form is stale. Use the current question.', 'invalid_transition')
    stamp(now)
    require(type(response) is dict, 'Invalid response.')
    lab, updated = deepcopy(state), deepcopy(progress)
    pack = pack_by_id(content, lab['family_id'])
    fid, stage = pack['id'], lab['stage']
    q = current_question(lab, content)
    lab['feedback'] = None

    if stage == 'PREDICT':
        selected = response.get('selected_option_id')
        require(selected in {o['id'] for o in q['options']}, 'Choose an answer before continuing.')
        lab['pending_answer'] = selected
        lab['stage'] = 'SELECT_REASON'
    elif stage in ('SELECT_REASON', 'PROBE'):
        reason = response.get('reason_id')
        require(reason in {r['id'] for r in pack['reason_options']}, 'Choose the reason behind your answer.')
        answer = lab['pending_answer'] if stage == 'SELECT_REASON' else response.get('selected_option_id')
        attempt = _attempt(lab, q, {'selected_option_id': answer}, token, now, updated, reason)
        matching = answer == pack['faulty_rule_id'] and reason == pack['faulty_rule_id']
        correct = answer == q['correct_option_id'] and reason == pack['correct_rule_id']
        record = ensure_record(updated, fid)
        if matching:
            lab.update(stage='TEST_RULE', evidence='Candidate rule supported by these choices', candidate=True)
            record['original_rule_id'] = pack['faulty_rule_id']
            status = 'candidate'
        elif correct:
            lab.update(stage='TRANSFER', evidence='Target misconception not observed in this response', candidate=False)
            status = 'unclear'
        elif stage == 'SELECT_REASON':
            lab.update(stage='PROBE', evidence='Mixed evidence — one more question', candidate=False)
            status = 'unclear'
        else:
            lab.update(stage='UNCLEAR', evidence='Cause unclear', candidate=False)
            status = 'unclear'
        # A new investigation invalidates a prior schedule but does not erase evidence.
        record['next_check_at'] = None
        record_event(updated, fid, event(token, 'diagnostic' if stage == 'SELECT_REASON' else 'probe',
                     status, now, attempt['attempt_id'], lab['evidence']))
    elif stage == 'UNCLEAR':
        require(response.get('action') == 'guided', 'Choose the guided example.', 'invalid_transition')
        lab['stage'] = 'TEST_RULE'
    elif stage == 'TEST_RULE':
        x = response.get('x')
        require(type(response.get('predict_equal')) is bool, 'Predict whether the results will agree.')
        original = evaluate(fid, 'original', pack['parameters'], x)
        faulty = evaluate(fid, 'faulty', pack['parameters'], x)
        lab['test_result'] = dict(x=x, original_value=original, rewritten_value=faulty,
                                  predict_equal=response['predict_equal'])
        record = ensure_record(updated, fid)
        record['counterexample'] = find_counterexample(fid, pack['parameters'])
        record_event(updated, fid, event(token, 'tested', 'tested' if lab['candidate'] else 'unclear', now,
                     note='Calculated a contrast; guided examples do not establish a personal diagnosis.'))
        lab['stage'] = 'INSPECT_CONTRADICTION'
    elif stage == 'INSPECT_CONTRADICTION':
        require(response.get('action') == 'repair', 'Continue to repair.', 'invalid_transition')
        lab['stage'] = 'REPAIR_RULE'
    elif stage == 'REPAIR_RULE':
        reason = response.get('reason_id')
        require(reason in (pack['correct_rule_id'], pack['faulty_rule_id']), 'Choose a structured explanation.')
        attempt = _attempt(lab, q, response, token, now, updated, reason)
        correct = (attempt['selected_option_id'] == q['correct_option_id'] and reason == pack['correct_rule_id'])
        record = ensure_record(updated, fid)
        if correct:
            record['repaired_rule_id'] = pack['correct_rule_id']
            record_event(updated, fid, event(token, 'repaired', 'repaired', now, token,
                         'Correct rule and explanation selected; three numerical regression checks agree.'))
            lab['stage'] = 'REPAIR_VERIFIED'
        else:
            record_event(updated, fid, event(token, 'repaired', record['status'], now, token,
                         'Repair still needs work; selected rule or explanation is incorrect.'))
            lab['feedback'] = 'The rule and explanation need another look. Try the hints or worked explanation.'
    elif stage == 'REPAIR_VERIFIED':
        require(response.get('action') == 'transfer', 'Continue to new problems.', 'invalid_transition')
        lab['stage'] = 'TRANSFER'
    elif stage == 'TRANSFER':
        attempt = _attempt(lab, q, response, token, now, updated)
        result = {'question_id': q['id'], 'correct': attempt['selected_option_id'] == q['correct_option_id'],
                  'help_used': attempt['help_used']}
        lab['transfer_results'].append(result)
        record = ensure_record(updated, fid)
        status = record['status']
        note = 'First transfer check recorded. The second check remains separate.'
        if len(lab['transfer_results']) == 2:
            note, passed = transfer_outcome(lab['transfer_results'])
            status = 'transfer_passed' if passed else ('repaired' if record['repaired_rule_id'] else 'unclear')
            if passed:
                record['next_check_at'] = stamp(now + timedelta(days=1))
        record_event(updated, fid, event(token, 'transfer', status, now, token, note))
        lab['stage'] = 'TRANSFER_FEEDBACK'
    elif stage == 'TRANSFER_FEEDBACK':
        require(response.get('action') == 'next', 'Continue to the next step.', 'invalid_transition')
        if len(lab['transfer_results']) == 1:
            lab['transfer_index'] = 1
            lab['stage'] = 'TRANSFER'
        else:
            lab['stage'] = 'LEDGER'
    else:
        require(False, 'No submission is available in this stage.', 'invalid_transition')

    lab['consumed_tokens'].append(token)
    lab['token'] = str(uuid4())
    return lab, updated
