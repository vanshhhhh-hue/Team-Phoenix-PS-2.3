"""Read-only material facade and evidence reporting; never writes learner records."""
from collections import defaultdict
from datetime import datetime
import nlm
import debugger
from learning_events import normalize_evidence
from ledger import clock

NLM_ID = 'authored:nlm-jee-2026'
# Explicit reversible presentation mapping for the inspected legacy demo, not a title heuristic.
HISTORICAL_DOCUMENTS = frozenset({('f0aee84a0c1ad096280d81c8', '2026-10-30T22:52:08.280754+05:30')})
NAVIGATION = ['Dashboard', 'Library', 'Quiz', 'Flash Cards', 'Insights']


def materials(state):
    result = [dict(id=NLM_ID, kind='authored', title="Newton's Laws of Motion (NLM)",
                   visibility='active', version=1, available=True)]
    result.extend(dict(id=d['id'], kind='uploaded', title=d['title'], version=1,
                       visibility='history' if (d['id'],d['created_at']) in HISTORICAL_DOCUMENTS else 'active',
                       available=True) for d in state['documents'])
    for row in result:
        meta=state.get('material_meta',{}).get(row['id'],{})
        row['title']=meta.get('title') or row['title']
        row['visibility']=meta.get('visibility',row['visibility'])
    return result


def navigation(value):
    return {'Revision': 'Flash Cards', 'Newton’s Laws': 'Library', 'Debugger': 'Quiz'}.get(value, value) if value in NAVIGATION + ['Revision', 'Newton’s Laws', 'Debugger'] else 'Dashboard'


def report(state, material_id=None, now=None, since=None, topic_ids=None):
    now = now or clock()
    rows = normalize_evidence(state, before=now)
    episodes = {e['id']: e for e in state['debugger']['episodes'] if e['learner']=='My learning'}
    def material(r):
        if r['origin']=='study':
            return next(d['id'] for d in state['documents'] if any(q['id']==r['question'] for q in d['questions']))
        if r['origin']=='newton': return NLM_ID
        ep=episodes[r['episode']]
        return ep['origin']['document_id'] if ep['origin'] else NLM_ID
    rows=[dict(r, material_id=material(r)) for r in rows]
    if material_id: rows=[r for r in rows if r['material_id']==material_id]
    if since: rows=[r for r in rows if datetime.fromisoformat(r['at'])>=since]
    if topic_ids: rows=[r for r in rows if r['skill'] in topic_ids]
    excluded=sum(r['question'] in state['item_status'] for r in rows)
    first=[r for r in rows if not r['repeat'] and r['role'] in ('primary','practice') and r['question'] not in state['item_status']]
    topics=defaultdict(list)
    for r in first: topics[r['skill']].append(r)
    topic_rows=[]
    for topic, events in topics.items():
        correct=sum(r['correct'] for r in events); n=len(events)
        topic_rows.append(dict(topic_id=topic,topic=topic_label(state,topic), correct=correct, attempted=n, accuracy=correct/n,
                               assisted=sum(r['helped'] for r in events),
                               status='insufficient evidence' if n<3 else 'needs practice' if correct/n<.7 else 'maintain'))
    cards=[c for c in state['cards'] if material_id in (None,c['document_id'])]
    due=card_queue(state,material_id,now=now)['due_count']
    repairs=[]
    for ep in episodes.values():
        mid=ep['origin']['document_id'] if ep['origin'] else NLM_ID
        if material_id and material_id!=mid: continue
        v=debugger.view(ep)
        repairs.append(dict(id=ep['id'], material_id=mid, date=ep['created_at'], status=v['repair_status'],
                            phase=v['phase'], due_at=v['due_at']))
    quizzes=[]
    for q in state['quizzes']:
        if material_id and q['document_id']!=material_id: continue
        if since and datetime.fromisoformat(q['created_at'])<since: continue
        attempts=[a for a in state['attempts'] if a['quiz_id']==q['id']]
        from study_flow import upload_activity_view
        recovery=upload_activity_view(state,q['id'])
        support=[__import__('study').practice_view(state,q['id'],a['question_id']) for a in attempts if not a['correct']]
        quizzes.append(dict(recovery_hints=sum(v['hints'] for v in support),recovery_retries=sum(len(v['retries']) for v in support),recovery_complete=recovery['recovery_complete'],id=q['id'], material_id=q['document_id'], date=q['created_at'],
                            correct=sum(a['correct'] for a in attempts), attempted=len(attempts),
                            hints=sum(a['hint_count'] for a in attempts), completed=q['completed']))
    if material_id in (None,NLM_ID):
        for s in state['nlm']['sessions']:
            if s['learner']!='My learning' or (since and datetime.fromisoformat(s['created_at'])<since): continue
            v=nlm.view(s); rs=v['responses']
            quizzes.append(dict(recovery_hints=v['max_hints'],recovery_retries=max(0,len(v['responses'])-1),recovery_complete=v['step'] in ('COMPLETE','RECAP'),id=s['id'],material_id=NLM_ID,date=s['created_at'],
                                correct=int(rs[0]['correct']) if rs else 0, attempted=int(bool(rs)),
                                hints=v['max_hints'],completed=v['step'] in ('COMPLETE','RECAP')))
    checks={}
    for role in ('follow_up','transfer','delayed'):
        rr=[r for r in rows if r['role']==role and not r['repeat'] and r['question'] not in state['item_status']]
        checks[role]=dict(attempted=len(rr), correct=sum(r['correct'] and not r['helped'] for r in rr),
                          assisted=sum(r['helped'] for r in rr))
    nlm_pending=0
    if material_id in (None,NLM_ID):
        for session in state['nlm']['sessions']:
            if session['learner']!='My learning': continue
            v=nlm.view(session)
            if v['step'] not in ('COMPLETE','RECAP') or v['due_at']: nlm_pending+=1
    from study import practice_view
    solutions=0
    for a in state['attempts']:
        quiz=next(q for q in state['quizzes'] if q['id']==a['quiz_id'])
        if material_id not in (None,quiz['document_id']): continue
        if not a['correct'] and practice_view(state,a['quiz_id'],a['question_id'])['solution']: solutions+=1
    if material_id in (None,NLM_ID):
        solutions+=sum(nlm.view(s)['ever_solution'] for s in state['nlm']['sessions'] if s['learner']=='My learning')
    solutions+=sum(any(e['action']=='help' for e in episodes[r['id']]['events']) for r in repairs)
    return dict(events=rows, excluded=excluded, first=first, solutions=solutions, correct=sum(r['correct'] for r in first), attempted=len(first),
                topics=topic_rows, due_cards=due, repairs=repairs, quizzes=sorted(quizzes,key=lambda q:q['date'],reverse=True),
                checks=checks, retries=sum(r['repeat'] for r in rows), assisted=sum(r['helped'] for r in rows),
                pending=sum(t['status'] in ('unfinished','due') for t in pending_tasks(state,material_id=material_id,now=now)),
                upcoming=sum(t['status']=='upcoming' for t in pending_tasks(state,material_id=material_id,now=now)),
                new_cards=card_queue(state,material_id,now=now)['new_count'])


def card_queue(state,material_id=None,mode='due',now=None,learner='My learning'):
    """One disjoint queue definition for counts and actions across uploaded/authored cards."""
    from engine import require
    require(mode in ('due','new','preview'),'Unknown card view.')
    now=now or clock(); rows=[]
    if material_id!=NLM_ID:
        for c in state['cards']:
            if material_id is not None and c['document_id']!=material_id: continue
            if c['id'] in state['item_status']: continue
            rows.append(dict(c,material_id=c['document_id'],is_new=c['review_count']==0))
    if material_id in (None,NLM_ID):
        for c in nlm.load_pack()['flashcards']:
            rs=[r for r in state['nlm']['reviews'] if r['learner']==learner and r['card_id']==c['id']]
            rows.append(dict(c,material_id=NLM_ID,is_new=not rs,due_at=rs[-1]['due_at'] if rs else None,review_count=len(rs)))
    new=[c for c in rows if c['is_new']]
    due=[c for c in rows if not c['is_new'] and datetime.fromisoformat(c['due_at'])<=now]
    upcoming=[c for c in rows if not c['is_new'] and datetime.fromisoformat(c['due_at'])>now]
    return dict(items=rows if mode=='preview' else new if mode=='new' else due,
        new_count=len(new),due_count=len(due),upcoming_count=len(upcoming),
        next_due_at=min((c['due_at'] for c in upcoming),key=datetime.fromisoformat,default=None))


def pending_tasks(state,learner='My learning',material_id=None,now=None):
    from study_flow import upload_activity_view
    now=now or clock(); tasks=[]
    def add(kind,mid,aid,item,status,due,reason):
        tasks.append(dict(id=kind+':'+aid,kind=kind,material_id=mid,learner=learner,activity_id=aid,item_id=item,
            topic_id=None,status=status,due_at=due,reason_code=kind,reason_text=reason,evidence_ids=[],availability_reason=None,
            target=dict(page='Quiz',material_id=mid,learner=learner,activity_kind=kind,activity_id=aid)))
    if learner=='My learning':
        for q in state['quizzes']:
            if material_id not in (None,q['document_id']): continue
            v=upload_activity_view(state,q['id'])
            if not v['scoring_complete'] or not v['recovery_complete']:
                add('upload_quiz',q['document_id'],q['id'],v['current_question_id'],'unfinished',None,
                    'Continue your saved mistake recovery.' if not v['recovery_complete'] else 'Continue your unanswered questions.')
                tasks[-1]['reason_code']='recovery' if not v['recovery_complete'] else 'unanswered'
    if material_id in (None,NLM_ID):
        for s in state['nlm']['sessions']:
            if s['learner']!=learner: continue
            v=nlm.view(s)
            status='unfinished' if v['step'] not in ('COMPLETE','RECAP') else 'due' if v['due_at'] and datetime.fromisoformat(v['due_at'])<=now else 'upcoming'
            needed='continue' if v['step'] in ('FIRST_RESPONSE','SOLUTION','REMEDIATION') else 'delayed' if status=='due' else None
            if needed and nlm.eligible_check(state,s['id'],needed) is None:status='blocked'
            add('newton_session',NLM_ID,s['id'],v['question_id'],status,v['due_at'],
                'Continue your saved Newton activity.' if status=='unfinished' else 'Delayed reasoning check '+('is due.' if status=='due' else 'is scheduled for later.'))
            if status=='blocked':
                tasks[-1]['reason_text']='No unused check remains. Review the lesson or choose another concept.'
                tasks[-1]['availability_reason']='Reviewed question bank exhausted.'
                tasks[-1]['target']=dict(page='Library',material_id=NLM_ID,learner=learner,activity_kind='lesson',topic_id=nlm.question(s['question_id'])['concept_id'])
            elif v['step'] in ('HINT_1','HINT_2','SOLUTION','REMEDIATION'):tasks[-1]['reason_code']='recovery'
    for e in state['debugger']['episodes']:
        mid=e['origin']['document_id'] if e['origin'] else NLM_ID
        if e['learner']!=learner or material_id not in (None,mid): continue
        v=debugger.view(e)
        if v['phase']=='complete' and not v['due_at']: continue
        status='due' if v['due_at'] and datetime.fromisoformat(v['due_at'])<=now else 'upcoming' if v['phase']=='complete' else 'unfinished'
        add('repair',mid,e['id'],None,status,v['due_at'],'Continue your saved reasoning review.' if status=='unfinished' else 'Return for the scheduled reasoning check.')
    return sorted(tasks,key=lambda t:({'unfinished':0,'due':1,'upcoming':2,'blocked':3}[t['status']],0 if t['reason_code']=='recovery' else 1,t['due_at'] or '',t['id']))


def recommend_next(state,material_id,now=None):
    tasks=pending_tasks(state,material_id=material_id,now=now)
    actions=[t for t in tasks if t['status'] in ('unfinished','due')]
    blocked=[t for t in tasks if t['status']=='blocked']
    queue=card_queue(state,material_id,now=now)
    extra=[]
    if material_id==NLM_ID:
        for session in reversed(state['nlm']['sessions']):
            if session['learner']!='My learning':continue
            view=nlm.view(session)
            if view['step']=='COMPLETE' and view['transfer'] is None and nlm.eligible_check(state,session['id'],'transfer'):
                extra.append(dict(reason_text='Try a new situation: '+nlm.question(session['question_id'])['concept_id'].replace('_',' ').title(),target=dict(page='Quiz',material_id=NLM_ID,learner='My learning',activity_kind='newton_session',activity_id=session['id'])))
                break
    if queue['due_count']:
        actions.append(dict(reason_text=f"Review {queue['due_count']} due cards",target=dict(page='Flash Cards',material_id=material_id,learner='My learning',activity_kind='cards',card_view='due')))
    actions.extend(extra);actions.extend(blocked)
    for mode,count in [('new',queue['new_count'])]:
        if count: actions.append(dict(reason_text=f"{'Review' if mode=='due' else 'Study'} {count} {mode} cards",
            target=dict(page='Flash Cards',material_id=material_id,learner='My learning',activity_kind='cards',card_view=mode)))
    if material_id!=NLM_ID:
        from study import topic_stats
        for topic in topic_stats(state,material_id):
            if topic['attempted']>=3 and topic['accuracy']<.7:
                evidence=[r for r in normalize_evidence(state,before=now or clock()) if r['skill']=='document:'+material_id+':'+topic['topic']]
                latest_error=max((datetime.fromisoformat(r['at']) for r in evidence if r['role']=='practice' and not r['correct']),default=None)
                recovered=any(r['role']=='follow_up' and r['correct'] and not r['helped'] and not r['repeat'] and (latest_error is None or datetime.fromisoformat(r['at'])>=latest_error) for r in evidence)
                if recovered:continue
                actions.append(dict(reason_text='Practise '+topic['topic'],target=dict(page='Quiz',material_id=material_id,learner='My learning',topic_id=topic['topic'])))
    if not actions:
        context=state['preferences'].get('last_context',{}).get('My learning')
        if context and context.get('material_id')==material_id and context['page']!='Dashboard':actions.append(dict(reason_text='Return to your saved activity',target=context))
    return actions


def update_material(state,material_id,*,title=None,visibility=None):
    from copy import deepcopy
    from engine import require
    require(material_id in {m['id'] for m in materials(state)},'Unknown material.')
    result=deepcopy(state)
    meta=result['material_meta'].setdefault(material_id,dict(visibility='active',title=None,active_pack=None))
    if title is not None:
        require(type(title) is str and 0<len(title.strip())<=100,'Use a title of 1–100 characters.'); meta['title']=title.strip()
    if visibility is not None:
        require(visibility in ('active','archived','history'),'Invalid material visibility.'); meta['visibility']=visibility
    return result


def topic_label(state,topic_id):
    for d in state['documents']:
        prefix='document:'+d['id']+':'
        if topic_id.startswith(prefix):return topic_id[len(prefix):]
    if topic_id.startswith('newton:'):
        cid=topic_id.split(':',1)[1]
        return next((c['title'] for c in nlm.load_pack()['concepts'] if c['id']==cid),cid.replace('_',' ').title())
    return {'debugger:motion':'Motion and forces','debugger:mass':'Force and mass','debugger:upload':'Source review'}.get(topic_id,topic_id.replace('_',' ').title())


def default_material(state):
    rows=materials(state);saved=state['preferences'].get('last_material')
    if saved in {m['id'] for m in rows}:return saved
    active=[m['id'] for m in rows if m['kind']=='uploaded' and m['visibility']=='active']
    return active[-1] if active else NLM_ID
