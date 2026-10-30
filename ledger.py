"""Single-student evidence ledger, clock-based reviews and atomic JSON import."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

from engine import DomainError, FAMILIES, evaluate, pack_by_id, question_by_id, require

STATUSES = {'candidate', 'tested', 'repaired', 'transfer_passed', 'delayed_check_passed',
            'reopened', 'unclear'}
EVENT_KINDS = {'diagnostic', 'probe', 'tested', 'repaired', 'transfer', 'delayed'}
MAX_IMPORT_BYTES = 1024 * 1024
LOCAL_TZ = timezone(timedelta(hours=5, minutes=30))


def clock():
    return datetime.now(LOCAL_TZ)


def stamp(now):
    require(isinstance(now, datetime) and now.tzinfo is not None and now.utcoffset() is not None,
            'A timezone-aware clock is required.')
    return now.isoformat()


def new_progress():
    return {'schema_version': 1, 'attempts': [], 'records': []}


def get_record(progress, family_id):
    return next((r for r in progress['records'] if r['family_id'] == family_id), None)


def ensure_record(progress, family_id):
    record = get_record(progress, family_id)
    if record is None:
        record = {'record_id': str(uuid4()), 'family_id': family_id, 'status': 'unclear',
                  'original_rule_id': None, 'repaired_rule_id': None, 'counterexample': None,
                  'attempt_ids': [], 'events': [], 'next_check_at': None, 'successful_delayed_checks': 0}
        progress['records'].append(record)
    return record


def record_event(progress, family_id, event):
    record = ensure_record(progress, family_id)
    if any(e['event_id'] == event['event_id'] for e in record['events']):
        return record
    require(event['kind'] in EVENT_KINDS and event['details']['status'] in STATUSES,
            'Unsupported ledger event.')
    record['events'].append(deepcopy(event))
    record['status'] = event['details']['status']
    aid = event['attempt_id']
    if aid is not None and aid not in record['attempt_ids']:
        record['attempt_ids'].append(aid)
    return record


def event(event_id, kind, status, now, attempt_id=None, note=''):
    return {'event_id': event_id, 'kind': kind, 'occurred_at': stamp(now), 'attempt_id': attempt_id,
            'details': {'status': status, 'note': note}}


def transfer_outcome(results):
    require(len(results) == 2, 'Two transfer results are required.')
    if any(r['help_used'] for r in results):
        return 'Assisted check — try an unaided new problem later', False
    if not results[0]['correct']:
        return 'Repair needs practice', False
    if not results[1]['correct']:
        return 'Repair needs transfer practice', False
    return 'Transfer checks passed', True


def recommend_next(progress, now):
    stamp(now)
    records = {r['family_id']: r for r in progress['records']}
    for fid in FAMILIES:
        if fid in records and records[fid]['status'] == 'reopened':
            return fid, 'Reopen the debugger', 'Debug Lab'
    for fid in FAMILIES:
        if fid in records and records[fid]['status'] in ('candidate', 'tested', 'repaired', 'unclear'):
            return fid, 'Continue the unresolved repair', 'Debug Lab'
    for fid in FAMILIES:
        if fid in records and records[fid]['next_check_at'] and datetime.fromisoformat(records[fid]['next_check_at']) <= now:
            return fid, 'Complete the due retrieval check', 'Repair Ledger'
    for fid in FAMILIES:
        if fid not in records:
            return fid, 'Try a new rule family', 'Debug Lab'
    return None, 'All current checks complete. Come back when a review is due.', 'Repair Ledger'


def delayed_question(record, content):
    pack = pack_by_id(content, record['family_id'])
    ids = pack['delayed_question_ids']
    return question_by_id(content, ids[min(record['successful_delayed_checks'], len(ids) - 1)])


def review(progress, family_id, response, token, now, content, preview=False):
    """Grade a real due check; previews never write evidence. Returns a fresh progress value."""
    updated = deepcopy(progress)
    record = get_record(updated, family_id)
    require(record is not None, 'No repair is available for review.', 'invalid_transition')
    if any(a['attempt_id'] == token for a in updated['attempts']):
        return updated
    if preview:
        return updated
    require(record['status'] in ('transfer_passed', 'delayed_check_passed') and record['next_check_at']
            and now >= datetime.fromisoformat(record['next_check_at']),
            'This review is not due yet. A preview does not count.', 'invalid_transition')
    pack = pack_by_id(content, family_id)
    q = delayed_question(record, content)
    require(response.get('selected_option_id') in {o['id'] for o in q['options']}, 'Choose an answer.')
    require(response.get('reason_id') in {r['id'] for r in pack['reason_options']}, 'Choose a reason.')
    require(type(response.get('help_used', False)) is bool, 'Invalid help flag.')
    passed = (response['selected_option_id'] == q['correct_option_id']
              and response['reason_id'] == pack['correct_rule_id'] and not response.get('help_used', False))
    attempt = {'attempt_id': token, 'question_id': q['id'], 'selected_option_id': response['selected_option_id'],
               'reason_id': response['reason_id'], 'context': 'delayed',
               'help_used': response.get('help_used', False), 'submitted_at': stamp(now),
               'session_id': response.get('session_id', 'review')}
    updated['attempts'].append(attempt)
    if passed:
        record['successful_delayed_checks'] += 1
        interval = 3 if record['successful_delayed_checks'] == 1 else 7
        record['next_check_at'] = stamp(now + timedelta(days=interval))
    else:
        record['next_check_at'] = None
    status = 'delayed_check_passed' if passed else 'reopened'
    record_event(updated, family_id, event(token, 'delayed', status, now, token,
                 'Passed this delayed check.' if passed else 'Needs another repair; earlier evidence retained.'))
    return updated


def export_progress(progress):
    # Only the specified evidence collections cross the persistence boundary.
    return json.dumps({k: progress[k] for k in ('schema_version', 'attempts', 'records')},
                      ensure_ascii=False, indent=2)


def _date(value):
    require(isinstance(value, str) and len(value) <= 64, 'Invalid timestamp.', 'invalid_progress')
    date = datetime.fromisoformat(value)
    require(date.tzinfo is not None and date.utcoffset() is not None, 'Timestamp needs a timezone.', 'invalid_progress')
    return date


def _identifier(value):
    require(isinstance(value, str) and 0 < len(value) <= 100, 'Invalid identifier.', 'invalid_progress')


def import_progress(text, content):
    """Validate an entire export without touching the caller's current state."""
    try:
        require(isinstance(text, str), 'Import must be JSON text.', 'invalid_progress')
        require(len(text.encode('utf-8')) <= MAX_IMPORT_BYTES, 'Progress file exceeds 1 MiB.', 'oversized_progress')
        data = json.loads(text)
        require(type(data) is dict and set(data) == {'schema_version', 'attempts', 'records'},
                'Unexpected progress fields.', 'invalid_progress')
        require(type(data['schema_version']) is int and data['schema_version'] == 1,
                'Unsupported progress version.', 'invalid_progress')
        require(type(data['attempts']) is list and type(data['records']) is list,
                'Progress collections must be lists.', 'invalid_progress')
        qfamilies = {}
        for p in content['packs']:
            for qid in [p['diagnostic_question_id'], p['probe_question_id'], p['repair_question_id'],
                        *p['transfer_question_ids'], *p['delayed_question_ids']]:
                qfamilies[qid] = p['id']
        attempts = {}
        afields = {'attempt_id', 'question_id', 'selected_option_id', 'reason_id', 'context',
                   'help_used', 'submitted_at', 'session_id'}
        for a in data['attempts']:
            require(type(a) is dict and set(a) == afields, 'Invalid attempt fields.', 'invalid_progress')
            for key in ('attempt_id', 'session_id'):
                _identifier(a[key])
            require(a['attempt_id'] not in attempts, 'Duplicate attempt.', 'invalid_progress')
            q = question_by_id(content, a['question_id'])
            p = pack_by_id(content, qfamilies[q['id']])
            require(a['context'] == q['role'] and type(a['help_used']) is bool,
                    'Invalid attempt context or help flag.', 'invalid_progress')
            require(a['selected_option_id'] in {o['id'] for o in q['options']}, 'Unknown answer.', 'invalid_progress')
            if a['context'] in ('diagnostic', 'probe', 'repair', 'delayed'):
                require(a['reason_id'] in {r['id'] for r in p['reason_options']}, 'Unknown reason.', 'invalid_progress')
            else:
                require(a['reason_id'] is None, 'Unexpected transfer reason.', 'invalid_progress')
            _date(a['submitted_at'])
            attempts[a['attempt_id']] = a
        fids, rids, eids, linked = set(), set(), set(), set()
        rfields = {'record_id', 'family_id', 'status', 'original_rule_id', 'repaired_rule_id',
                   'counterexample', 'attempt_ids', 'events', 'next_check_at', 'successful_delayed_checks'}
        for r in data['records']:
            require(type(r) is dict and set(r) == rfields, 'Invalid record fields.', 'invalid_progress')
            _identifier(r['record_id'])
            p = pack_by_id(content, r['family_id'])
            require(r['family_id'] not in fids and r['record_id'] not in rids, 'Duplicate record.', 'invalid_progress')
            fids.add(r['family_id']); rids.add(r['record_id'])
            require(r['status'] in STATUSES, 'Unknown status.', 'invalid_progress')
            require(r['original_rule_id'] in (None, p['faulty_rule_id'])
                    and r['repaired_rule_id'] in (None, p['correct_rule_id']), 'Unknown rule.', 'invalid_progress')
            require(type(r['successful_delayed_checks']) is int and r['successful_delayed_checks'] >= 0,
                    'Invalid review count.', 'invalid_progress')
            require(type(r['attempt_ids']) is list and type(r['events']) is list and r['events'],
                    'Record needs attempts and events.', 'invalid_progress')
            require(len(set(r['attempt_ids'])) == len(r['attempt_ids']), 'Duplicate attempt link.', 'invalid_progress')
            for aid in r['attempt_ids']:
                require(aid in attempts and qfamilies[attempts[aid]['question_id']] == r['family_id']
                        and aid not in linked, 'Invalid attempt link.', 'invalid_progress')
                linked.add(aid)
            c = r['counterexample']
            if c is not None:
                require(type(c) is dict and set(c) == {'x', 'original_value', 'rewritten_value'}
                        and all(type(v) is int for v in c.values()), 'Invalid counterexample.', 'invalid_progress')
                require(c['original_value'] == evaluate(p['id'], 'original', p['parameters'], c['x'])
                        and c['rewritten_value'] == evaluate(p['id'], 'faulty', p['parameters'], c['x'])
                        and c['original_value'] != c['rewritten_value'], 'Counterexample does not calculate.', 'invalid_progress')
            event_attempts, passed_count = set(), 0
            previous = None
            for e in r['events']:
                require(type(e) is dict and set(e) == {'event_id', 'kind', 'occurred_at', 'attempt_id', 'details'},
                        'Invalid event.', 'invalid_progress')
                _identifier(e['event_id'])
                require(e['event_id'] not in eids and e['kind'] in EVENT_KINDS, 'Duplicate or unknown event.', 'invalid_progress')
                eids.add(e['event_id'])
                at = _date(e['occurred_at'])
                require(previous is None or at >= previous, 'Events are out of order.', 'invalid_progress')
                previous = at
                d = e['details']
                require(type(d) is dict and set(d) == {'status', 'note'} and d['status'] in STATUSES
                        and isinstance(d['note'], str) and len(d['note']) <= 2000, 'Invalid event details.', 'invalid_progress')
                if e['attempt_id'] is not None:
                    require(e['attempt_id'] in r['attempt_ids'], 'Unknown event attempt.', 'invalid_progress')
                    event_attempts.add(e['attempt_id'])
                    require(at == _date(attempts[e['attempt_id']]['submitted_at']), 'Event time mismatch.', 'invalid_progress')
                if e['kind'] == 'delayed' and d['status'] == 'delayed_check_passed':
                    passed_count += 1
            require(event_attempts == set(r['attempt_ids']) and passed_count == r['successful_delayed_checks'],
                    'Inconsistent evidence links or review count.', 'invalid_progress')
            require(r['events'][-1]['details']['status'] == r['status'], 'Current status differs from history.', 'invalid_progress')
            scheduled = r['status'] in ('transfer_passed', 'delayed_check_passed')
            require(scheduled == (r['next_check_at'] is not None), 'Schedule inconsistent with status.', 'invalid_progress')
            if scheduled:
                require(_date(r['next_check_at']) > previous, 'Review schedule must follow its event.', 'invalid_progress')
        require(linked == set(attempts), 'Unlinked attempts.', 'invalid_progress')
        return data
    except DomainError as exc:
        if exc.code == 'oversized_progress':
            raise
        raise DomainError('invalid_progress', str(exc)) from exc
    except (ValueError, KeyError, TypeError, OverflowError, RecursionError) as exc:
        raise DomainError('invalid_progress', 'Malformed progress JSON. Current progress was preserved.') from exc
