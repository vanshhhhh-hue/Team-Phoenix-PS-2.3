"""Durable uploaded activity selectors and bounded student commands."""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from engine import require
from ledger import clock, stamp


def hint_level(state,quiz_id,question_id):
    return max((e['value'] for e in state['activity_events'] if e['kind']=='hint' and e['activity_id']==quiz_id and e['item_id']==question_id),default=0)


def show_hint(state,quiz_id,question_id,level,now=None):
    quiz=next((q for q in state['quizzes'] if q['id']==quiz_id),None)
    require(quiz and not quiz['completed'] and question_id in quiz['question_ids'],'Open the current quiz first.')
    answered={a['question_id'] for a in state['attempts'] if a['quiz_id']==quiz_id}
    require(next((qid for qid in quiz['question_ids'] if qid not in answered),None)==question_id,'Help is only available for the current unanswered item.')
    require(type(level) is int and 1<=level<=2,'Invalid hint level.')
    existing=hint_level(state,quiz_id,question_id)
    if level<=existing: return deepcopy(state)
    require(level==existing+1,'Show hints in order.')
    result=deepcopy(state)
    result['activity_events'].append(dict(id='hint:'+sha256((quiz_id+question_id+str(level)).encode()).hexdigest(),
        learner='My learning',material_id=quiz['document_id'],activity_id=quiz_id,item_id=question_id,
        kind='hint',value=level,at=stamp(now or clock())))
    return result


def submit_answer(state,quiz_id,question_id,selected_index,token,now=None):
    from study import answer_question
    return answer_question(state,quiz_id,question_id,selected_index,hint_level(state,quiz_id,question_id),token,now)


def upload_activity_view(state,quiz_id):
    from study import practice_view
    quiz=next((q for q in state['quizzes'] if q['id']==quiz_id),None)
    require(quiz is not None,'Unknown quiz.')
    attempts=[a for a in state['attempts'] if a['quiz_id']==quiz_id]
    pending=next((a for a in attempts if not a['correct'] and not practice_view(state,quiz_id,a['question_id'])['done']),None)
    answered={a['question_id'] for a in attempts}
    unanswered=next((qid for qid in quiz['question_ids'] if qid not in answered),None)
    current=pending['question_id'] if pending else unanswered
    support=practice_view(state,quiz_id,pending['question_id']) if pending else None
    return dict(scoring_complete=quiz['completed'],recovery_complete=pending is None,
        current_question_id=current,pending_support_question_id=pending['question_id'] if pending else None,
        current_phase='recovery' if pending else 'results' if quiz['completed'] else 'question',
        first_attempt=pending,latest_retry=support['retries'][-1] if support and support['retries'] else None,
        pre_answer_hints=pending['hint_count'] if pending else hint_level(state,quiz_id,current),
        recovery_hints=support['hints'] if support else 0,solution_revealed=support['solution'] if support else False,
        exposure_status='recorded' if current and any(e['activity_id']==quiz_id and e['item_id']==current for e in state['activity_events']) else 'unknown',
        resume_target=dict(page='Quiz',material_id=quiz['document_id'],learner='My learning',activity_kind='upload_quiz',activity_id=quiz_id),
        result_summary=dict(correct=sum(a['correct'] for a in attempts),answered=len(attempts),total=len(quiz['question_ids'])))


def validate_activity_events(s):
    from schema_v6 import aware
    events=s['activity_events']; require(type(events) is list and len(events)<=30000,'Invalid activity events.')
    quizzes={q['id']:q for q in s['quizzes']}; seen=set(); levels={}; times={}
    for e in events:
        require(type(e) is dict and set(e)=={'id','learner','material_id','activity_id','item_id','kind','value','at'},'Invalid activity fields.')
        require(type(e['id']) is str and 0<len(e['id'])<=100 and e['id'] not in seen,'Invalid activity token.'); seen.add(e['id'])
        if e['kind']=='debugger_experiment':
            from experiments import debugger_comparison
            ep=next((ep for ep in s['debugger']['episodes'] if ep['id']==e['activity_id']),None)
            require(ep and ep['topic']==e['item_id'] and ep['learner']==e['learner'] and e['material_id']=='authored:nlm-jee-2026','Invalid repair comparison context.')
            v=e['value'];require(type(v) is dict and set(v)=={'version','parameters','prediction','result'} and type(v['version']) is int and v['version']==1 and type(v['prediction']) is int and v['prediction'] in (0,1),'Invalid comparison value.')
            observed=debugger_comparison(ep['topic'],**v['parameters']);require(v['result']==observed['result'] and aware(e['at'])>=aware(ep['created_at']),'Invalid comparison result or time.')
            continue
        if e['kind']=='experiment':
            from experiments import scenario
            require(e['material_id']=='authored:nlm-jee-2026' and e['activity_id']=='lesson:'+e['item_id'] and e['learner'] in ('My learning','Demo Learner A','Demo Learner B'),'Invalid lesson context.')
            v=e['value'];require(type(v) is dict and set(v)=={'version','parameters','prediction','explanation','result'} and type(v['version']) is int and v['version']==1,'Invalid experiment value.')
            observed=scenario(e['item_id'],**v['parameters'])
            require(type(v['prediction']) is int and v['prediction'] in (0,1) and type(v['explanation']) is str and len(v['explanation'])<=4000 and v['result']==observed['result'],'Invalid experiment comparison.')
            aware(e['at']);continue
        q=quizzes.get(e['activity_id'])
        require(q and e['material_id']==q['document_id'] and e['item_id'] in q['question_ids'] and e['learner']=='My learning','Invalid activity context.')
        if e['kind']=='present':
            require(e['value'] is None,'Invalid presentation value.')
            version=next(v for v in s['pack_versions'] if e['item_id'] in v['question_ids'])
            require(not any(old['kind']=='present' and old['item_id']==e['item_id'] and (version['kind']=='independent' or old['activity_id']==e['activity_id']) for old in events[:events.index(e)]),'Duplicate presentation.')
            at=aware(e['at']);require(at>=aware(q['created_at']),'Invalid presentation date.')
            first=next((a for a in s['attempts'] if a['quiz_id']==q['id'] and a['question_id']==e['item_id']),None)
            require(first is None or at<=aware(first['answered_at']),'Presentation follows the response.')
            continue
        require(e['kind']=='hint' and type(e['value']) is int and 1<=e['value']<=2,'Unsupported activity event.')
        pair=(e['activity_id'],e['item_id']); at=aware(e['at'])
        require(e['value']==levels.get(pair,0)+1 and at>=times.get(pair,aware(q['created_at'])),'Invalid hint progression.')
        a=next((a for a in s['attempts'] if a['quiz_id']==q['id'] and a['question_id']==e['item_id']),None)
        require(a is None or at<=aware(a['answered_at']),'Pre-answer hint cannot follow the answer.')
        levels[pair]=e['value']; times[pair]=at
    for a in s['attempts']:
        pair=(a['quiz_id'],a['question_id'])
        require(pair not in levels or a['hint_count']==levels[pair],'Answer assistance contradicts recorded help.')


def save_draft(state,material_id,activity_id,item_id,text,now=None,learner='My learning'):
    from study import get_question
    require(type(text) is str and len(text)<=4000,'Keep saved writing within 4,000 characters.')
    require(valid_draft_context(state,material_id,activity_id,item_id,learner),'Draft does not belong to this activity.')
    result=deepcopy(state)
    old=next((d for d in result['drafts'] if d['activity_id']==activity_id and d['item_id']==item_id and d['learner']==learner),None)
    if not text:
        if old: result['drafts'].remove(old)
        return result
    require(old is not None or len(result['drafts'])<100,'Writing capacity reached. Clear an older saved draft first.')
    entry=dict(learner=learner,material_id=material_id,activity_id=activity_id,item_id=item_id,text=text,updated_at=stamp(now or clock()))
    if old: result['drafts'].remove(old)
    result['drafts'].append(entry)
    return result


def validate_drafts(s):
    from schema_v6 import aware
    require(type(s['drafts']) is list and len(s['drafts'])<=100,'Invalid drafts.')
    seen=set()
    for d in s['drafts']:
        require(type(d) is dict and set(d)=={'learner','material_id','activity_id','item_id','text','updated_at'},'Invalid draft fields.')
        require(valid_draft_context(s,d['material_id'],d['activity_id'],d['item_id'],d['learner']),'Invalid draft context.')
        pair=(d['learner'],d['activity_id'],d['item_id']); require(pair not in seen,'Duplicate draft.'); seen.add(pair)
        require(type(d['text']) is str and 0<len(d['text'])<=4000,'Invalid draft text.'); aware(d['updated_at'])


def record_experiment(state,concept,parameters,prediction,explanation='',learner='My learning',now=None):
    from experiments import scenario
    from workspace import NLM_ID
    from uuid import uuid4
    result=scenario(concept,**parameters)
    require(learner in ('My learning','Demo Learner A','Demo Learner B') and type(prediction) is int and prediction in (0,1),'Choose a prediction.')
    require(type(explanation) is str and len(explanation)<=4000,'Keep explanation within 4,000 characters.')
    value=dict(version=1,parameters=result['parameters'],prediction=prediction,explanation=explanation,result=result['result'])
    prior=[e for e in state['activity_events'] if e['kind']=='experiment' and e['item_id']==concept and e['learner']==learner]
    if prior and prior[-1]['value']==value:return deepcopy(state)
    updated=deepcopy(state)
    updated['activity_events'].append(dict(id=str(uuid4()),learner=learner,material_id=NLM_ID,activity_id='lesson:'+concept,
        item_id=concept,kind='experiment',value=value,at=stamp(now or clock())))
    return updated


def record_presentations(state,quiz_id,now=None):
    """Conservatively reserve/expose the whole independent round in its start command."""
    from uuid import uuid4
    quiz=next(q for q in state['quizzes'] if q['id']==quiz_id)
    result=deepcopy(state)
    for qid in quiz['question_ids']:
        version=next(v for v in state['pack_versions'] if qid in v['question_ids'])
        if version['kind']=='independent':require(not any(e['kind']=='present' and e['item_id']==qid for e in state['activity_events']),'This independent item has already been presented.')
        require(not any(e['kind']=='present' and e['activity_id']==quiz_id and e['item_id']==qid for e in state['activity_events']),'This presentation is already saved.')
        result['activity_events'].append(dict(id=str(uuid4()),learner='My learning',material_id=quiz['document_id'],activity_id=quiz_id,item_id=qid,kind='present',value=None,at=stamp(now or clock())))
    return result


def valid_draft_context(state,material_id,activity_id,item_id,learner):
    from workspace import NLM_ID
    import nlm
    if learner not in ('My learning','Demo Learner A','Demo Learner B'):return False
    if activity_id=='cards':
        if material_id==NLM_ID:return any(c['id']==item_id for c in nlm.load_pack()['flashcards'])
        return learner=='My learning' and any(c['id']==item_id and c['document_id']==material_id for c in state['cards'])
    if material_id==NLM_ID:
        session=next((s for s in state['nlm']['sessions'] if s['id']==activity_id and s['learner']==learner),None)
        return session is not None and any(q['id']==item_id and q['concept_id']==nlm.question(session['question_id'])['concept_id'] for q in nlm.load_pack()['questions'])
    quiz=next((q for q in state['quizzes'] if q['id']==activity_id and q['document_id']==material_id),None)
    return learner=='My learning' and quiz is not None and item_id in quiz['question_ids']


def record_debugger_experiment(state,episode_id,parameters,prediction,now=None):
    from uuid import uuid4
    from experiments import debugger_comparison
    ep=next((e for e in state['debugger']['episodes'] if e['id']==episode_id),None)
    require(ep and ep['topic'] in ('motion','mass'),'Comparison needs its reviewed repair case.')
    require(type(prediction) is int and prediction in (0,1),'Choose a prediction.')
    observed=debugger_comparison(ep['topic'],**parameters)
    value=dict(version=1,parameters=parameters,prediction=prediction,result=observed['result'])
    prior=[e for e in state['activity_events'] if e['kind']=='debugger_experiment' and e['activity_id']==episode_id]
    if prior and prior[-1]['value']==value:return deepcopy(state)
    result=deepcopy(state)
    result['activity_events'].append(dict(id=str(uuid4()),learner=ep['learner'],material_id='authored:nlm-jee-2026',activity_id=episode_id,item_id=ep['topic'],kind='debugger_experiment',value=value,at=stamp(now or clock())))
    return result
