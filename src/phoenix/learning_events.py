"""Read-only normalization. Missing historical reasoning remains unknown."""
from datetime import datetime
from hashlib import sha256
import nlm
from debugger_content import QUESTIONS


def normalize_evidence(state, learner='My learning', before=None):
    rows = []
    def append(**row):
        if before is None or datetime.fromisoformat(row['at']) <= before:
            rows.append(row)
    if learner == 'My learning':
        for a in state['attempts']:
            doc = next(d for d in state['documents'] if any(q['id']==a['question_id'] for q in d['questions']))
            q = next(q for q in doc['questions'] if q['id']==a['question_id'])
            version=next((v for v in state.get('pack_versions',[]) if q['id'] in v['question_ids']),None)
            independent=bool(version and version['kind']=='independent')
            append(id='study:'+a['id'], origin='study', episode=a['quiz_id'], question=q['id'],
                   family='study:'+doc['id']+':'+sha256(' '.join(q['prompt'].casefold().split()).encode()).hexdigest()[:20], skill='document:'+doc['id']+':'+q['topic'], role='follow_up' if independent else 'practice',
                   correct=a['correct'], helped=a['hint_count']>0, exposed='known' if independent or a['hint_count'] or any(e['kind']=='present' and e['activity_id']==a['quiz_id'] and e['item_id']==q['id'] for e in state.get('activity_events',[])) else 'unknown', effects={},
                   at=a['answered_at'], intervention=None, representation='text',confidence='unknown')
    if learner == 'My learning':
        for e in state.get('practice_events',[]):
            if e['action']!='retry': continue
            doc=next(d for d in state['documents'] if any(q['id']==e['question_id'] for q in d['questions']))
            q=next(q for q in doc['questions'] if q['id']==e['question_id'])
            append(id='study-support:'+e['id'],origin='study',episode=e['quiz_id'],question=q['id'],
                   family='study:'+doc['id']+':'+sha256(' '.join(q['prompt'].casefold().split()).encode()).hexdigest()[:20],skill='document:'+doc['id']+':'+q['topic'],role='retry',
                   correct=e['value']==q['correct_index'],helped=True,exposed='known',effects={},
                   at=e['at'],intervention='source_hint',representation='text',confidence='unknown')
    for session in state['nlm']['sessions']:
        if session['learner'] != learner:
            continue
        view = nlm.view(session)
        for index,r in enumerate(view['responses']):
            q=nlm.question(r['question_id']); effects={}
            # Explicit, versioned concept mappings; generic calculation errors remain ambiguous.
            if q['id'] in ('inertia-1','inertia-2','inertia-4'):
                if not r['correct'] and q['distractor_candidates'][str(r['selected_index'])]=='m01':
                    effects={'motion_force':'supports'}
                elif r['correct']: effects={'motion_force':'contradicts'}
            if q['id']=='second-3':
                if r['correct']: effects={'mass_rule':'contradicts'}
                elif r['selected_index']==2: effects={'mass_rule':'supports'}
            # Deliberately no arithmetic diagnosis from the old catch-all calculation tag.
            append(id='newton:'+session['id']+':'+str(index),origin='newton',episode=session['id'],
                   question=q['id'], family='newton:'+q['id'],skill='newton:'+q['concept_id'],
                   role='primary' if r['phase']=='primary' else r['phase'],correct=r['correct'],
                   helped=r['hints']>0,exposed='unknown',effects=effects,at=r['at'],intervention=None,
                   representation=q.get('representation','text'),confidence='unknown')
    for ep in state.get('debugger',{}).get('episodes',[]):
        if ep['learner'] != learner: continue
        q=None; helped=False; intervention=None
        for e in ep['events']:
            if e['action']=='present': q=QUESTIONS[e['value']['question_id']]; helped=False
            elif e['action'] in ('repair','alternate'): intervention=e['value']['hypothesis']
            elif e['action']=='help': helped=True
            elif e['action']=='answer':
                append(id='debugger:'+e['id'],origin='debugger',episode=ep['id'],question=q['id'],
                       family='debugger:'+q['family'],skill='debugger:'+q['topic'],role=q['role'],
                       correct=e['value']['option']==q['correct'],helped=helped,exposed='known',
                       effects=q['effects'].get(str(e['value']['option']),{}),at=e['at'],
                       intervention=intervention,representation=q['representation'],confidence=e['value']['confidence'])
    rows.sort(key=lambda r:datetime.fromisoformat(r['at']))
    # Repeated answers never become new independent observations.
    seen=set()
    for r in rows:
        r['repeat']=r['family'] in seen
        seen.add(r['family'])
    return rows


def exposed_questions(state, learner):
    """Exposure filtering stays active even when recommendation history is disabled."""
    result=set()
    for ep in state.get('debugger',{}).get('episodes',[]):
        if ep['learner']==learner:
            result.update(e['value']['question_id'] for e in ep['events'] if e['action']=='present')
    return result
