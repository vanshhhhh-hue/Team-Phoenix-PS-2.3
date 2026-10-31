"""JEE Physics presentation selectors over disclosed synthetic profiles and live session work."""
from collections import Counter
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from engine import require

DATA_DIR = Path(__file__).resolve().parents[2] / 'samples/users/user-1/physics'
PAGES = ['Dashboard', 'Library', 'Quiz', 'Flash Cards', 'Insights', 'Teacher Dashboard']


def load_showcase():
    data = json.loads((DATA_DIR / 'showcase.json').read_text(encoding='utf-8'))
    require(data['version'] == 2 and len(data['students']) > 0, 'Invalid showcase data.')
    ids = [q['id'] for q in data['bank']]
    require(len(ids) == len(set(ids)), 'Duplicate practice items.')
    concepts = {c['id'] for c in data['chapters']}
    for q in data['bank']:
        require(q['concept'] in concepts and len(q['options']) == 4 and len(set(q['options'])) == 4
                and type(q['correct_index']) is int and 0 <= q['correct_index'] < 4, 'Invalid physics item.')
    for student in data['students']:
        for row in student['history']:
            q = next((q for q in data['bank'] if q['id'] == row['question_id']), None)
            require(q and row['concept'] == q['concept'] and row['correct'] == (row['selected_index'] == q['correct_index']), 'Invalid history reference.')
    return data


def student_report(data, student_id):
    person = next(p for p in data['students'] if p['id'] == student_id)
    history = person['history']
    topics = []
    for chapter in data['chapters']:
        rows = [r for r in history if r['concept'] == chapter['id']]
        n = len(rows); correct = sum(r['correct'] for r in rows)
        recent = rows[-5:]
        topics.append(dict(**chapter, attempted=n, correct=correct, accuracy=correct/n if n else None,
            recent_accuracy=sum(r['correct'] for r in recent)/len(recent) if recent else None,
            errors=n-correct, hints=sum(r.get('hint_used',False) for r in rows)))
    n = len(history)
    days = Counter(r['at'][:10] for r in history)
    trend = [dict(date=day, accuracy=round(100*sum(r['correct'] for r in history if r['at'].startswith(day))/count)) for day,count in sorted(days.items())]
    return dict(person=deepcopy(person),topics=topics,attempted=n,correct=sum(r['correct'] for r in history),
        accuracy=sum(r['correct'] for r in history)/n if n else 0,
        minutes=sum(r.get('minutes',0) for r in history),days=days,trend=trend,
        weak=sorted([t for t in topics if t['attempted']>=3],key=lambda t:t['accuracy']))


def confusion_report(data, student_id):
    person = next(p for p in data['students'] if p['id'] == student_id)
    bank = {q['id']:q for q in data['bank']}
    patterns = Counter()
    for row in person['history']:
        if not row['correct']:
            q=bank[row['question_id']]
            patterns[(row['concept'], q['error_labels'][str(row['selected_index'])])] += 1
    return [dict(concept=cid,pattern=pattern,count=count) for (cid,pattern),count in patterns.most_common()]


def record_response(data, student_id, round_id, response):
    result = deepcopy(data)
    history = next(s for s in result['students'] if s['id']==student_id)['history']
    identity = round_id + ':' + response['question_id']
    if response['phase']=='first':
        require(not any(r['id']==identity for r in history),'Answer already recorded.')
        history.append(dict(response,id=identity,hint_used=not response['correct'],minutes=2))
    else:
        original=next(r for r in history if r['id']==identity)
        original['hint_used']=True
        original['retry_correct']=response['correct']
        original.setdefault('support_attempts',[]).append(deepcopy(response))
        if not response['correct'] and response.get('attempt')==2:original['approach_used']=True
        if not response['correct'] and response.get('attempt')==3:original['solution_used']=True
    return result


def teaching_report(data, student_ids=None):
    """Transparent intervention priorities from first answers; retries never add grades."""
    from physics_teaching import TEACHING
    students=[s for s in data['students'] if student_ids is None or s['id'] in student_ids]
    reports=[student_report(data,s['id']) for s in students]
    bank={q['id']:q for q in data['bank']}
    topics=[];priorities=[]
    for chapter in data['chapters']:
        rows=[r for s in students for r in s['history'] if r['concept']==chapter['id']]
        correct=sum(r['correct'] for r in rows);n=len(rows)
        errors=n-correct
        affected=[];recent=[];patterns=Counter()
        for student in students:
            items=sorted([r for r in student['history'] if r['concept']==chapter['id']],key=lambda r:r['at'])
            recent.extend(items[-5:])
            if any(not r['correct'] for r in items):
                affected.append(dict(id=student['id'],name=student['name'],errors=sum(not r['correct'] for r in items)))
        for row in rows:
            if not row['correct']:patterns[bank[row['question_id']]['error_labels'][str(row['selected_index'])]]+=1
        topic=dict(**chapter,attempted=n,correct=correct,accuracy=correct/n if n else None,
                   errors=errors,hints=sum(r.get('hint_used',False) for r in rows),
                   affected=affected,patterns=[dict(pattern=p,count=c) for p,c in patterns.most_common()])
        topics.append(topic)
        if errors:
            recent_error=sum(not r['correct'] for r in recent)/len(recent) if recent else 0
            score=.6*(errors/n)+.25*(len(affected)/max(1,len(students)))+.15*recent_error
            content=TEACHING[chapter['id']]
            exposed={r['question_id'] for s in students for r in s['history']}
            candidates=[q for q in data['bank'] if q['concept']==chapter['id']]
            check=next((q for q in candidates if q['id'] not in exposed),candidates[0])
            priorities.append(dict(topic,score=score,recent_error=recent_error,
                counter=content['counter'],steps=content['plan'],
                exit_question=check['prompt'],exit_answer=check['solution'],
                exit_question_id=check['id'],exit_is_fresh=check['id'] not in exposed))
    priorities.sort(key=lambda t:(-t['score'],-t['errors'],t['title']))
    for rank,priority in enumerate(priorities,1):priority['rank']=rank
    history=[r for s in students for r in s['history']]
    return dict(students=students,reports=reports,topics=topics,priorities=priorities,
        attempted=len(history),correct=sum(r['correct'] for r in history),
        accuracy=sum(r['correct'] for r in history)/len(history) if history else 0,
        hint_support=sum(r.get('hint_used',False) for r in history),
        approach_support=sum(r.get('approach_used',False) for r in history),
        solution_support=sum(r.get('solution_used',False) for r in history))
