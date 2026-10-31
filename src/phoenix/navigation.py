"""Validated navigation targets; no widget writes occur in page renderers."""
from dataclasses import dataclass, asdict
from engine import require
from workspace import NLM_ID, NAVIGATION, navigation

LEARNERS=('My learning','Demo Learner A','Demo Learner B')


@dataclass(frozen=True)
class NavigationTarget:
    page: str
    material_id: str | None = None
    learner: str = 'My learning'
    activity_kind: str | None = None
    activity_id: str | None = None
    topic_id: str | None = None
    item_id: str | None = None
    card_view: str | None = None


def validate_target(state,target):
    if isinstance(target,dict): target=NavigationTarget(**target)
    require(isinstance(target,NavigationTarget) and target.page in NAVIGATION and target.learner in LEARNERS,'Invalid navigation target.')
    mids={d['id'] for d in state['documents']}|{NLM_ID}
    require(target.material_id in mids or target.material_id is None and target.page=='Library','This material is unavailable.')
    require(target.card_view in (None,'due','new','preview'),'Unknown card queue.')
    require(target.activity_kind in (None,'lesson','upload_quiz','newton_session','repair','cards','report'),'Unknown activity.')
    if target.activity_id:
        if target.activity_kind in ('upload_quiz','report') and target.material_id!=NLM_ID:
            q=next((q for q in state['quizzes'] if q['id']==target.activity_id),None)
            require(q and q['document_id']==target.material_id and target.learner=='My learning','Quiz belongs to another material.')
            require(target.item_id is None or target.item_id in q['question_ids'],'Item belongs to another quiz.')
        elif target.activity_kind in ('newton_session','report'):
            q=next((q for q in state['nlm']['sessions'] if q['id']==target.activity_id),None)
            require(q and target.material_id==NLM_ID and q['learner']==target.learner,'Session belongs to another learner or material.')
            import nlm
            concept=nlm.question(q['question_id'])['concept_id']
            require(target.topic_id is None or target.topic_id==concept,'Topic belongs to another session.')
            if target.item_id:require(nlm.question(target.item_id)['concept_id']==concept,'Item belongs to another session concept.')
        elif target.activity_kind=='repair':
            e=next((e for e in state['debugger']['episodes'] if e['id']==target.activity_id),None)
            require(e and e['learner']==target.learner and (e['origin']['document_id'] if e['origin'] else NLM_ID)==target.material_id,'Repair belongs to another learner or material.')
        else: require(False,'Activity is incompatible with this route.')
    if target.material_id!=NLM_ID: require(target.learner=='My learning','Uploads belong to My learning.')
    if target.item_id and target.activity_kind=='cards':
        import nlm
        valid=any(c['id']==target.item_id for c in nlm.load_pack()['flashcards']) if target.material_id==NLM_ID else any(c['id']==target.item_id and c['document_id']==target.material_id for c in state['cards'])
        require(valid,'Card belongs to another material.')
    elif target.item_id and not target.activity_id:require(False,'Item needs a compatible saved activity.')
    if target.topic_id:
        require(target.material_id is not None,'A topic needs its material.')
        if target.material_id==NLM_ID:
            import nlm
            require(target.topic_id in {c['id'] for c in nlm.load_pack()['concepts']},'Unknown concept.')
        else:
            d=next(d for d in state['documents'] if d['id']==target.material_id)
            require(target.topic_id in d['topics'],'Unknown source-local topic.')
    return target


def request_navigation(session,target):
    session['navigation_pending']=asdict(target) if isinstance(target,NavigationTarget) else target


def apply_navigation(session,state):
    pending=session.pop('navigation_pending',None)
    if pending is None: return
    target=validate_target(state,pending)
    session['study_nav']=target.page
    session['study_material']=target.material_id or NLM_ID
    session['nlm_learner']=target.learner; session['debugger_learner']=target.learner
    session['study_repair']=target.activity_kind=='repair'
    session.pop('study_feedback',None)
    if target.activity_id:
        if target.activity_kind in ('upload_quiz','report') and target.material_id!=NLM_ID: session['study_quiz_id']=target.activity_id
        elif target.activity_kind in ('newton_session','report'):
            session['nlm_active_'+target.learner]=target.activity_id
            session['nlm_choose_'+target.learner]=next(s['question_id'] for s in state['nlm']['sessions'] if s['id']==target.activity_id)
        elif target.activity_kind=='repair': session['debugger_active_'+target.learner]=target.activity_id
    session['study_topic']=target.topic_id
    if target.card_view:
        label={'due':'Due reviews','new':'New cards','preview':'Preview all'}[target.card_view]
        session['study_card_view']=label; session['nlm_card_view']=label
    if target.material_id==NLM_ID:
        if target.topic_id:
            from journey import UNITS
            session['nlm_unit']=next(u for u in UNITS if target.topic_id in u['concepts']);session['nlm_concept']=target.topic_id
        session['study_nlm_open']=True
        session['nlm_tab']={'Quiz':'Practice','Flash Cards':'Flashcards','Insights':'Evidence'}.get(target.page,'Learn visually')


def encode_target(target):
    return {k:v for k,v in asdict(target).items() if v is not None}


def decode_target(state,params):
    # Only allow opaque context and fixed route fields from URLs.
    page=navigation(params.get('page','Dashboard'))
    if params.get('material',NLM_ID)==NLM_ID and params.get('page') in ('Library','Newton’s Laws'):
        page={'Practice':'Quiz','Flashcards':'Flash Cards','Evidence':'Insights'}.get(params.get('lesson'),page)
    return validate_target(state,NavigationTarget(page=page,
        material_id=params.get('material',NLM_ID),learner=params.get('learner','My learning'),
        activity_kind=params.get('activity_kind','repair' if params.get('repair') else None),activity_id=params.get('activity',params.get('repair')),
        card_view=params.get('card_view'),topic_id=params.get('topic')))
