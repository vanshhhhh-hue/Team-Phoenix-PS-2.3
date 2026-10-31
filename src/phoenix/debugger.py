"""History-aware debugger: validated events, deterministic decisions and local progress."""
from copy import deepcopy
from datetime import datetime, timedelta
from uuid import uuid4
from engine import require, DomainError
from ledger import clock, stamp
from debugger_content import QUESTIONS, TOPICS, HYPOTHESES, REPAIRS, POLICY, VERSION, validate_content
from debugger_policy import choose_next_action, choose_repair
from learning_events import exposed_questions

LEARNERS=('My learning','Demo Learner A','Demo Learner B')
EVENT_FIELDS={'id','action','value','at','revision'}


def empty_progress():
    return dict(content_version=VERSION,history={},episodes=[])


def get_episode(state,sid):
    ep=next((e for e in state['debugger']['episodes'] if e['id']==sid),None)
    require(ep is not None,'Unknown debugger episode.')
    return ep


def view(ep):
    """Replay an episode against its pinned content. Summaries are never authoritative state."""
    require(ep['topic'] in TOPICS or ep['topic']=='upload','Unsupported debugger topic.')
    v=dict(phase='primary' if ep['topic']!='upload' else 'source',pending=None,decision=None,
           probes=0,answers=[],helped=False,repair=None,feedback=None,confidence=None,
           immediate=None,transfer=None,delayed=None,due_at=None,successful_delayed=0,
           disagreements=0,unavailable=False,repair_status='open',preference=None)
    seen=set(); last=datetime.fromisoformat(ep['created_at'])
    require(last.tzinfo is not None,'Missing episode timezone.')
    for i,e in enumerate(ep['events']):
        require(type(e) is dict and set(e)==EVENT_FIELDS and type(e['id']) is str
                and 0<len(e['id'])<=100 and e['id'] not in seen
                and type(e['revision']) is int and e['revision']==i,'Invalid debugger event.')
        seen.add(e['id']); at=datetime.fromisoformat(e['at'])
        require(at.tzinfo is not None and at>=last,'Invalid debugger event time.'); last=at
        action=e['action']; val=e['value']
        if action=='present':
            require(v['phase'] in ('primary','probe','teach','follow_up','transfer','delayed')
                    and v['pending'] is None and not v['unavailable'],'Question not available.')
            require(type(val) is dict and set(val)=={'question_id','reason_code','evidence_ids','policy_version','content_version'},'Invalid decision.')
            q=QUESTIONS.get(val['question_id'])
            require(q is not None and q['topic']==ep['topic'] and q['role']==v['phase']
                    and val['policy_version']==POLICY and type(val['content_version']) is int and val['content_version']==VERSION
                    and type(val['reason_code']) is str and val['reason_code'] in
                    {'fresh_primary','fresh_probe','fresh_teach','fresh_follow_up','fresh_transfer','fresh_delayed',
                     'discriminate_causes_with_history','discriminate_current_attempt'}
                    and type(val['evidence_ids']) is list and len(val['evidence_ids'])<=1000
                    and all(type(x) is str and 0<len(x)<=200 for x in val['evidence_ids']), 'Invalid question decision.')
            require(v['phase']!='probe' or v['probes']<2,'Probe budget exhausted.')
            v.update(pending=q['id'],decision=val,helped=False,feedback=None)
        elif action=='answer':
            require(v['pending'] is not None and type(val) is dict and set(val)=={'option','confidence'}
                    and val['confidence'] in ('sure','unsure','guessing','not given'),'Invalid answer.')
            q=QUESTIONS[v['pending']]
            require(type(val['option']) is int and 0<=val['option']<len(q['options']),'Choose an answer.')
            result=dict(question_id=q['id'],role=q['role'],correct=val['option']==q['correct'],helped=v['helped'],at=e['at'])
            v['answers'].append(result); v['feedback']=result; v['confidence']=val['confidence']
            v['pending']=None
            if q['role']=='primary': v['phase']='follow_up' if result['correct'] and not result['helped'] else 'probe'
            elif q['role']=='probe':
                v['probes']+=1; v['phase']='repair' if v['probes']==2 else 'probe'
            elif q['role']=='teach': v['phase']='follow_up' if result['correct'] else 'repair'
            elif q['role'] in ('follow_up','transfer','delayed'):
                key={'follow_up':'immediate','transfer':'transfer','delayed':'delayed'}[q['role']]
                v[key]=result; passed=result['correct'] and not result['helped']
                v['repair_status']=({'follow_up':'immediate_check_passed','transfer':'transfer_check_passed','delayed':'delayed_check_passed'}[q['role']] if passed else 'reopened')
                v['phase']='complete'
                if q['role']=='delayed': v['successful_delayed']=v['successful_delayed']+1 if passed else 0
                days=(1,3,7)[min(v['successful_delayed'],2)] if passed else 1
                if q['role']!='transfer' or not v['due_at']:
                    v['due_at']=stamp(at+timedelta(days=days))
        elif action=='help':
            require(val is None and v['pending'] is not None and not v['helped'],'Help is not available.')
            v['helped']=True
        elif action in ('repair','alternate'):
            require(v['phase'] in ('primary','probe','repair','source','follow_up','complete') or action=='alternate' and v['phase']=='teach','Repair not available.')
            require(type(val) is dict and set(val)=={'hypothesis','reason_code','evidence_ids','policy_version','content_version'}
                    and val['hypothesis'] in REPAIRS and (val['hypothesis']=='unclear' or val['hypothesis'] in TOPICS.get(ep['topic'],{}).get('hypotheses',[]))
                    and val['policy_version']==POLICY and type(val['content_version']) is int and val['content_version']==VERSION
                    and type(val['evidence_ids']) is list and len(val['evidence_ids'])<=1000
                    and all(type(x) is str and 0<len(x)<=200 for x in val['evidence_ids'])
                    and val['reason_code'] in ('supported_candidate','correct_relation_execution_needs_check',
                    'forces_identified_quantity_needs_check','insufficient_or_conflicting_evidence','student_choice','source_guided_review'), 'Invalid repair.')
            v.update(phase='source' if ep['topic']=='upload' else 'teach',pending=None,helped=False,
                     repair=val,repair_status='in_progress',unavailable=False,feedback=None)
        elif action=='review':
            require(v['phase']=='complete' and v['pending'] is None and val in ('transfer','delayed','retry'),'Review not available.')
            if val=='delayed': require(v['due_at'] and at>=datetime.fromisoformat(v['due_at']),'Delayed check is not due.')
            if val=='transfer': require(v['immediate'] and v['immediate']['correct'] and not v['immediate']['helped'] and v['transfer'] is None,'Pass an independent follow-up before transfer.')
            v.update(phase='follow_up' if val=='retry' else val,pending=None,feedback=None,unavailable=False)
        elif action=='unavailable':
            require(val is None and v['pending'] is None and v['phase'] in ('probe','follow_up','transfer','delayed'),'Invalid exhausted-bank state.')
            v['unavailable']=True
        elif action=='disagree':
            require(val is None,'Invalid disagreement.'); v['disagreements']+=1
        elif action=='feedback':
            require(v['repair'] and val in ('helped','did not help'),'Invalid support feedback.'); v['preference']=val
        elif action=='source_complete':
            require(ep['topic']=='upload' and v['phase']=='source' and val is None,'Invalid source completion.')
            v.update(phase='source_done',repair_status='reviewed_source')
        else: raise DomainError('invalid_transition','Unknown debugger action.')
    return v


def start(state,topic,learner='My learning',now=None,origin=None):
    now=now or clock()
    require(learner in LEARNERS and (topic in TOPICS or topic=='upload'),'Choose a supported learning workspace.')
    if topic=='upload':
        require(learner=='My learning' and type(origin) is dict and set(origin)=={'document_id','question_id'},'Choose uploaded material.')
        _validate_origin(state,origin)
    else: require(origin is None,'Authored practice has no uploaded source mapping.')
    for ep in reversed(state['debugger']['episodes']):
        if ep['learner']==learner and ep['topic']==topic and ep['origin']==origin and view(ep)['phase'] not in ('complete','source_done'):
            return deepcopy(state),ep['id']
    result=deepcopy(state); sid=str(uuid4())
    ep=dict(id=sid,learner=learner,topic=topic,origin=deepcopy(origin),created_at=stamp(now),events=[])
    result['debugger']['episodes'].append(ep)
    if topic!='upload': result=event(result,sid,'next',token=sid+':0',revision=0,now=now)
    validate_progress(result)
    return result,sid


def event(state,sid,action,value=None,token=None,revision=None,now=None):
    ep=get_episode(state,sid); now=now or clock()
    require(type(token) is str and 0<len(token)<=100,'Invalid submission token.')
    if any(e['id']==token for e in ep['events']): return deepcopy(state)
    require(type(revision) is int and revision==len(ep['events']),'This step changed. Refresh and try again.','invalid_transition')
    v=view(ep)
    if action=='next':
        require(value is None and v['pending'] is None,'Finish the current question first.')
        if v['phase']=='repair': action='repair'; value=choose_repair(state,ep,now)
        else:
            require(ep['topic']!='upload','Review the source for this material.')
            value=choose_next_action(state,ep,v,now)
            if value['question_id'] is None:
                if v['phase']=='probe': action='repair'; value=choose_repair(state,ep,now)
                else: action='unavailable'; value=None
            else: action='present'
    elif action=='repair':
        require(value is None,'Automatic repair does not accept a diagnosis.')
        value=choose_repair(state,ep,now) if ep['topic']!='upload' else dict(hypothesis='unclear',reason_code='source_guided_review',evidence_ids=[],policy_version=POLICY,content_version=VERSION)
    elif action=='alternate':
        require(value in REPAIRS and (value=='unclear' or value in TOPICS.get(ep['topic'],{}).get('hypotheses',[])),'Choose a suitable explanation.')
        value=dict(hypothesis=value,reason_code='student_choice',evidence_ids=[],policy_version=POLICY,content_version=VERSION)
    else: require(action in ('answer','help','review','disagree','feedback','source_complete'),'Unknown debugger action.')
    result=deepcopy(state); target=get_episode(result,sid)
    target['events'].append(dict(id=token,action=action,value=value,at=stamp(now),revision=revision))
    view(target)
    validate_progress(result)
    return result


def set_history(state,learner,enabled):
    require(learner in LEARNERS and type(enabled) is bool,'Invalid history preference.')
    result=deepcopy(state); result['debugger']['history'][learner]=enabled
    return result


def delete_history(state,learner):
    """Scoped deletion: remove only debugger episodes. Legacy progress remains in its source."""
    require(learner in LEARNERS,'Unknown learner.')
    result=deepcopy(state)
    result['debugger']['episodes']=[e for e in result['debugger']['episodes'] if e['learner']!=learner]
    result['debugger']['history'][learner]=False
    if 'activity_events' in result:result['activity_events']=[e for e in result['activity_events'] if not(e['kind']=='debugger_experiment' and e['learner']==learner)]
    context=result.get('preferences',{}).get('last_context',{}).get(learner)
    if context and context.get('activity_kind')=='repair':result['preferences']['last_context'].pop(learner,None)
    return result


def _validate_origin(state,origin):
    d=next((d for d in state['documents'] if d['id']==origin['document_id']),None)
    require(d is not None and any(q['id']==origin['question_id'] for q in d['questions']),'Unknown uploaded question.')


def validate_progress(state):
    """Validate replay, references and cross-session exposure before importing or saving."""
    validate_content(); progress=state['debugger']
    require(type(progress) is dict and set(progress)=={'content_version','history','episodes'}
            and type(progress['content_version']) is int and progress['content_version']==VERSION,'Unsupported debugger content version.')
    require(type(progress['history']) is dict and all(k in LEARNERS and type(v) is bool for k,v in progress['history'].items()),'Invalid history preferences.')
    require(type(progress['episodes']) is list and len(progress['episodes'])<=200,'Debugger episode limit reached.')
    ids=set(); event_ids=set(); exposures=set(); evidence={}
    # Native identifiers are checked by the study/Newton validators; references cannot point to missing evidence.
    from learning_events import normalize_evidence
    for learner in LEARNERS:
        evidence.update({r['id']:(learner,datetime.fromisoformat(r['at'])) for r in normalize_evidence(state,learner)})
    for ep in progress['episodes']:
        require(type(ep) is dict and set(ep)=={'id','learner','topic','origin','created_at','events'}
                and type(ep['id']) is str and 0<len(ep['id'])<=100 and ep['id'] not in ids
                and ep['learner'] in LEARNERS and type(ep['created_at']) is str and len(ep['created_at'])<=64
                and type(ep['events']) is list and len(ep['events'])<=200,'Invalid debugger episode.')
        ids.add(ep['id'])
        if ep['topic']=='upload':
            require(ep['learner']=='My learning' and type(ep['origin']) is dict and set(ep['origin'])=={'document_id','question_id'},'Invalid material link.')
            _validate_origin(state,ep['origin'])
        else: require(ep['origin'] is None,'Invalid authored source link.')
        view(ep)
        for e in ep['events']:
            require(e['id'] not in event_ids,'Duplicate debugger event ID.'); event_ids.add(e['id'])
            if e['action'] in ('present','repair','alternate'):
                require(all(ref in evidence and evidence[ref][0]==ep['learner']
                            and evidence[ref][1]<=datetime.fromisoformat(e['at'])
                            for ref in e['value']['evidence_ids']),'Missing, foreign or future decision evidence.')
            if e['action']=='present':
                q=QUESTIONS[e['value']['question_id']]; pair=(ep['learner'],q['family'])
                require(q['role'] in ('primary','teach') or pair not in exposures,'Previously exposed item cannot count as fresh.')
                exposures.add(pair)
    return progress
