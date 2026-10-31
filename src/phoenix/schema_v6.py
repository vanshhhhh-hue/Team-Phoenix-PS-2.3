"""Closed, additive checkpoint metadata. Legacy evidence is never rewritten."""
from copy import deepcopy
from datetime import datetime
from uuid import UUID, uuid4
import hashlib
import json
from engine import require

EXTRA = {'workspace_id','revision','last_saved_at','material_meta','pack_versions',
         'activity_events','item_status','drafts','preferences','command_receipts'}
LEGACY = {'schema_version','documents','quizzes','attempts','cards','reviews','nlm','debugger','practice_events'}


def aware(value):
    require(type(value) is str and len(value)<=64, 'Invalid timestamp.')
    dt=datetime.fromisoformat(value)
    require(dt.tzinfo is not None and dt.utcoffset() is not None, 'Timestamp requires an offset.')
    return dt


def register_pack(state, doc, count=None, difficulty=None,selected=None,quality=None):
    did=doc['id']
    state['pack_versions'].append(dict(id=did+':v1',document_id=did,version=1,mode=doc['mode'],kind='ordinary',origin_item_id=None,
        summary=doc['summary'],topics=list(doc['topics']),question_ids=[q['id'] for q in doc['questions']],
        card_ids=[c['id'] for c in state['cards'] if c['document_id']==did],
        source_ids=list(dict.fromkeys(q['source_chunk_id'] for q in doc['questions'])),
        selected_source_ids=[c['id'] for c in (selected or doc['chunks'])],
        quality=quality or dict(source_references='validated',local_keys='validated' if doc['mode']=='local' else 'not independently verified',semantic_review='not performed',authored_review=False,question_count=len(doc['questions']),card_count=sum(c['document_id']==did for c in state['cards'])),
        requested_count=count,requested_difficulty=difficulty,created_at=doc['created_at']))
    state['material_meta'][did]=dict(visibility='history' if (did,doc['created_at']) in __import__('workspace').HISTORICAL_DOCUMENTS else 'active',title=None,active_pack=did+':v1')


def upgrade_v5(data):
    require(set(data)==LEGACY,'Malformed schema-v5 backup.')
    state=deepcopy(data)
    state.update(schema_version=6,workspace_id=str(uuid4()),revision=0,last_saved_at=None,
        material_meta={},pack_versions=[],activity_events=[],item_status={},drafts=[],preferences={},command_receipts=[])
    for doc in state['documents']: register_pack(state,doc)
    return state


def validate_extensions(s):
    require(type(s['workspace_id']) is str and str(UUID(s['workspace_id']))==s['workspace_id'], 'Invalid workspace identity.')
    require(type(s['revision']) is int and s['revision']>=0,'Invalid workspace revision.')
    if s['last_saved_at'] is not None: aware(s['last_saved_at'])
    require(s['revision']==0 or s['last_saved_at'] is not None,'Installed revisions need a save time.')
    docs={d['id']:d for d in s['documents']}
    require(type(s['material_meta']) is dict and set(s['material_meta'])<=set(docs)|{'authored:nlm-jee-2026'},'Invalid material metadata.')
    for mid,m in s['material_meta'].items():
        require(type(m) is dict and set(m)=={'visibility','title','active_pack'} and m['visibility'] in ('active','history','archived'),'Invalid material fields.')
        require(m['title'] is None or type(m['title']) is str and 0<len(m['title'].strip())<=100,'Invalid material title.')
    require(type(s['pack_versions']) is list and len(s['pack_versions'])<=200,'Invalid pack versions.')
    versions={}
    for v in s['pack_versions']:
        require(type(v) is dict and set(v)=={'id','document_id','version','mode','kind','origin_item_id','summary','topics','question_ids','card_ids','source_ids','selected_source_ids','quality','requested_count','requested_difficulty','created_at'},'Invalid pack descriptor.')
        require(v['document_id'] in docs and v['id'] not in versions and type(v['version']) is int and v['version']>=1,'Invalid pack identity.')
        d=docs[v['document_id']]; versions[v['id']]=v
        require(v['kind'] in ('ordinary','independent') and (v['origin_item_id'] is None if v['kind']=='ordinary' else v['mode']=='gemini' and v['origin_item_id'] in {q['id'] for q in d['questions']}),'Invalid pack role or origin.')
        require(v['mode'] in ('local','gemini') and type(v['summary']) is str and len(v['summary'])<=10000 and type(v['topics']) is list and all(type(t) is str and t in d['topics'] for t in v['topics']),'Invalid pack snapshot.')
        for key,pool in [('question_ids',{q['id'] for q in d['questions']}),('card_ids',{c['id'] for c in s['cards'] if c['document_id']==d['id']}),('source_ids',{c['id'] for c in d['chunks']}),('selected_source_ids',{c['id'] for c in d['chunks']})]:
            require(type(v[key]) is list and len(v[key])==len(set(v[key])) and set(v[key])<=pool,'Invalid pack references.')
        require(v['requested_count'] is None or type(v['requested_count']) is int and 3<=v['requested_count']<=10,'Invalid requested count.')
        require(v['requested_difficulty'] in (None,'mixed','easy','medium','hard'),'Invalid requested difficulty.')
        quality=v['quality']
        require(type(quality) is dict and set(quality)=={'source_references','local_keys','semantic_review','authored_review','question_count','card_count'} and quality['source_references']=='validated' and quality['local_keys'] in ('validated','not independently verified') and quality['semantic_review'] in ('not performed','passed') and quality['authored_review'] is False and quality['question_count']==len(v['question_ids']) and quality['card_count']==len(v['card_ids']),'Invalid quality report.')
        aware(v['created_at'])
    for mid,m in s['material_meta'].items():
        require(m['active_pack'] is None or m['active_pack'] in versions and versions[m['active_pack']]['document_id']==mid,'Invalid active pack.')
    from study_flow import validate_activity_events, validate_drafts
    validate_activity_events(s); validate_drafts(s)
    # These namespaces are reserved until a closed command/validator is implemented.
    require(type(s['item_status']) is dict and len(s['item_status'])<=5000 and type(s['preferences']) is dict and set(s['preferences'])<= {'use_ai','source_preview','last_material','last_context'} and ('use_ai' not in s['preferences'] or type(s['preferences']['use_ai']) is bool),'Invalid item status or unsupported preference fields.')
    if 'last_material' in s['preferences']:require(s['preferences']['last_material'] in set(docs)|{'authored:nlm-jee-2026'},'Invalid saved material.')
    if 'last_context' in s['preferences']:
        from navigation import validate_target,LEARNERS
        contexts=s['preferences']['last_context'];require(type(contexts) is dict and set(contexts)<=set(LEARNERS),'Invalid saved route contexts.')
        for learner,target in contexts.items():require(validate_target(s,target).learner==learner,'Invalid route owner.')
    if 'source_preview' in s['preferences']:
        from content_quality import validate_source_draft
        validate_source_draft(s['preferences']['source_preview'])
    items={q['id'] for d in s['documents'] for q in d['questions']}|{c['id'] for c in s['cards']}
    for item,status in s['item_status'].items():
        require(item in items and type(status) is dict and set(status)=={'status','reason','feedback','at'},'Invalid item status context.')
        require(status['status'] in ('disputed','quarantined','retired') and status['reason'] in ('answer seems wrong','ambiguous choices','missing source support','explanation unclear','other'),'Invalid item status.')
        require(type(status['feedback']) is str and len(status['feedback'])<=1000,'Invalid item feedback.'); aware(status['at'])
    require(type(s['command_receipts']) is list and len(s['command_receipts'])<=256,'Invalid receipts.')
    seen=set()
    for r in s['command_receipts']:
        require(type(r) is dict and set(r)=={'id','hash','revision'} and type(r['id']) is str and 0<len(r['id'])<=100 and r['id'] not in seen,'Invalid command receipt.')
        seen.add(r['id'])
        require(type(r['hash']) is str and len(r['hash'])==64 and all(c in '0123456789abcdef' for c in r['hash']) and type(r['revision']) is int and 0<r['revision']<=s['revision'],'Invalid receipt result.')
