"""Four data-driven Newton units and read-only student journey selectors."""
import re
import nlm

UNITS = (
    dict(id='laws', title='1 · Forces and Newton’s laws', concepts=('inertia','second','third'), outcome='Distinguish motion from force, calculate acceleration, identify interaction pairs.'),
    dict(id='systems', title='2 · Free-body diagrams and systems', concepts=('normal','tension','equilibrium'), outcome='Choose a system, draw its forces and resolve balanced interactions.'),
    dict(id='friction', title='3 · Friction and circular motion', concepts=('static','kinetic','circular','roads'), outcome='Check sticking versus sliding and explain the inward resultant on a turn.'),
    dict(id='momentum', title='4 · Momentum and impulse', concepts=('momentum','impulse'), outcome='Connect force-time area to momentum change and conservation.'),
)
KEYWORDS = {
 'inertia': ('inertia','first law'), 'second': ('acceleration','second law','f = ma'),
 'third': ('third law','reaction','interaction pair'), 'normal': ('normal force','free-body','free body'),
 'tension': ('tension','pulley'), 'equilibrium': ('equilibrium','balanced forces'),
 'static': ('static friction','coefficient of friction'), 'kinetic': ('kinetic friction','rolling friction'),
 'circular': ('circular','centripetal'), 'roads': ('banked','banking','level road'),
 'momentum': ('momentum','collision'), 'impulse': ('impulse','force-time','force time'),
}

def note_sections(state, concept_id):
    """Explicit phrase matches are reading suggestions, never diagnostic evidence."""
    rows=[]
    for d in state['documents']:
        for chunk in d['chunks']:
            text=chunk['text'].lower()
            hits=[term for term in KEYWORDS[concept_id] if re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',text)]
            if hits:
                rows.append(dict(document_id=d['id'], title=d['title'], chunk_id=chunk['id'],
                                 page=chunk['page'], text=chunk['text'], matches=hits))
    return sorted(rows,key=lambda r:-len(r['matches']))[:4]

def journey(state, learner='My learning'):
    """Rebuild stages from persisted responses; no fabricated completion counters."""
    pack=nlm.load_pack(); rows=[]
    for concept in pack['concepts']:
        cid=concept['id']
        sessions=[s for s in state['nlm']['sessions'] if s['learner']==learner and nlm.question(s['question_id'])['concept_id']==cid]
        views=[nlm.view(s) for s in sessions]
        checked=any(v.get('step') in ('COMPLETE','TRANSFER','DELAYED_REVIEW') for v in views)
        pending=any(v['step'] not in ('COMPLETE','RECAP') for v in views)
        stage='Continue practice' if pending else 'Review and transfer' if checked else 'Revisit lesson' if sessions else 'Learn and predict'
        seen={s['question_id'] for s in sessions}
        primary=[q for q in pack['questions'] if q['concept_id']==cid and q['role']=='primary']
        qid=next((s['question_id'] for s in reversed(sessions) if nlm.view(s)['step'] not in ('COMPLETE','RECAP')), next((q['id'] for q in primary if q['id'] not in seen),primary[0]['id']))
        rows.append(dict(id=cid,title=concept['title'],stage=stage,question_id=qid,sessions=len(sessions),notes=note_sections(state,cid)))
    return rows
