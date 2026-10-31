"""Phoenix: the main uploaded-material learning experience."""
from datetime import datetime
from html import escape
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import os
from demo import load_demo

import streamlit as st

from ai_provider import ProviderError, connection_check, settings
from engine import DomainError
from ledger import clock
from presentation import date_label
from storage import read_workspace, commit_snapshot, prepare_restore, apply_restore, storage_usage
from study_flow import hint_level, show_hint, submit_answer, upload_activity_view, save_draft
from content_quality import source_preview, flag_item
from study import STATE_PATH, regenerate_document
from followups import build_followup
from navigation import NavigationTarget, request_navigation as queue_navigation, apply_navigation, decode_target, validate_target
from study import (add_document, answer_question, export_state, get_document, get_question,
                   grade_card, import_state, load_state, new_state, recommendations, save_state,
                   start_quiz, topic_stats, migrate_state, validate_state, practice_view, practice_event)
import nlm
import nlm_app
from journey import UNITS, journey
import debugger as debugger_domain
import debugger_app
from workspace import default_material,card_queue, pending_tasks, recommend_next, update_material, NLM_ID, NAVIGATION, materials, navigation, report

LOGO = Path(__file__).resolve().parents[2] / "assets/phoenix-logo.jpeg"

st.set_page_config(page_title='Phoenix · Your learning workspace', page_icon=str(LOGO), layout='wide')
st.markdown('''<style>
.block-container{max-width:1120px;padding-top:2rem;padding-bottom:4rem}
h1{letter-spacing:-.025em;font-weight:700!important;font-size:2rem!important}
@media(max-width:600px){button,[data-testid="stRadio"] label{min-height:44px!important}.block-container{padding:1rem!important}[data-testid=stForm]{padding:12px!important}h1{font-size:1.6rem!important}}
h2,h3{letter-spacing:-.025em}
[data-testid="stSidebar"]{border-right:1px solid #dce5ec}
[data-testid="stMetricLabel"] p{white-space:normal!important;overflow:visible!important}
[data-testid="stMetricValue"]{font-size:1.65rem!important}
[data-testid="stMetric"]{background:white;border:1px solid #dfe6ed;border-radius:8px;padding:18px}
[data-testid="stForm"]{background:white;border:1px solid #dfe6ed;border-radius:8px;padding:24px}
.eyebrow{color:#087f74;letter-spacing:.16em;font-size:.73rem;font-weight:600;text-transform:uppercase}
.subtitle{font-size:1.1rem;color:#59677c;line-height:1.7;max-width:780px;margin-bottom:1.6rem}
.brand{font-weight:600;font-size:1.6rem;letter-spacing:-.05em;color:#17253d}
.brand span{color:#087f74}
.topic-tile{border:1px solid #dce5ec;border-radius:8px;padding:16px;margin:8px 0;min-height:125px}
.topic-tile strong{font-size:1rem}.topic-tile p{font-size:1.7rem;font-weight:600;margin:8px 0}
.flow{color:#637087;font-size:.8rem;letter-spacing:.05em;margin:1rem 0 2rem}
</style>''', unsafe_allow_html=True)

def recovery_screen(result):
    st.title('Recover your workspace')
    if result.code=='workspace_busy':
        st.warning('The workspace is busy saving in another process. Wait a moment and retry opening it.')
        if st.button('Retry opening workspace'):st.rerun()
        st.stop()
    st.error('Your saved workspace could not be opened. The file has been kept.')
    if STATE_PATH.exists():
        try:st.download_button('Download original recovery file', STATE_PATH.read_bytes(), 'phoenix-unreadable-recovery.json')
        except OSError:st.info('The recovery file cannot currently be read. It has been kept on disk.')
    for checkpoint in result.checkpoints:
        try:st.download_button('Download previous valid checkpoint', Path(checkpoint).read_bytes(), 'phoenix-previous-backup.json')
        except OSError:st.info('The previous checkpoint cannot currently be downloaded.')
    recovery_file=st.file_uploader('Validated study backup',type=['json'],key='recovery_backup')
    if st.button('Preview recovery backup',disabled=recovery_file is None):
        try: st.session_state.restore_preview=prepare_restore(STATE_PATH,recovery_file.getvalue())
        except (DomainError,OSError,UnicodeError) as exc: st.error(str(exc))
    if st.checkbox('I have saved the recovery file and want an empty workspace',key='recovery_new_confirm'):
        if st.button('Preview new empty workspace'):
            st.session_state.restore_preview=prepare_restore(STATE_PATH,export_state(new_state()).encode('utf-8'))
    restore_controls()
    st.stop()


def restore_controls():
    preview=st.session_state.get('restore_preview')
    if preview:
        st.write('Validated backup:',preview.counts)
        st.write('Current work to replace:',preview.current_counts)
        st.caption('Includes uploaded notes, quizzes, cards, Newton and debugger progress. Excludes algebra lab and credentials.')
        st.caption('Backup saved: '+str(preview.saved_at or 'unknown'))
        if st.button('Confirm replacement with this backup',key='confirm_restore'):
            result=apply_restore(STATE_PATH,preview,preview.revision)
            if result.status=='committed':
                # Clear volatile reveals, feedback and widget selections after workspace replacement.
                for key in list(st.session_state):
                    if key not in ('study_persist',): del st.session_state[key]
                st.session_state.study=result.state; st.rerun()
            else: st.error(result.message)


if 'study' not in st.session_state and 'study_persist' not in st.session_state:
    mode = os.getenv('PHOENIX_MODE', 'demo').lower()
    if mode not in ('demo', 'local'):
        st.error('PHOENIX_MODE must be demo or local.'); st.stop()
    st.session_state.study_persist = mode == 'local'
    st.session_state.demo_workspace = mode == 'demo'
    if mode == 'demo':
        st.session_state.study = load_demo()

if 'study' not in st.session_state:
    if st.session_state.get('study_persist',True):
        loaded=read_workspace(STATE_PATH)
        if loaded.status!='ready': recovery_screen(loaded)
        st.session_state.study=loaded.state
    else: st.session_state.study=new_state()
elif st.session_state.study.get('schema_version') in (2,3,4,5):
    st.session_state.study=validate_state(migrate_state(st.session_state.study))
if 'study_nav' not in st.session_state:
    try:
        queue_navigation(st.session_state,decode_target(st.session_state.study,dict(st.query_params) if st.query_params else {'page':'Dashboard','material':default_material(st.session_state.study)}))
    except (DomainError,TypeError,ValueError):
        st.session_state.study_notice='That link is unavailable. Choose your material from the Library.'
        queue_navigation(st.session_state,NavigationTarget('Library',None))
    st.session_state.study_nav = navigation(st.query_params.get('page','Dashboard'))
    st.session_state.study_material = st.query_params.get('material',default_material(st.session_state.study))
    tab_hint=st.query_params.get('lesson')
    if tab_hint in ('Learn visually','Practice','Flashcards','Evidence','Sources'):
        st.session_state.nlm_tab=tab_hint
        st.session_state.study_nlm_open=True
    repair_hint=st.query_params.get('repair')
    if repair_hint and any(e['id']==repair_hint and e['learner']=='My learning' for e in st.session_state.study['debugger']['episodes']):
        st.session_state.study_repair=True
        st.session_state['debugger_active_My learning']=repair_hint
incoming = st.session_state.pop('study_next_page', st.session_state.study_nav)
if incoming == 'Debugger':
    st.session_state.study_repair = True
elif incoming == 'Newton’s Laws':
    st.session_state.study_material = NLM_ID
    st.session_state.study_nlm_open = True
st.session_state.study_nav = navigation(incoming)
if 'nlm_next_tab' in st.session_state:
    selected_tab=st.session_state.pop('nlm_next_tab')
    st.session_state.nlm_tab=selected_tab
    st.session_state.study_nav={'Practice':'Quiz','Flashcards':'Flash Cards','Evidence':'Insights'}.get(selected_tab,'Library')
try:
    apply_navigation(st.session_state,st.session_state.study)
except (DomainError,TypeError,ValueError) as exc:
    st.session_state.study_notice=str(exc)
if 'study_use_ai' not in st.session_state:
    st.session_state.study_use_ai = st.session_state.study['preferences'].get('use_ai',bool(settings().key))


def primary_navigation():
    if st.session_state.study_nav=='Dashboard':
        st.session_state.nlm_learner='My learning';st.session_state.debugger_learner='My learning'


def change_page(page):
    st.session_state.nlm_learner='My learning'
    st.session_state.debugger_learner='My learning'
    if page == 'Debugger':
        st.session_state.study_repair = False
        selected=st.session_state.get('study_material',NLM_ID)
        current=st.session_state.study
        if selected!=NLM_ID:
            doc=next((d for d in current['documents'] if d['id']==selected),None)
            wrong=next((a for a in reversed(current['attempts']) if doc and not a['correct'] and any(q['id']==a['question_id'] for q in doc['questions'])),None)
            if wrong:
                updated,sid=debugger_domain.start(current,'upload',origin={'document_id':selected,'question_id':wrong['question_id']})
                commit(updated)
                st.session_state['debugger_active_My learning']=sid
                st.session_state.study_repair=True
            else: st.session_state.study_notice='No eligible mistake is saved for this material. Start practice first.'
        else:
            matching=[e for e in current['debugger']['episodes'] if e['learner']=='My learning' and e['topic']!='upload']
            st.session_state.study_repair=True
            if matching: st.session_state['debugger_active_My learning']=matching[-1]['id']
    if page != 'Debugger':
        st.session_state.study_repair = False
    st.session_state.study_next_page = 'Quiz' if page=='Debugger' else page
    if page=='Flash Cards':
        st.session_state.study_card_view='Due reviews'; st.session_state.nlm_card_view='Due reviews'


def open_lab():
    st.session_state.workspace_view = 'Lab'


def commit(updated):
    if st.session_state.get('study_persist',True):
        result=commit_snapshot(STATE_PATH,st.session_state.study,updated)
        if result.status not in ('committed','already_applied'):
            if result.status=='conflict' and result.state is not None:
                st.session_state.study=result.state
            st.error(result.message)
            st.stop()
        updated=result.state
    st.session_state.study=updated



def request_navigation(session,target):
    from copy import deepcopy
    from dataclasses import asdict
    validated=validate_target(session.study,target)
    updated=deepcopy(session.study)
    if validated.material_id:updated['preferences']['last_material']=validated.material_id
    if validated.page!='Dashboard':updated['preferences'].setdefault('last_context',{})[validated.learner]=asdict(validated)
    commit(updated)
    queue_navigation(session,validated)


def selected_material_changed():
    from copy import deepcopy
    updated=deepcopy(st.session_state.study)
    updated['preferences']['last_material']=st.session_state.study_material
    commit(updated)


def save_ai_preference():
    from copy import deepcopy
    updated=deepcopy(st.session_state.study)
    updated['preferences']['use_ai']=st.session_state.study_use_ai
    commit(updated)


def build(title,filename,payload,count=6,difficulty='mixed'):
    try:
        preview=source_preview(filename,payload)
        from copy import deepcopy
        updated=deepcopy(st.session_state.study)
        updated['preferences']['source_preview']=dict(title=title,filename=filename[:150],count=count,difficulty=difficulty,text=preview['text'],chunks=preview['chunks'])
        commit(updated)
        st.session_state.pop('preview_sections',None)
        st.session_state.source_build_preview=dict(title=title,filename=filename,payload=payload,count=count,difficulty=difficulty,preview=preview)
        st.rerun()
    except (DomainError,OSError) as exc: st.error(str(exc))


def promote_preview(pending):
    try:
        with st.spinner('Building a study pack from the inspected source…'):
            updated,doc_id,message=add_document(st.session_state.study,pending['title'],pending['filename'],pending['payload'],
                pending['count'],pending['difficulty'],st.session_state.study_use_ai,source_ids=st.session_state.get('preview_sections'),extracted=(pending['preview']['text'],pending['preview']['chunks']))
        updated['preferences'].pop('source_preview',None)
        updated['preferences']['last_material']=doc_id
        commit(updated)
        st.session_state.pop('source_build_preview',None)
        st.session_state.study_next_document=doc_id; st.session_state.study_notice=message
        st.rerun()
    except (DomainError,OSError) as exc: st.error(str(exc))


state = st.session_state.study
documents = state['documents']
material_list = materials(state)
material_labels = {m['id']: m['title'] + (' · '+m['visibility'].title() if m['visibility']!='active' else '') for m in material_list}
if 'study_next_document' in st.session_state:
    selected = st.session_state.pop('study_next_document')
    st.session_state.study_document = selected
    st.session_state.study_material = selected
if st.session_state.get('study_material') not in material_labels:
    st.session_state.study_material = NLM_ID

with st.sidebar:
    st.image(str(LOGO), width=110)
    st.markdown('<div class="brand">Phoenix</div>', unsafe_allow_html=True)
    st.caption('Study from your notes')
    if st.session_state.get('demo_workspace'):
        st.markdown('**User 1** · Sample workspace')
        st.caption('Fictional study history. Changes stay in this browser session; no sign-in required.')
    else:
        st.caption('Personal workspace · local storage')
    st.radio('Navigate', NAVIGATION, key='study_nav',on_change=primary_navigation)
    st.divider()
    show_history = st.checkbox('Show historical or archived materials', key='show_material_history')
    visible = [m['id'] for m in material_list if m['visibility']=='active' or show_history or m['id']==st.session_state.study_material]
    st.selectbox('Selected material', visible, format_func=material_labels.get, key='study_material',on_change=selected_material_changed)
    archived=[m for m in material_list if m['visibility']=='archived']
    if archived:
        archived_due=sum(card_queue(state,m['id'])['due_count'] for m in archived)
        st.caption(f'{len(archived)} archived materials · {archived_due} scheduled cards due. Show archived materials to reopen saved work.')
    with st.expander('Workspace settings'):
        st.toggle('Use Gemini when available', key='study_use_ai',on_change=save_ai_preference)
        st.caption('AI mode sends selected source excerpts to Google when you build a pack. Local mode keeps generation on this PC.')
        with st.expander('AI connection'):
            config = settings()
            st.write('Key configured' if config.key else 'No key found — local mode available')
            st.caption('Model: ' + config.model)
            if st.button('Test Gemini connection'):
                try:
                    if connection_check():
                        st.success('Configured model supports generation. A successful generation has not been verified by this check.')
                    else:
                        st.warning('No usable content-generation model found.')
                except ProviderError as exc:
                    st.warning(str(exc))
        st.divider()
        st.button('🧪 Open Misconception Lab', on_click=open_lab, width='stretch')
        st.caption('A supporting, authored algebra experiment — not the whole app.')
        st.divider()
        st.download_button('Export study backup ↓', export_state(state), 'phoenix-study-backup.json',
                           'application/json', width='stretch')
        if st.session_state.get('study_persist', True):
            with st.expander('Restore a backup'):
                st.caption('Backups include your extracted notes and progress, never API keys.')
                backup = st.file_uploader('Study backup JSON (up to 8 MB)', type=['json'], key='study_backup')
                if st.button('Preview study backup'):
                    try:
                        if backup is None: raise DomainError('invalid_progress','Choose a study backup first.')
                        st.session_state.restore_preview=prepare_restore(STATE_PATH,backup.getvalue())
                    except (DomainError,UnicodeError,OSError) as exc: st.error(str(exc))
                restore_controls()
                undo_path=STATE_PATH.with_suffix(STATE_PATH.suffix+'.pre-restore')
                if undo_path.exists() and st.button('Preview undo of last restore'):
                    try:
                        st.session_state.restore_preview=prepare_restore(STATE_PATH,undo_path.read_bytes()); st.rerun()
                    except (DomainError,OSError,UnicodeError) as exc: st.error(str(exc))
        usage=storage_usage(state)
        st.caption(f"Storage: {usage['bytes']/1048576:.2f} / 8 MiB. Study backups exclude the algebra lab; export it inside the lab.")
        if usage['level']!='normal': st.warning('Storage is nearly full. Export a backup before adding more material.')
        if st.session_state.get('study_persist', True):
            with st.expander('Export and start a new workspace'):
                st.caption('Keep the complete study backup before replacing this workspace. A recoverable checkpoint is retained; archiving alone does not free bytes.')
                st.download_button('Download complete workspace before rollover',export_state(validate_state(state)),'phoenix-workspace-archive.json','application/json',key='rollover_backup')
                ready=st.checkbox('I have saved the complete backup and want a new empty workspace',key='rollover_confirm')
                if st.button('Preview new workspace',disabled=not ready):
                    st.session_state.restore_preview=prepare_restore(STATE_PATH,export_state(new_state()).encode('utf-8')); st.rerun()
        elif st.button('Reset User 1 sample workspace'):
            for key in list(st.session_state):
                del st.session_state[key]
            st.rerun()
    st.caption('User 1 · session-only sample data' if st.session_state.get('demo_workspace') else 'Single-student workspace · saved locally on this PC')

document_id = st.session_state.study_material if st.session_state.study_material != NLM_ID else None
document = get_document(state, document_id) if document_id else None
page = st.session_state.study_nav
is_nlm = st.session_state.study_material == NLM_ID
if st.session_state.get('previous_material',st.session_state.study_material)!=st.session_state.study_material:
    st.session_state.study_repair=False
    st.session_state.pop('study_feedback',None)
st.session_state.previous_material=st.session_state.study_material


def hero(number, title, subtitle):
    st.markdown(f'<div class="eyebrow">{escape(number)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="subtitle">{escape(subtitle)}</div>', unsafe_allow_html=True)


def require_document():
    if document is None:
        st.info('Upload notes or try the sample material to unlock this workspace.')
        st.button('Add study material →', on_click=change_page, args=('Library',), type='primary')
        return False
    return True


def open_nlm(tab='Learn visually'):
    current=st.session_state.study
    updated=nlm.install(current)
    updated['preferences']['last_material']=NLM_ID
    commit(updated)
    st.session_state.study_next_document = NLM_ID
    st.session_state.nlm_learner = 'My learning'
    st.session_state.study_nlm_open = True
    st.session_state.nlm_next_tab = tab
    st.session_state.study_next_page = {'Practice':'Quiz', 'Flashcards':'Flash Cards', 'Evidence':'Insights'}.get(tab,'Library')
    st.rerun()


def topic_journey():
    st.subheader('Sample material learning journey')
    st.caption('Learn → predict → practise → repair → fresh check → spaced recall. Stages come from your saved work; opening a lesson does not count as completion.')
    rows={r['id']:r for r in journey(state)}
    for unit in UNITS:
        with st.expander(unit['title'],expanded=False):
            st.write(unit['outcome'])
            for cid in unit['concepts']:
                row=rows[cid]
                st.markdown('**'+row['title']+'** · '+row['stage'])
                st.caption(str(row['sessions'])+' saved practice session(s) · '+str(len(row['notes']))+' matching uploaded source section(s)')
                a,b=st.columns(2)
                if a.button('Learn '+row['title'],key='journey_learn_'+cid):
                    if not state['nlm']['installed']:commit(nlm.install(st.session_state.study))
                    request_navigation(st.session_state,NavigationTarget('Library',NLM_ID,activity_kind='lesson',topic_id=cid));st.rerun()
                if b.button('Continue '+row['title']+' practice',key='journey_practice_'+cid):
                    updated,sid=nlm.start(nlm.install(st.session_state.study),row['question_id'])
                    commit(updated)
                    request_navigation(st.session_state,NavigationTarget('Quiz',NLM_ID,activity_kind='newton_session',activity_id=sid,topic_id=cid));st.rerun()



def report_summary(r):
    cols=st.columns(3)
    cols[0].metric('First answers correct',f"{r['correct']}/{r['attempted']}" if r['attempted'] else 'No answers yet')
    cols[1].metric('Cards due · new',f"{r['due_cards']} · {r['new_cards']}")
    cols[2].metric('Continue or review',r['pending'])
    st.caption(f"{r['attempted']} first answers across {len(r['topics'])} topics · {r['upcoming']} upcoming checks")


def recent_reports(r):
    st.subheader('Recent quiz reports')
    for q in r['quizzes'][:8]:
        with st.container(border=True):
            st.write(f"{material_labels[q['material_id']]} · {q['correct']}/{q['attempted']} · {q['hints']} hint levels before first answers")
            st.caption(f"Recovery: {q['recovery_hints']} hint levels · {q['recovery_retries']} retries · {'complete' if q['recovery_complete'] else 'unfinished'}")
            st.caption(date_label(q['date']) + ' · ' + ('completed' if q['completed'] else 'in progress'))
            if st.button('Review / resume · '+material_labels[q['material_id']]+' · '+date_label(q['date']), key='report_'+q['id']):
                request_navigation(st.session_state,NavigationTarget('Quiz',q['material_id'],activity_kind='newton_session' if q['material_id']==NLM_ID else 'upload_quiz',activity_id=q['id']))
                if q['material_id']==NLM_ID:
                    st.session_state['nlm_active_My learning']=q['id']
                    st.session_state.nlm_next_tab='Practice'
                else:
                    st.session_state.study_quiz_id=q['id']
                    st.session_state.pop('study_feedback',None)
                st.session_state.study_next_page='Quiz'; st.rerun()
    if not r['quizzes']: st.info('No saved quiz reports for this scope yet. Start a practice question.')


def dashboard():
    hero('YOUR WORKSPACE', 'Start studying' if not any(m['kind']=='uploaded' and m['visibility']=='active' for m in material_list) and not state['nlm']['sessions'] else 'Your study workspace',
         'Continue a quiz, review scheduled cards, or add new study material.')
    if st.session_state.get('demo_workspace'):
        st.info('User 1 · Fictional sample data. Reports below are calculated from saved sample answers and reviews.')
    if not any(m['kind']=='uploaded' and m['visibility']=='active' for m in material_list):
        st.button('Add your notes',on_click=change_page,args=('Library',),type='primary')
    if not any(m['kind']=='uploaded' and m['visibility']=='active' for m in material_list) and not state['nlm']['sessions'] and not state['debugger']['episodes']:
        st.caption('Text-based PDF, TXT or Markdown. Review extracted text before building practice.')
        if st.button('Try sample material'):open_nlm()
        return
    for col, target in zip(st.columns(4), ['Library','Quiz','Flash Cards','Insights']):
        col.button(target+' →', on_click=change_page, args=(target,), width='stretch')
    r=report(state,st.session_state.study_material); report_summary(r)
    st.subheader('Topic performance')
    if r['topics']: st.dataframe([{k:v for k,v in t.items() if k!='topic_id'} for t in r['topics']],hide_index=True,width='stretch')
    else: st.info('No first responses saved for this material yet.')
    st.subheader('Recommended next activity')
    if r['pending']:
        st.write(f"{r['pending']} unfinished repairs or due checks: resume your saved work before starting a new round.")
    elif any(t['status']=='needs practice' for t in r['topics']):
        st.write('Practise '+next(t['topic'] for t in r['topics'] if t['status']=='needs practice')+' — under 70% correct across at least three first responses.')
    elif r['due_cards']:
        st.write(f"Recall {r['due_cards']} scheduled cards due now.")
    else: st.write('Start an unseen question to collect first-response evidence.')
    for index,action in enumerate(recommend_next(state,st.session_state.study_material)[:3]):
        if st.button(action['reason_text'],key='recommended_'+str(index)):
            request_navigation(st.session_state,action['target']); st.rerun()
    if not recommend_next(state,st.session_state.study_material):
        st.button('Practise '+material_labels[st.session_state.study_material],on_click=change_page,args=('Quiz',))
    st.button('Review due cards →',on_click=change_page,args=('Flash Cards',))
    st.button('Understand this mistake',on_click=change_page,args=('Debugger',))
    recent_reports(r)
    if is_nlm and state['nlm']['sessions']:
        with st.expander('Newton progress details'): debugger_app.evidence(state)
    st.subheader('Active Material')
    for m in material_list:
        if m['visibility']!='active': continue
        with st.container(border=True):
            st.markdown('**'+m['title']+'**')
            st.caption('User 1 sample material · reviewed offline practice' if m['kind']=='authored' else 'Source notes · quizzes and recall cards')
            for col,label,target in zip(st.columns(2),['Continue learning','Practice'],['Library','Quiz']):
                if col.button(label,key='active_'+target+m['id']):
                    request_navigation(st.session_state,NavigationTarget(target,m['id']))
                    st.session_state.study_nlm_open=True; st.rerun()



def library():
    hero('LIBRARY', 'Material library',
         'Bring a chapter, lecture notes, or a syllabus. Check the extracted text, then study what your material actually contains.')
    if 'study_notice' in st.session_state:
        st.info(st.session_state.pop('study_notice'))
    search=st.text_input('Find material',placeholder='Search your library')
    if search:
        for m in material_list:
            if search.casefold() in m['title'].casefold() and st.button(m['title'],key='find_'+m['id']):
                request_navigation(st.session_state,NavigationTarget('Library',m['id'])); st.rerun()
    with st.expander('Manage selected material'):
        current_meta=state['material_meta'].get(st.session_state.study_material,{})
        renamed=st.text_input('Display title',value=material_labels[st.session_state.study_material],max_chars=100)
        if st.button('Save material title'):
            try:
                commit(update_material(state,st.session_state.study_material,title=renamed)); st.rerun()
            except (DomainError,OSError) as exc: st.error(str(exc))
        archived=current_meta.get('visibility')=='archived'
        if st.button('Reactivate material' if archived else 'Archive material'):
            try:
                commit(update_material(state,st.session_state.study_material,visibility='active' if archived else 'archived')); st.rerun()
            except (DomainError,OSError) as exc: st.error(str(exc))
        st.caption('Archiving hides the material from active lists. It preserves work and schedules and does not free storage.')
    with st.expander('Add new material', expanded=not state['documents'] and not st.session_state.get('study_nlm_open') and 'source_preview' not in state['preferences']):
        upload_tab, paste_tab = st.tabs(['Upload a file', 'Paste notes'])
        with upload_tab:
            with st.form('add_upload'):
                title = st.text_input('Material title', placeholder='e.g. Biology · Cell energy')
                uploaded = st.file_uploader('PDF, TXT or Markdown · up to 10 MB', type=['pdf', 'txt', 'md'], key='source_upload')
                count = st.slider('Questions to create', 3, 10, 6, key='upload_count')
                difficulty = st.selectbox('Difficulty', ['mixed', 'easy', 'medium', 'hard'], key='upload_difficulty')
                st.caption('Text-based PDFs only, up to 60 pages / 100,000 extracted characters. Scanned pages require OCR first.')
                if st.form_submit_button('Build study pack →', type='primary'):
                    if uploaded is None:
                        st.error('Choose a file first.')
                    else:
                        build(title.strip() or Path(uploaded.name).stem, uploaded.name, uploaded.getvalue(), count, difficulty)
        with paste_tab:
            with st.form('add_paste'):
                title = st.text_input('Title for pasted notes', placeholder='e.g. Operating Systems · Scheduling')
                text = st.text_area('Paste notes or syllabus', height=220, max_chars=100000,
                                    placeholder='Include explanatory statements, not just a list of topic names.')
                count = st.slider('Questions to create', 3, 10, 6, key='paste_count')
                difficulty = st.selectbox('Difficulty', ['mixed', 'easy', 'medium', 'hard'], key='paste_difficulty')
                if st.form_submit_button('Build from pasted notes →', type='primary'):
                    build(title.strip() or 'Pasted notes', 'pasted-notes.txt', text.encode('utf-8'), count, difficulty)
    pending_build=st.session_state.get('source_build_preview')
    if pending_build is None and 'source_preview' in state['preferences']:
        saved=state['preferences']['source_preview']
        pending_build=dict(title=saved['title'],filename=saved['filename'],payload=b'',count=saved['count'],difficulty=saved['difficulty'],
            preview=dict(text=saved['text'],chunks=saved['chunks'],warnings=['Saved extracted source preview. Review sections before generation.'],selected_ids=[c['id'] for c in __import__('content_quality').selected_sources(saved['chunks'])],omitted_ids=[c['id'] for c in saved['chunks'] if c not in __import__('content_quality').selected_sources(saved['chunks'])]))
    if pending_build:
        st.subheader('Check extracted source before generation')
        preview=pending_build['preview']
        for warning in preview['warnings']: st.warning(warning)
        st.caption(f"{len(preview['chunks'])} sections extracted. AI samples {len(preview['selected_ids'])}; {len(preview['omitted_ids'])} omitted. Local recall may cover fewer sections.")
        st.multiselect('Source sections to assess',[c['id'] for c in preview['chunks']],default=[c['id'] for c in preview['chunks']],format_func=lambda cid:next(c['section']+' · '+cid for c in preview['chunks'] if c['id']==cid),key='preview_sections')
        for chunk in preview['chunks']:
            with st.expander(chunk['section']+(' · page '+str(chunk['page']) if chunk['page'] else '')+' · '+chunk['id']): st.write(chunk['text'])
        st.write('Selected for AI:',', '.join(preview['selected_ids']))
        if preview['omitted_ids']: st.write('Omitted from AI:',', '.join(preview['omitted_ids']))
        if st.button('Confirm source and build pack',type='primary'): promote_preview(pending_build)
        if st.button('Cancel source preview'):
            from copy import deepcopy
            updated=deepcopy(state);updated['preferences'].pop('source_preview',None);commit(updated)
            st.session_state.pop('source_build_preview',None); st.rerun()
    if is_nlm:
        if not st.session_state.get('study_nlm_open'):topic_journey()
        with st.expander('Authored sources and scope'):
            authored=nlm.load_pack();st.write(authored['provenance']);st.write(authored['source_note'])
            for key,source in authored['sources'].items():st.markdown('['+source['section']+']('+source['url']+') · '+source['role'])
        st.subheader("Newton's Laws of Motion (NLM)")
        st.badge('Reviewed authored material · offline')
        st.write('Visual lessons, Newton practice, conceptual recall and evidence reports share the original saved progress.')
        for col,label,tab in zip(st.columns(4),['Learn','Practice Quiz','Flash Cards','View Insights'],['Learn visually','Practice','Flashcards','Evidence']):
            if col.button(label,key='nlm_material_'+tab): open_nlm(tab)
        if any(e['learner']=='My learning' and e['topic']!='upload' for e in state['debugger']['episodes']):
            st.button('Resume Repair',on_click=change_page,args=('Debugger',))
        if st.session_state.get('study_nlm_open'):
            if not state['nlm']['installed']:
                if st.button('Open authored lessons'): open_nlm()
            else: nlm_app.page(state,commit)
            with st.expander('Choose another Newton topic'):topic_journey()
        return
    if not document:
        return
    if any(m['id']==document_id and m['visibility']=='history' for m in material_list):
        st.info('Historical study material — original sources, timestamps, attempts and schedules preserved.')
    st.subheader(material_labels.get(document_id,document['title']))
    version=next(v for v in state['pack_versions'] if v['id']==state['material_meta'][document_id]['active_pack'])
    st.badge('Gemini generated' if version['mode']=='gemini' else 'Local extractive practice')
    st.caption(f"{document['filename']} · {len(document['chunks'])} source sections · {len(version['question_ids'])} active questions")
    with st.expander('Content checks and provenance'):
        st.write(version['quality'])
        st.caption('Source references, automated semantic review and authored review are separate claims. None guarantees arbitrary generated content is true.')
    st.write(version['summary'])
    st.write('**Topics:** ' + ' · '.join(version['topics']))
    st.caption(f"Pack version {version['version']}: {len(version['question_ids'])} questions. Sections assessed: {', '.join(version['source_ids'])}. Other extracted sections are available below.")
    with st.expander('Build an improved pack version'):
        st.caption('Existing attempts, questions, cards and schedules remain available. New questions are ordinary practice unless separately validated as independent checks.')
        regen_sections=st.multiselect('Sections for the new pack',[c['id'] for c in document['chunks']],default=[c['id'] for c in document['chunks']],key='regen_sections_'+document_id)
        regen_count=st.slider('New questions',3,10,6,key='regen_count')
        regen_difficulty=st.selectbox('New difficulty',['mixed','easy','medium','hard'],key='regen_difficulty')
        if st.button('Generate and save new pack version'):
            try:
                with st.spinner('Preparing a new pack version…'):
                    updated,message=regenerate_document(state,document_id,regen_count,regen_difficulty,st.session_state.study_use_ai,source_ids=regen_sections)
                commit(updated); st.session_state.study_notice=message; st.rerun()
            except (DomainError,OSError) as exc: st.error(str(exc))
    st.caption('AI content has source-reference checks, not a guarantee of factual or pedagogical correctness. A syllabus alone cannot supply missing teaching content.')
    a, b = st.columns(2)
    a.button('Take an adaptive quiz →', on_click=change_page, args=('Quiz',), type='primary', width='stretch')
    b.button('Open Flash Cards →', on_click=change_page, args=('Flash Cards',), width='stretch')
    with st.expander('Read extracted source material'):
        for chunk in document['chunks']:
            st.markdown(f'**{chunk["id"]} · {chunk["section"]}' + (f' · page {chunk["page"]}' if chunk['page'] else '') + '**')
            st.write(chunk['text'])


def begin_quiz():
    try:
        updated, qid = start_quiz(state, document_id, min(5, len(document['questions'])),topic=st.session_state.get('study_topic'))
        updated['preferences'].setdefault('last_context',{})['My learning']=dict(page='Quiz',material_id=document_id,learner='My learning',activity_kind='upload_quiz',activity_id=qid)
        commit(updated)
        st.session_state.study_quiz_id = qid
        st.session_state.pop('study_feedback', None)
        st.rerun()
    except (DomainError, OSError) as exc:
        st.error(str(exc))


def source_evidence(question):
    chunk = next(c for c in document['chunks'] if c['id'] == question['source_chunk_id'])
    st.caption('Source: ' + document['title'] + ' · ' + chunk['id']
               + (f' · page {chunk["page"]}' if chunk['page'] else '') + ' · ' + chunk['section'])
    st.info(question['evidence_quote'])
    with st.expander('Flag this question',expanded=False):
        reason=st.selectbox('Reason',['answer seems wrong','ambiguous choices','missing source support','explanation unclear','other'],key='flag_reason_'+question['id'])
        feedback=st.text_input('Optional feedback',max_chars=1000,key='flag_feedback_'+question['id'])
        if st.button('Save question flag',key='flag_'+question['id']):
            commit(flag_item(state,question['id'],reason,feedback)); st.rerun()
        if question['id'] in state['item_status']: st.info('Flagged: excluded from new practice and actionable accuracy. Historical answers are retained.')


def quiz_page():
    hero('QUIZ', 'Practice', 'Answer a question, then review your reasoning.')
    if is_nlm:
        if not state['nlm']['installed']:
            st.button('Open Newton practice',on_click=open_nlm,args=('Practice',));return
        nlm_app.page(state,commit); return
    if not require_document():
        return
    st.subheader(material_labels.get(document_id,document['title']))
    quizzes = [q for q in state['quizzes'] if q['document_id'] == document_id]
    selected = next((q for q in quizzes if q['id'] == st.session_state.get('study_quiz_id')), None)
    active = selected or next((q for q in reversed(quizzes) if not q['completed'] or not upload_activity_view(state,q['id'])['recovery_complete']), None)
    if active is None:
        st.write(f'This pack has {len(document["questions"])} questions. A round uses up to five.')
        st.caption('Local mode uses recall questions extracted from notes; Gemini can generate application questions when supported by the source.')
        if st.button('Start adaptive quiz →', type='primary'):
            begin_quiz()
        return
    quiz_version=next(v for v in state['pack_versions'] if active['question_ids'][0] in v['question_ids'])
    st.caption('Generated changed-situation check · source and automated review passed; fallible generated content.' if quiz_version['kind']=='independent' else 'Ordinary practice · supported recovery is separate from independent checks.')
    st.session_state.study_quiz_id=active['id']
    attempts = [a for a in state['attempts'] if a['quiz_id'] == active['id']]
    feedback = st.session_state.get('study_feedback')
    pending=next((a for a in attempts if not a['correct'] and not practice_view(state,active['id'],a['question_id'])['done']),None)
    if pending: feedback=(active['id'],pending['question_id'])
    if feedback and feedback[0] == active['id']:
        question = get_question(state, feedback[1])
        answer = next(a for a in attempts if a['question_id'] == question['id'])
        support=practice_view(state,active['id'],question['id'])
        def support_action(action,value=None):
            try:
                revision=support['revision']
                commit(practice_event(state,active['id'],question['id'],action,value,
                    f"support:{active['id']}:{sha256(question['id'].encode()).hexdigest()[:16]}:{revision}",revision))
                st.rerun()
            except (DomainError,OSError) as exc: st.error(str(exc))
        if not answer['correct'] and not support['solution']:
            st.warning('Not yet. Try this next hint.' if support['retries'] else 'First response saved. Try a targeted hint before the worked explanation.')
            st.markdown('### '+question['prompt'])
            for hint in question['hints'][:support['hints']]: st.info(hint)
            with st.form('retry_'+active['id']+question['id']+str(support['revision'])):
                retry=st.radio('Retry your answer',range(4),index=None,format_func=lambda i:question['options'][i])
                if st.form_submit_button('Check retry'): support_action('retry',retry)
            if st.button('Show worked explanation'): support_action('solution')
            st.caption('Up to two retries; the first response remains unchanged. Uploaded content has source-guided support, without reviewed Newton diagnostic coverage.')
            return
        retry_correct=bool(support['retries'] and support['retries'][-1]['correct'])
        (st.success if answer['correct'] or retry_correct else st.info)('Correct on this question.' if answer['correct'] else 'Correct on retry, with help.' if retry_correct else 'Review the expected answer and explanation.')
        if support['retries']: st.write('Latest retry: '+question['options'][support['retries'][-1]['selected_index']]+(' — correct' if retry_correct else ' — incorrect'))
        st.markdown('**First answer:** ' + question['options'][answer['selected_index']])
        st.markdown('**Expected answer in this study pack:** ' + question['options'][question['correct_index']])
        st.write(question['explanation'])
        known_help=bool(answer['hint_count'] or any(e['activity_id']==active['id'] and e['item_id']==question['id'] for e in state['activity_events']))
        help_label=str(answer['hint_count'])+' hint levels' if known_help else 'unknown in this historical round'
        st.caption(f"Help before first answer: {help_label}; during recovery: {support['hints'] if not answer['correct'] else 0} levels / {len(support['retries'])} retries. The first score stays unchanged.")
        source_evidence(question)
        if st.button('Review this difficulty in Debugger'):
            try:
                updated,sid=debugger_domain.start(state,'upload',origin={'document_id':document_id,'question_id':question['id']})
                commit(updated); st.session_state['debugger_active_My learning']=sid
                st.session_state.debugger_learner='My learning'
                st.session_state.study_next_page='Debugger'; st.rerun()
            except (DomainError,OSError) as exc: st.error(str(exc))
        if not answer['correct']:
            draft=next((d for d in state['drafts'] if d['activity_id']==active['id'] and d['item_id']==question['id']),None)
            writing=st.text_area('Teach-back: explain the principle in your own words (optional, not graded)',value=draft['text'] if draft else '',max_chars=4000,key='teach_'+active['id']+question['id'])
            st.caption(('Saved in this session' if st.session_state.get('demo_workspace') else 'Saved locally') if draft and draft['text']==writing else 'Unsaved writing — use Save writing to keep it after refresh.')
            if st.button('Save writing'):
                try:
                    commit(save_draft(state,document_id,active['id'],question['id'],writing)); st.rerun()
                except (DomainError,OSError) as exc: st.error(str(exc))
            st.caption('This retry is supported recovery. Ordinary quiz items are not independent checks. Generated changed-situation checks require source, novelty and automated-review gates; unsupported sources remain unavailable.')
            if st.button('Build generated changed-situation checks',disabled=not st.session_state.study_use_ai):
                try:
                    with st.spinner('Checking whether the source supports a new situation…'):
                        updated,message=build_followup(state,document_id,question['id'])
                    commit(updated);st.session_state.study_notice=message;st.rerun()
                except (DomainError,OSError) as exc:st.warning(str(exc))
            if not st.session_state.study_use_ai:st.caption('Enable Gemini to request generated check candidates. Local recall supports ordinary practice only.')
        if st.button('View results →' if active['completed'] else 'Next question →', type='primary'):
            if not support['done']:
                commit(practice_event(state,active['id'],question['id'],'finish',None,
                    f"support:{active['id']}:{sha256(question['id'].encode()).hexdigest()[:16]}:{support['revision']}",support['revision']))
            st.session_state.pop('study_feedback', None)
            st.rerun()
        return
    if active['completed']:
        correct = sum(a['correct'] for a in attempts)
        a, b, c = st.columns(3)
        a.metric('First answers correct', f'{correct}/{len(attempts)}')
        b.metric('Hints before first answers', sum(a['hint_count'] for a in attempts))
        repeated = sum(any(old['question_id'] == a['question_id'] and old['quiz_id'] != active['id'] for old in state['attempts']) for a in attempts)
        c.metric('Previously seen items', repeated)
        support_views=[practice_view(state,active['id'],a['question_id']) for a in attempts if not a['correct']]
        st.write(f"Recovery help: {sum(v['hints'] for v in support_views)} hint levels · {sum(len(v['retries']) for v in support_views)} retries. Original first score is unchanged.")
        st.caption('This is a quiz result, not a mastery badge. Repeats are practice and do not inflate first-response analytics.')
        for a in attempts:
            q = get_question(state, a['question_id'])
            with st.expander(('✓ ' if a['correct'] else '↻ ') + q['topic'] + ' · ' + q['prompt'][:90]):
                st.write(q['explanation']); source_evidence(q)
                if not a['correct']:
                    if st.button('Build changed-situation checks',key='result_check_'+q['id'],disabled=not st.session_state.study_use_ai):
                        try:
                            with st.spinner('Preparing source-supported check candidates…'):
                                updated,message=build_followup(state,document_id,q['id'])
                            updated,check_id=start_quiz(updated,document_id,3)
                            commit(updated);st.session_state.study_quiz_id=check_id;st.session_state.pop('study_feedback',None);st.rerun()
                        except (DomainError,OSError) as exc:st.warning(str(exc))
                    if not st.session_state.study_use_ai:st.caption('Generated checks need Gemini. Ordinary local practice remains available.')
        left, right = st.columns(2)
        if left.button('Start another practice round', width='stretch'):
            begin_quiz()
        right.button('See weak topics →', on_click=change_page, args=('Insights',), type='primary', width='stretch')
        return
    answered_ids = {a['question_id'] for a in attempts}
    question_id = next(qid for qid in active['question_ids'] if qid not in answered_ids)
    question = get_question(state, question_id)
    st.progress(len(attempts) / len(active['question_ids']), text=f'Question {len(attempts) + 1} of {len(active["question_ids"])}')
    st.caption(question['topic'] + ' · ' + question['difficulty'].title())
    if question_id in state['item_status']:st.warning('This question is disputed. Any response is practice, excluded from actionable accuracy and independent-check results. You can build a replacement pack in Library.')
    prior = [a for a in state['attempts'] if a['question_id'] == question_id]
    if prior:
        st.info('Previously seen question — useful practice, counted separately from new-item evidence.')
    hint_key = 'study_hint_' + active['id'] + question_id
    hints_used = hint_level(state,active['id'],question_id)
    with st.form('answer_' + active['id'] + question_id):
        st.markdown('### ' + question['prompt'])
        answer = st.radio('Choose your answer', range(4), index=None, format_func=lambda i: question['options'][i], key='answer_' + active['id'] + question_id)
        if st.form_submit_button('Check my answer →', type='primary'):
            try:
                updated = submit_answer(state, active['id'], question_id, answer, active['id'] + ':' + question_id)
                commit(updated)
                st.session_state.study_feedback = (active['id'], question_id)
                st.session_state.study_quiz_id = active['id']
                st.rerun()
            except (DomainError, OSError) as exc:
                st.error(str(exc))
    for hint in question['hints'][:hints_used]:
        st.info(hint)
    if hints_used < 2 and st.button('Give me a hint', key='get_study_hint'):
        try:
            commit(show_hint(state,active['id'],question_id,hints_used+1)); st.rerun()
        except (DomainError,OSError) as exc: st.error(str(exc))
    st.caption('Two hints are available. Answers and source evidence appear after submission.')


def revision_page():
    hero('FLASH CARDS', 'Recall practice', 'Recall the answer before revealing it, then rate your recall.')
    if is_nlm:
        if not state['nlm']['installed']:
            st.button('Open Newton cards',on_click=open_nlm,args=('Flashcards',));return
        nlm_app.page(state,commit); return
    if not require_document():
        return
    if 'card_notice' in st.session_state:st.success(st.session_state.pop('card_notice'))
    all_cards = [c for c in state['cards'] if c['document_id'] == document_id]
    queue=card_queue(state,document_id)
    st.caption(f"{queue['due_count']} due now · {queue['new_count']} new · {queue['upcoming_count']} upcoming")
    mode=st.radio('Card view',['Due reviews','New cards','Preview all'],index=0 if any(c['review_count'] for c in all_cards) else 1,horizontal=True,key='study_card_view')
    queue=card_queue(state,document_id,{'Preview all':'preview','New cards':'new','Due reviews':'due'}[mode])
    cards=queue['items']
    if not cards:
        st.info('No scheduled reviews are due.' if mode=='Due reviews' else 'No new cards remain in this material.')
        if queue['new_count']: st.write(f"Study {queue['new_count']} new cards using New cards.")
        if queue['next_due_at']: st.caption('Next scheduled review: '+date_label(queue['next_due_at']))
        return
    card_ids = [c['id'] for c in cards]
    if st.session_state.get('revision_card') not in card_ids: st.session_state.revision_card=card_ids[0]
    card_id = st.selectbox('Flash Card', card_ids,
                           format_func=lambda cid: next(c['front'][:85] for c in cards if c['id'] == cid), key='revision_card')
    card = next(c for c in cards if c['id'] == card_id)
    st.badge(card['topic'])
    st.caption(f"{len(cards)} cards remain in this view · card {card_ids.index(card_id)+1} of {len(cards)}")
    with st.container(border=True):
        st.subheader(card['front'])
        nlm_app.draft_editor(state,commit,document_id,'cards',card_id,'My learning','Write your recalled explanation (optional, ungraded)','recall_'+card_id)
        reveal_key = 'reveal_' + card_id + '_' + str(card['review_count'])
        if not st.session_state.get(reveal_key):
            if st.button('Reveal answer', type='primary'):
                st.session_state[reveal_key] = True
                st.rerun()
        else:
            st.write(card['back'])
            with st.expander('Flag this card'):
                reason=st.selectbox('Card flag reason',['answer seems wrong','missing source support','explanation unclear','other'],key='card_flag_reason_'+card_id)
                if st.button('Save card flag'):
                    commit(flag_item(state,card_id,reason));st.rerun()
            st.caption('Source evidence · ' + card['source_chunk_id'])
            st.info(card['evidence_quote'])
            is_due = datetime.fromisoformat(card['due_at']) <= clock()
            if not is_due:
                st.warning('Preview only. This card is not due; its schedule and review count stay unchanged.')
            for col, rating in zip(st.columns(4), ('Again', 'Hard', 'Good', 'Easy')):
                if col.button(rating, key='rate_' + rating, disabled=not is_due, width='stretch'):
                    try:
                        token = 'review_' + card_id + '_' + str(card['review_count'])
                        commit(grade_card(state, card_id, rating, token))
                        saved=next(c for c in st.session_state.study['cards'] if c['id']==card_id)
                        st.session_state.card_notice='Recall rating saved. Next review: '+date_label(saved['due_at'])
                        st.rerun()
                    except (DomainError, OSError) as exc:
                        st.error(str(exc))
    st.caption('Prototype intervals: Again = 10 minutes; Hard = 1 day; Good = 1, 3, 7, then 14 days; Easy skips one step. Self-rated recall is not an objective mastery measure.')


def insights_page():
    hero('INSIGHTS', 'Learning insights', 'Saved observations, support and fresh checks — scoped to the selected material.')
    period_column, topic_column = st.columns(2)
    with period_column:
        days=st.selectbox('Report period',['All saved history','Last 7 days','Last 30 days'])
    from datetime import timedelta
    since=None if days=='All saved history' else clock()-timedelta(days=7 if '7' in days else 30)
    r=report(state,st.session_state.study_material,since=since)
    topic_labels={t['topic_id']:t['topic'] for t in r['topics']}
    with topic_column:
        selected=st.multiselect('Topic filter',list(topic_labels),format_func=topic_labels.get)
    if selected: r=report(state,st.session_state.study_material,since=since,topic_ids=selected)
    report_summary(r)
    with st.expander('How this report is calculated'):
        st.caption('First answers are counted once per question family. Retries, assistance and later checks remain separate. Topic/date filters apply to accuracy and checks; schedules and pending work cover the whole material. Quiz reports cover whole rounds.')
        st.caption('Needs practice: fewer than 70% correct with at least 3 first answers. Recurring support candidates need two different item families including a diagnostic probe; contradictory observations remain visible.')
    if r['topics']:
        topics=r['topics']
        heatmap_columns=st.columns(min(3,len(topics)))
        for i, t in enumerate(topics):
            bg='#eef1f5' if t['attempted']<3 else '#fdeee9' if t['accuracy']<.7 else '#e3f3ec'
            with heatmap_columns[i % len(heatmap_columns)]:
                st.markdown(f'<div class="topic-tile" style="background:{bg}"><strong>{escape(t["topic"])}</strong><p>{t["accuracy"]:.0%}</p>{t["correct"]}/{t["attempted"]} first responses · {escape(t["status"])}</div>',unsafe_allow_html=True)
        st.caption('Heatmap legend: grey = insufficient evidence (<3); coral = <70%; green = ≥70%. The table is the textual alternative.')
        with st.expander('Detailed topic results'):
            st.dataframe([{k:v for k,v in t.items() if k!='topic_id'} for t in topics],hide_index=True,width='stretch')
    else: st.info('Insufficient evidence. Answer a question to begin a report.')
    st.write(f"Assisted responses: {r['assisted']} · repeated responses/retries: {r['retries']} · material-wide sessions with solution/help: {r['solutions']}")
    st.dataframe([dict(check={'follow_up':'New example','transfer':'New situation','delayed':'Scheduled check'}[k],**v) for k,v in r['checks'].items()],hide_index=True,width='stretch')
    st.caption('Check correct counts require unassisted responses. Immediate recovery, changed-context transfer and delayed retention are separate; no mastery is inferred.')
    if r['events']:
        with st.expander('Trace observations and recent trend'):
            st.dataframe(r['events'],hide_index=True,width='stretch')
    recent_reports(r)
    if r['repairs']: st.dataframe(r['repairs'],hide_index=True,width='stretch')
    if is_nlm:
        st.caption('Additional all-time Newton and debugger history below uses its own displayed sample sizes; topic/date filters apply to the report above.')
        debugger_app.evidence(state)
        nlm_app.evidence(state['nlm'])
    st.button('Understand this mistake',on_click=change_page,args=('Debugger',))
    st.button('Practise with an adaptive quiz →',on_click=change_page,args=('Quiz',),type='primary')
    st.button('Review due Flash Cards →',on_click=change_page,args=('Flash Cards',))


if page == 'Quiz' and st.session_state.get('study_repair'):
    if st.button('← Return to practice'):
        st.session_state.study_repair=False; st.rerun()
    debugger_app.page(state,commit)
else:
    # Set a default subordinate tab only when the primary destination changes.
    if is_nlm and st.session_state.get('material_destination') != (page,st.session_state.study_material):
        if page in ('Quiz','Flash Cards'): st.session_state.nlm_tab='Practice' if page=='Quiz' else 'Flashcards'
    st.session_state.material_destination=(page,st.session_state.study_material)
    {'Dashboard':dashboard,'Library':library,'Quiz':quiz_page,'Flash Cards':revision_page,'Insights':insights_page}[page]()
st.divider()
st.caption('Phoenix · Source-grounded study · '+('User 1 sample workspace · session-only changes' if st.session_state.get('demo_workspace') else 'Personal workspace · saved locally'))

# URL context is validated on restore; no duplicate records or saved-preference migration.
context={'page':page,'material':st.session_state.study_material}
route_learner=st.session_state.get('debugger_learner','My learning') if st.session_state.get('study_repair') else st.session_state.get('nlm_learner','My learning') if is_nlm else 'My learning'
context['learner']=route_learner
if page=='Quiz':
    if st.session_state.get('study_repair'):
        route_id=st.session_state.get('debugger_active_'+route_learner)
        if route_id:context.update(activity_kind='repair',activity=route_id)
    elif is_nlm:
        route_id=st.session_state.get('nlm_active_'+route_learner)
        if route_id:context.update(activity_kind='newton_session',activity=route_id)
    else:
        route_id=st.session_state.get('study_quiz_id')
        if any(q['id']==route_id and q['document_id']==document_id for q in state['quizzes']):context.update(activity_kind='upload_quiz',activity=route_id)
if page=='Flash Cards':
    view=st.session_state.get('nlm_card_view' if is_nlm else 'study_card_view')
    if view:context['card_view']={'Due reviews':'due','New cards':'new','Preview all':'preview'}[view]
if is_nlm and st.session_state.get('nlm_tab'):
    context['lesson']=st.session_state.nlm_tab
    if page=='Library' and st.session_state.get('nlm_concept'):context['topic']=st.session_state.nlm_concept
if page=='Quiz' and st.session_state.get('study_repair'):
    active=st.session_state.get('debugger_active_My learning')
    if active: context['repair']=active
if dict(st.query_params)!=context:
    st.query_params.from_dict(context)
