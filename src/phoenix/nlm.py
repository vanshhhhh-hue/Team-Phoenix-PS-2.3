"""Validated authored pack and event-sourced adaptive learning, independent of AI."""
from copy import deepcopy
from datetime import datetime, timedelta
from functools import lru_cache
import json
import math
from pathlib import Path
from uuid import uuid4

from engine import DomainError, require
from ledger import clock, stamp

PACK_PATH = Path(__file__).resolve().parents[2] / 'samples/users/user-1/nlm-v1.json'
FAMILIES = {'block','experiment','pair','incline','friction','circle','impulse','equilibrium'}


def validate_pack(pack):
    try:
        require(pack['id']=='nlm-jee-2026' and type(pack['version']) is int and pack['version']==1
                and pack['syllabus_year']==2026, 'Unsupported NLM pack.')
        maps={}
        for collection in ('concepts','prerequisites','questions','misconceptions','flashcards','visuals'):
            rows=pack[collection]
            require(type(rows) is list and all(type(r) is dict for r in rows), 'Invalid pack collection.')
            require(all(type(r['id']) is str and 0<len(r['id'])<100 for r in rows), 'Invalid pack ID.')
            require(len({r['id'] for r in rows})==len(rows),'Duplicate pack ID.')
            maps[collection]={r['id']:r for r in rows}
        concepts=maps['concepts']; prereqs=set(concepts)|set(maps['prerequisites'])
        require(len(concepts)>=12 and len(maps['misconceptions'])>=18 and len(maps['flashcards'])>=24,'Incomplete pack.')
        require(len([q for q in pack['questions'] if q['role']=='primary'])>=36,'Incomplete primary bank.')
        for v in pack['visuals']:
            require(set(v)=={'id','family','version'} and v['family'] in FAMILIES and v['id']==v['family']
                    and type(v['version']) is int and v['version']==1, 'Unsafe visual specification.')
        for s in pack['sources'].values():
            require(s['url'].startswith('https://') and s['section'] and s['role'], 'Missing source provenance.')
        for r in pack['concepts']+pack['prerequisites']+pack['questions']+pack['flashcards']:
            require(r['evidence_refs'] and all(s in pack['sources'] for s in r['evidence_refs']), 'Broken evidence reference.')
        for c in pack['concepts']:
            require(all(p in prereqs and p!=c['id'] for p in c['prerequisite_ids']) and c['visual_id'] in maps['visuals'], 'Broken concept reference.')
            require(all(isinstance(c[k],str) and c[k] for k in ('explanation','formula_assumptions','worked_example')), 'Missing teaching note.')
        def visit(cid, path):
            require(cid not in path, 'Cyclic prerequisites.')
            if cid in concepts:
                for dep in concepts[cid]['prerequisite_ids']: visit(dep,path|{cid})
        for cid in concepts: visit(cid,set())
        for m in pack['misconceptions']:
            require(m['concept_id'] in concepts and m['remediation_ref'] in concepts and m['probe'] and m['hint'] and m['observable_distractors'], 'Invalid misconception candidate.')
        for q in pack['questions']:
            require(q['concept_id'] in concepts and q['visual_id'] in maps['visuals']
                    and all(p in prereqs for p in q['prerequisite_ids']), 'Broken question reference.')
            require(q['role'] in ('primary','follow_up','transfer') and q['difficulty'] in ('easy','medium','hard'), 'Invalid question kind.')
            require(type(q['options']) is list and len(q['options'])==4 and len(set(q['options']))==4
                    and all(type(o) is str and o for o in q['options']) and type(q['correct_index']) is int
                    and 0<=q['correct_index']<4,'Invalid deterministic answer.')
            require(len(q['hints'])==2 and all(type(h) is str and h for h in q['hints'])
                    and q['solution_steps'] and q['assumptions'] and q['provenance'], 'Missing learning support.')
            require(set(q['distractor_candidates'])=={str(i) for i in range(4) if i!=q['correct_index']}
                    and all(v in ('calculation','uncertain') or v in maps['misconceptions'] for v in q['distractor_candidates'].values()), 'Invalid distractor mapping.')
            require(q['role']!='primary' or q['follow_up_ids'], 'Primary needs a fresh follow-up.')
            require(all(f in maps['questions'] and maps['questions'][f]['role']=='follow_up'
                        and maps['questions'][f]['concept_id']==q['concept_id'] and f!=q['id'] for f in q['follow_up_ids']), 'Broken follow-up.')
            validate_scene(q['scene'])
        for m in pack['misconceptions']:
            actual={q['id']+':'+k for q in pack['questions'] for k,v in q['distractor_candidates'].items() if v==m['id']}
            require(set(m['observable_distractors'])==actual,'Broken observable distractor reference.')
        for card in pack['flashcards']:
            require(card['concept_id'] in concepts and card['practice_id'] in maps['questions']
                    and card['visual_id'] in maps['visuals'] and card['kind']=='open_recall', 'Invalid recall card.')
    except (KeyError,TypeError,ValueError,AttributeError,RecursionError) as exc:
        raise DomainError('invalid_content','Malformed NLM pack.') from exc
    return pack


def validate_scene(scene):
    if scene is None: return
    require(type(scene) is dict, 'Invalid question scene.')
    kind=scene.get('kind')
    if kind=='graph':
        require(set(scene)=={'kind','quantity','points','x_max','y_min','y_max'} and scene['quantity'] in ('velocity','force'), 'Invalid graph spec.')
        require(all(type(scene[k]) in (int,float) and math.isfinite(scene[k]) for k in ('x_max','y_min','y_max'))
                and 0<scene['x_max']<=100 and -100<=scene['y_min']<scene['y_max']<=100, 'Invalid graph bounds.')
        points=scene['points']
        require(type(points) is list and 2<=len(points)<=8 and all(type(p) is list and len(p)==2
                    and all(type(v) in (int,float) and math.isfinite(v) for v in p)
                    and 0<=p[0]<=scene['x_max'] and scene['y_min']<=p[1]<=scene['y_max'] for p in points), 'Invalid graph points.')
        require(all(a[0]<=b[0] for a,b in zip(points,points[1:])), 'Time must be ordered.')
    elif kind=='orbit':
        require(scene=={'kind':'orbit','position':'rightmost','rotation':'anticlockwise'}, 'Unsupported orbit scene.')
    elif kind=='incline':
        require(set(scene)=={'kind','angle'} and type(scene['angle']) in (int,float) and 0<=scene['angle']<=75, 'Invalid incline scene.')
    else: raise DomainError('invalid_content','Unsupported question scene.')


@lru_cache(maxsize=1)
def _pack():
    return validate_pack(json.loads(PACK_PATH.read_text(encoding='utf-8')))


def load_pack():
    return deepcopy(_pack())


def empty_progress():
    return {'pack_version':1,'installed':False,'sessions':[],'reviews':[]}


def install(state):
    load_pack()  # Validate before any mutation; progress is never reseeded.
    result=deepcopy(state); result['nlm']['installed']=True
    return result


def question(qid):
    q=next((q for q in _pack()['questions'] if q['id']==qid),None)
    require(q is not None,'Unknown NLM question.')
    return deepcopy(q)


def start(state,qid,learner='My learning',now=None):
    require(state['nlm']['installed'],'Install the authored pack first.')
    require(question(qid)['role']=='primary','Start with a primary question.')
    require(type(learner) is str and 0<len(learner)<=60,'Invalid learner namespace.')
    existing=next((s for s in reversed(state['nlm']['sessions']) if s['learner']==learner
                   and s['question_id']==qid and view(s)['step']!='COMPLETE'),None)
    if existing: return deepcopy(state),existing['id']
    result=deepcopy(state); sid=str(uuid4())
    result['nlm']['sessions'].append(dict(id=sid,learner=learner,question_id=qid,created_at=stamp(now or clock()),events=[]))
    return result,sid


def view(session):
    """Replay validated events. No separate mutable grading/completion flags to corrupt."""
    initial=question(session['question_id'])
    v=dict(step='UNANSWERED',phase='primary',question_id=initial['id'],hints=0,tries=0,
           first_response=None,responses=[],candidate=None,solution=False,cycles=0,follow_up=None,
           transfer=None,delayed=None,due_at=None,last_correct=None,probes=[],ever_solution=False,max_hints=0)
    seen=set(); last=datetime.fromisoformat(session['created_at'])
    require(last.tzinfo is not None,'Missing timezone.')
    for index,e in enumerate(session['events']):
        require(set(e)=={'id','action','answer','at','revision'} and type(e['id']) is str and 0<len(e['id'])<=100
                and e['id'] not in seen and type(e['revision']) is int and e['revision']==index, 'Invalid learning event.')
        seen.add(e['id']); date=datetime.fromisoformat(e['at'])
        require(date.tzinfo is not None and date>=last,'Invalid event time.'); last=date
        action=e['action']; q=question(v['question_id'])
        if action=='answer':
            require(v['step'] in ('UNANSWERED','HINT_1','HINT_2','RETRY','FOLLOW_UP','TRANSFER','DELAYED_REVIEW') and not v['solution'], 'Answer not allowed now.')
            answer=e['answer']; require(type(answer) is int and 0<=answer<4,'Choose an answer.')
            correct=answer==q['correct_index']
            response=dict(question_id=q['id'],phase=v['phase'],selected_index=answer,correct=correct,hints=v['hints'],at=e['at'])
            v['responses'].append(response); v['last_correct']=correct; v['tries']+=1
            if v['first_response'] is None: v['first_response']=deepcopy(response)
            if not correct:
                v['candidate']=q['distractor_candidates'][str(answer)]
            if v['phase']!='primary':
                v[v['phase']]=deepcopy(response)
                if correct:
                    v['step']='COMPLETE'; v['due_at']=stamp(date+timedelta(days=1))
                else:
                    v['cycles']+=1; v['solution']=True; v['step']='REMEDIATION' if v['cycles']<2 else 'RECAP'
                    v['due_at']=stamp(date+timedelta(days=1))
            elif correct:
                v['step']='FIRST_RESPONSE'; v['solution']=False
            elif v['tries']<=2:
                v['hints']=max(v['hints'],v['tries']); v['step']='HINT_'+str(v['hints'])
            else:
                v['solution']=True; v['step']='SOLUTION'
        elif action=='probe':
            require(v['step'] in ('HINT_1','HINT_2') and v['candidate'] is not None
                    and e['answer'] in ('concept','calculation','uncertain') and not v['probes'], 'Probe not available.')
            v['probes'].append(dict(response=e['answer'],candidate=v['candidate'],at=e['at']))
        elif action=='hint':
            require(e['answer'] is None and v['phase']=='primary' and not v['solution']
                    and v['step'] in ('UNANSWERED','HINT_1','RETRY') and v['hints']<2,'Hint not available.')
            v['hints']+=1; v['step']='HINT_'+str(v['hints'])
        elif action=='solution':
            require(e['answer'] is None and v['phase']=='primary' and v['hints']>=1 and not v['solution']
                    and v['step'] in ('HINT_1','HINT_2','RETRY'),'Try a hint first.')
            v['solution']=True; v['step']='SOLUTION'
        elif action in ('continue','continue_v2'):
            require((e['answer'] is None if action=='continue' else type(e['answer']) is str) and v['step'] in ('SOLUTION','FIRST_RESPONSE','REMEDIATION'), 'Continue not available.')
            if v['step']=='REMEDIATION':
                choices=[x for x in _pack()['questions'] if x['concept_id']==initial['concept_id'] and x['role']=='follow_up'
                         and x['id'] not in {r['question_id'] for r in v['responses']}]
                require(choices,'No fresh remediation check available.')
                target=choices[0]['id']
            else: target=initial['follow_up_ids'][0]
            if action=='continue_v2':
                target=e['answer']
                require(question(target)['concept_id']==initial['concept_id'] and question(target)['role']=='follow_up' and target not in {r['question_id'] for r in v['responses']},'Invalid fresh follow-up target.')
            v.update(question_id=target,phase='follow_up',step='FOLLOW_UP',hints=0,tries=0,solution=False,last_correct=None)
        elif action in ('transfer','delayed','transfer_v2','delayed_v2'):
            versioned=action.endswith('_v2')
            action=action.removesuffix('_v2')
            require((type(e['answer']) is str if versioned else e['answer'] is None) and v['step'] in ('COMPLETE','RECAP'),'Review not available.')
            if action=='transfer': require(v['step']=='COMPLETE' and v['transfer'] is None,'Transfer already recorded or recap required.')
            if action=='delayed':
                require(v['due_at'] and date>=datetime.fromisoformat(v['due_at']),'Delayed review is not due.')
            used={r['question_id'] for r in v['responses']}
            choices=[x for x in _pack()['questions'] if x['concept_id']==initial['concept_id'] and x['role'] in ('follow_up','transfer') and x['id'] not in used]
            require(choices,'All fresh checks used. Start another primary after your recap.')
            target=choices[-1]['id'] if action=='transfer' else choices[0]['id']
            if versioned:
                target=e['answer']; require(target in {c['id'] for c in choices},'Invalid fresh review target.')
            phase='transfer' if action=='transfer' else 'delayed'
            v.update(question_id=target,phase=phase,step='TRANSFER' if action=='transfer' else 'DELAYED_REVIEW',hints=0,tries=0,solution=False,last_correct=None)
        else: raise DomainError('invalid_transition','Unknown learning action.')
        v['ever_solution']=v['ever_solution'] or v['solution']
        v['max_hints']=max(v['max_hints'],v['hints'])
    return v


def event(state,sid,action,answer=None,token=None,revision=None,now=None):
    s=next((s for s in state['nlm']['sessions'] if s['id']==sid),None)
    require(s is not None,'Unknown learning session.')
    require(type(token) is str and 0<len(token)<=100,'Invalid event token.')
    existing=next((e for e in s['events'] if e['id']==token),None)
    if existing:
        require(existing['action'].removesuffix('_v2')==action and (action in ('continue','transfer','delayed') or existing['answer']==answer),'Learning token was reused with different content.')
        return deepcopy(state)
    require(type(revision) is int and revision==len(s['events']),'This learning step changed. Refresh and try again.','invalid_transition')
    if action in ('continue','transfer','delayed'):
        target=eligible_check(state,sid,action)
        require(target is not None,'No unused independent item is available on this route. Review the explanation or choose another concept; repeated practice cannot establish an independent pass.','invalid_transition')
        action=action+'_v2'; answer=target
    result=deepcopy(state); updated=next(s for s in result['nlm']['sessions'] if s['id']==sid)
    updated['events'].append(dict(id=token,action=action,answer=answer,at=stamp(now or clock()),revision=revision))
    view(updated)
    return result


def eligible_check(state,sid,action):
    session=next(s for s in state['nlm']['sessions'] if s['id']==sid)
    v=view(session); initial=question(session['question_id'])
    exposed=set()
    for old in state['nlm']['sessions']:
        if old['learner']!=session['learner']: continue
        # Include every presentation, including abandoned items without an answer.
        for count in range(len(old['events'])+1):
            prefix=dict(old,events=old['events'][:count]); exposed.add(view(prefix)['question_id'])
    roles=('follow_up',) if action=='continue' else ('follow_up','transfer')
    choices=[q['id'] for q in _pack()['questions'] if q['concept_id']==initial['concept_id'] and q['role'] in roles and q['id'] not in exposed]
    preferred=initial['follow_up_ids'] if action=='continue' else []
    return next((qid for qid in preferred if qid in choices),choices[-1] if choices and action=='transfer' else choices[0] if choices else None)


def remaining_unseen_checks(state,concept_id,learner='My learning'):
    exposed=set()
    for session in state['nlm']['sessions']:
        if session['learner']!=learner:continue
        for n in range(len(session['events'])+1):exposed.add(view(dict(session,events=session['events'][:n]))['question_id'])
    return sum(q['concept_id']==concept_id and q['role'] in ('follow_up','transfer') and q['id'] not in exposed for q in _pack()['questions'])


def review_card(state,cid,rating,token,learner='My learning',now=None):
    now=now or clock()
    require(any(c['id']==cid for c in _pack()['flashcards']),'Unknown NLM card.')
    require(rating in ('Again','Hard','Good','Easy') and type(token) is str and 0<len(token)<=100,'Invalid review.')
    require(type(learner) is str and 0<len(learner)<=60,'Invalid learner.')
    records=state['nlm']['reviews']
    if any(r['id']==token for r in records): return deepcopy(state)
    prior=[r for r in records if r['card_id']==cid and r['learner']==learner]
    require(not prior or now>=datetime.fromisoformat(prior[-1]['due_at']),'This card is not due.')
    step=prior[-1]['step'] if prior else 0
    if rating=='Again': step=0; interval=timedelta(minutes=10)
    elif rating=='Hard': interval=timedelta(days=1)
    else:
        index=min(step+(rating=='Easy'),3); interval=timedelta(days=[1,3,7,14][index]); step=min(index+1,3)
    result=deepcopy(state)
    result['nlm']['reviews'].append(dict(id=token,card_id=cid,learner=learner,rating=rating,reviewed_at=stamp(now),due_at=stamp(now+interval),step=step))
    return result


def validate_progress(progress):
    try:
        require(type(progress) is dict and set(progress)==set(empty_progress()) and type(progress['pack_version']) is int
                and progress['pack_version']==1 and type(progress['installed']) is bool,'Invalid NLM progress version.')
        require(type(progress['sessions']) is list and type(progress['reviews']) is list
                and len(progress['sessions'])<=1000 and len(progress['reviews'])<=10000, 'Invalid NLM collections.')
        require(progress['installed'] or not (progress['sessions'] or progress['reviews']), 'Pack not installed.')
        ids=set()
        for s in progress['sessions']:
            require(set(s)=={'id','learner','question_id','created_at','events'} and type(s['id']) is str and 0<len(s['id'])<=100
                    and s['id'] not in ids and type(s['learner']) is str and 0<len(s['learner'])<=60
                    and type(s['events']) is list and len(s['events'])<=100
                    and question(s['question_id'])['role']=='primary','Invalid learning session.')
            ids.add(s['id']); view(s)
        replay={'nlm':empty_progress()}
        for r in progress['reviews']:
            require(set(r)=={'id','card_id','learner','rating','reviewed_at','due_at','step'} and r['id'] not in ids,'Invalid recall review.')
            ids.add(r['id']); at=datetime.fromisoformat(r['reviewed_at']); require(at.tzinfo is not None,'Missing timezone.')
            replay=review_card(replay,r['card_id'],r['rating'],r['id'],r['learner'],at)
            require(replay['nlm']['reviews'][-1]==r,'Inconsistent recall schedule.')
    except (KeyError,TypeError,ValueError,AttributeError,RecursionError) as exc:
        raise DomainError('invalid_progress','Malformed NLM progress; existing data preserved.') from exc
    return progress


def insights(progress,learner=None):
    rows=[]; seen=set()
    for s in progress['sessions']:
        if learner is not None and s['learner']!=learner: continue
        v=view(s); first=v['first_response']
        if not first: continue
        identity=(s['learner'],s['question_id'])
        repeat=identity in seen; seen.add(identity)
        follow=v['follow_up']; later=v['delayed']; transfer=v['transfer']
        rows.append(dict(learner=s['learner'],concept=question(s['question_id'])['concept_id'],question_id=s['question_id'],
                         first_correct=first['correct'],pre_answer_help=first['hints'],repeat_practice=repeat,
                         retries=sum(r['phase']=='primary' for r in v['responses'])-1,
                         hints_used=v['max_hints'],solution_revealed=v['ever_solution'],
                         candidate=('Your answer may suggest '+v['candidate']) if v['candidate'] else 'No candidate inferred',
                         probe_response=v['probes'][0]['response'] if v['probes'] else None,
                         status='follow-up passed' if follow and follow['correct'] else 'improved with hints' if any(r['correct'] and r['hints'] for r in v['responses']) else 'needs practice' if not first['correct'] else 'reasoning check pending',
                         immediate_follow_up=None if follow is None else follow['correct'],transfer=None if transfer is None else transfer['correct'],
                         follow_up_checks=[r['correct'] for r in v['responses'] if r['phase']=='follow_up'],
                         delayed_recall=None if later is None else later['correct'],review='delayed review pending' if later is None else 'delayed review recorded',due_at=v['due_at']))
    return rows


def reset_demo(state,learner):
    require(learner in ('Demo Learner A','Demo Learner B'),'Only explicit demo learner records can be reset.')
    result=deepcopy(state)
    for key in ('sessions','reviews'):
        result['nlm'][key]=[r for r in result['nlm'][key] if r['learner']!=learner]
    # Debugger decisions can reference this demo's Newton evidence. Reset the same demo's
    # derived cases as well, so no dangling evidence survives an explicitly scoped reset.
    if 'debugger' in result:
        result['debugger']['episodes']=[e for e in result['debugger']['episodes'] if e['learner']!=learner]
    if 'activity_events' in result:result['activity_events']=[e for e in result['activity_events'] if e['learner']!=learner]
    if 'drafts' in result:result['drafts']=[d for d in result['drafts'] if d['learner']!=learner]
    result.get('preferences',{}).get('last_context',{}).pop(learner,None)
    return result
