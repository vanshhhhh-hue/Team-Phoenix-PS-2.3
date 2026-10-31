"""Five core questions, three attempts per item, fifteen questions at most."""
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
from engine import require

MAX_QUESTIONS = 15


def start_round(bank, concepts):
    require(len(concepts) == 5 and len(set(concepts)) == 5, 'Choose five distinct concepts.')
    queue = [next(q['id'] for q in bank if q['concept'] == concept) for concept in concepts]
    return dict(id=str(uuid4()), protocol_version=2, queue=queue, position=0, stage='answer', responses=[],
                started_at=datetime.now(timezone.utc).isoformat(), limit_reached=False)


def current_question(round_, bank):
    require(round_['stage'] != 'complete', 'This round is complete.')
    return next(q for q in bank if q['id'] == round_['queue'][round_['position']])


def respond(round_, bank, answer):
    require(round_['stage'] in ('answer', 'hint', 'approach'), 'This answer has already been submitted.')
    require(type(answer) is int and 0 <= answer < 4, 'Choose an answer first.')
    result = deepcopy(round_)
    question = current_question(result, bank)
    first = result['stage'] == 'answer'
    correct = answer == question['correct_index']
    attempt = sum(r['question_id'] == question['id'] for r in result['responses']) + 1
    require(attempt <= 3, 'All three attempts have been used.')
    result['responses'].append(dict(question_id=question['id'], concept=question['concept'], attempt=attempt,
        selected_index=answer, correct=correct, phase='first' if first else 'retry',
        at=datetime.now(timezone.utc).isoformat()))
    result['stage'] = 'feedback' if correct else {1:'hint', 2:'approach', 3:'solution'}[attempt]
    return result


def advance(round_, bank):
    require(round_['stage'] in ('feedback', 'solution'), 'Finish the current question first.')
    result = deepcopy(round_)
    question = current_question(result, bank)
    first = next(r for r in result['responses'] if r['question_id'] == question['id'] and r['phase'] == 'first')
    if not first['correct']:
        followup = next((q for q in bank if q['concept'] == question['concept'] and q['id'] not in result['queue']), None)
        if followup and len(result['queue']) < MAX_QUESTIONS:
            result['queue'].insert(result['position'] + 1, followup['id'])
        else:
            result['limit_reached'] = True
    result['position'] += 1
    result['stage'] = 'complete' if result['position'] == len(result['queue']) else 'answer'
    return result


def first_responses(round_):
    return [r for r in round_['responses'] if r['phase'] == 'first']


def upgrade_round(round_):
    """Keep a pre-upgrade session and offer the newly available third attempt."""
    if round_.get('protocol_version') == 2:return round_
    result=deepcopy(round_);result['protocol_version']=2
    if result['stage']=='solution':
        qid=result['queue'][result['position']]
        attempts=sum(r['question_id']==qid for r in result['responses'])
        if attempts==2:result['stage']='approach'
    return result
