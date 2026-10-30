"""Phoenix Study: the main uploaded-material learning experience."""
from datetime import datetime
from html import escape
from pathlib import Path
from uuid import uuid4

import streamlit as st

from ai_provider import ProviderError, connection_check, settings
from engine import DomainError
from ledger import clock
from study import (add_document, answer_question, export_state, get_document, get_question,
                   grade_card, import_state, load_state, new_state, recommendations, save_state,
                   start_quiz, topic_stats)

st.set_page_config(page_title='Phoenix Study · Your learning workspace', page_icon='✦', layout='wide')
st.markdown('''<style>
.block-container{max-width:1190px;padding-top:2.5rem;padding-bottom:4rem}
h1{letter-spacing:-.055em;font-weight:800!important;font-size:2.8rem!important}
h2,h3{letter-spacing:-.025em}
[data-testid="stSidebar"]{border-right:1px solid #dce5ec}
[data-testid="stMetric"]{background:white;border:1px solid #dfe6ed;border-radius:14px;padding:18px}
[data-testid="stForm"]{background:white;border:1px solid #dfe6ed;border-radius:16px;padding:24px}
.eyebrow{color:#087f74;letter-spacing:.16em;font-size:.73rem;font-weight:800;text-transform:uppercase}
.subtitle{font-size:1.1rem;color:#59677c;line-height:1.7;max-width:780px;margin-bottom:1.6rem}
.brand{font-weight:800;font-size:1.6rem;letter-spacing:-.05em;color:#17253d}
.brand span{color:#087f74}
.topic-tile{border:1px solid #dce5ec;border-radius:14px;padding:20px;margin:8px 0;min-height:140px}
.topic-tile strong{font-size:1rem}.topic-tile p{font-size:1.7rem;font-weight:800;margin:8px 0}
.flow{color:#637087;font-size:.8rem;letter-spacing:.05em;margin:1rem 0 2rem}
</style>''', unsafe_allow_html=True)

if 'study' not in st.session_state:
    try:
        st.session_state.study = load_state()
    except (DomainError, OSError) as exc:
        st.error(f'The saved workspace could not be loaded: {exc}. The existing file has been preserved.')
        st.stop()
if 'study_nav' not in st.session_state:
    st.session_state.study_nav = 'Dashboard'
if 'study_next_page' in st.session_state:
    st.session_state.study_nav = st.session_state.pop('study_next_page')
if 'study_use_ai' not in st.session_state:
    st.session_state.study_use_ai = bool(settings().key)


def change_page(page):
    st.session_state.study_nav = page


def open_lab():
    st.session_state.workspace_view = 'Lab'


def commit(updated):
    if st.session_state.get('study_persist', True):
        save_state(updated)
    st.session_state.study = updated


def build(title, filename, payload, count=6, difficulty='mixed'):
    try:
        with st.spinner('Reading your material and building a source-grounded study pack…'):
            updated, doc_id, message = add_document(st.session_state.study, title, filename, payload,
                count, difficulty, st.session_state.study_use_ai)
            commit(updated)
            st.session_state.study_next_document = doc_id
            st.session_state.study_notice = message
            st.session_state.study_next_page = 'Library'
            st.rerun()
    except (DomainError, OSError) as exc:
        st.error(str(exc))


state = st.session_state.study
documents = state['documents']
doc_labels = {d['id']: d['title'] for d in documents}
if 'study_next_document' in st.session_state:
    st.session_state.study_document = st.session_state.pop('study_next_document')
if documents and st.session_state.get('study_document') not in doc_labels:
    st.session_state.study_document = documents[-1]['id']

with st.sidebar:
    st.markdown('<div class="brand">✦ Phoenix<span>Study</span></div>', unsafe_allow_html=True)
    st.caption('Your notes. Your gaps. Your next step.')
    st.radio('Navigate', ['Dashboard', 'Library', 'Quiz', 'Revision', 'Insights'], key='study_nav')
    st.divider()
    if documents:
        st.selectbox('Active material', list(doc_labels), format_func=doc_labels.get, key='study_document')
    else:
        st.caption('Your library is empty. Upload something to begin.')
    st.toggle('Use Gemini when available', key='study_use_ai')
    st.caption('AI mode sends selected source excerpts to Google when you build a pack. Local mode keeps generation on this PC.')
    with st.expander('AI connection'):
        config = settings()
        st.write('Key configured' if config.key else 'No key found — local mode available')
        st.caption('Model: ' + config.model)
        if st.button('Test Gemini connection'):
            try:
                if connection_check():
                    st.success('Gemini connection works. Generation quota is checked when you build a pack.')
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
    with st.expander('Restore a backup'):
        st.caption('Backups include your extracted notes and progress, never API keys.')
        backup = st.file_uploader('Study backup JSON (up to 8 MB)', type=['json'], key='study_backup')
        if st.button('Restore study workspace'):
            try:
                if backup is None:
                    raise DomainError('invalid_progress', 'Choose a study backup first.')
                restored = import_state(backup.getvalue().decode('utf-8'))
                commit(restored)
                st.session_state.pop('study_feedback', None)
                st.session_state.study_next_page = 'Dashboard'
                st.rerun()
            except (DomainError, UnicodeError, OSError) as exc:
                st.error(f'Restore rejected: {exc}. Existing progress is unchanged.')
    st.caption('Single-student workspace · saved locally on this PC')

document_id = st.session_state.get('study_document') if documents else None
document = get_document(state, document_id) if document_id else None
page = st.session_state.study_nav


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


def dashboard():
    hero('YOUR PERSONAL LEARNING WORKSPACE', 'Learn from where you are.',
         'Turn your own notes into a study plan. Find the gaps, practise with guidance, and come back to what needs another look.')
    st.markdown('<div class="flow">UPLOAD MATERIAL  →  CHECK UNDERSTANDING  →  REPAIR GAPS  →  REVISE</div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    a.metric('Study materials', len(documents))
    b.metric('Quiz responses', len(state['attempts']))
    a.metric('Cards due', sum(datetime.fromisoformat(c['due_at']) <= clock() for c in state['cards']))
    b.metric('Topics explored', len(topic_stats(state)))
    st.markdown('### Your next steps')
    for title, target, description in recommendations(state):
        with st.container(border=True):
            cols = st.columns([4, 1])
            cols[0].markdown('**' + title + '**')
            cols[0].caption(description)
            cols[1].button('Open →', key='rec_' + title, on_click=change_page, args=(target,), width='stretch')
    if not documents:
        left, right = st.columns(2)
        with left:
            st.subheader('Start with your own material')
            st.write('Upload a text-based PDF, TXT or Markdown file, or paste your lecture notes.')
            st.button('Upload my notes →', on_click=change_page, args=('Library',), type='primary')
        with right:
            st.subheader('See the full journey first')
            st.write('Try biology notes through the same upload-to-quiz pipeline. Nothing is limited to algebra.')
            if st.button('Build a pack from sample notes'):
                build('Cell Energy', 'demo-notes.md', (Path(__file__).parent / 'data/demo-notes.md').read_bytes())
    else:
        st.markdown('### Recently added')
        for d in reversed(documents[-3:]):
            with st.container(border=True):
                st.markdown('**' + d['title'] + '**')
                st.caption(f'{len(d["questions"])} questions · {len(d["topics"])} topics · '
                           + ('Gemini source-grounded pack' if d['mode'] == 'gemini' else 'Local extractive pack'))


def library():
    hero('01 / MATERIAL LIBRARY', 'Your course starts here.',
         'Bring a chapter, lecture notes, or a syllabus. Check the extracted text, then study what your material actually contains.')
    if 'study_notice' in st.session_state:
        st.info(st.session_state.pop('study_notice'))
    with st.expander('Add new material', expanded=not documents):
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
    if not document:
        return
    st.subheader(document['title'])
    st.badge('Gemini generated' if document['mode'] == 'gemini' else 'Local extractive practice')
    st.caption(f'{document["filename"]} · {len(document["chunks"])} source sections · {len(document["questions"])} questions')
    st.write(document['summary'])
    st.write('**Topics:** ' + ' · '.join(document['topics']))
    st.caption('AI content has source-reference checks, not a guarantee of factual or pedagogical correctness. A syllabus alone cannot supply missing teaching content.')
    a, b = st.columns(2)
    a.button('Take an adaptive quiz →', on_click=change_page, args=('Quiz',), type='primary', width='stretch')
    b.button('Open revision cards →', on_click=change_page, args=('Revision',), width='stretch')
    with st.expander('Read extracted source material'):
        for chunk in document['chunks']:
            st.markdown(f'**{chunk["id"]} · {chunk["section"]}' + (f' · page {chunk["page"]}' if chunk['page'] else '') + '**')
            st.write(chunk['text'])


def begin_quiz():
    try:
        updated, qid = start_quiz(state, document_id, min(5, len(document['questions'])))
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


def quiz_page():
    hero('02 / ADAPTIVE QUIZ', 'Practise the gaps. Keep the reasoning.',
         'New questions come first. Topics with weaker first responses get priority. Hints guide you before the answer is revealed.')
    if not require_document():
        return
    st.subheader(document['title'])
    quizzes = [q for q in state['quizzes'] if q['document_id'] == document_id]
    selected = next((q for q in quizzes if q['id'] == st.session_state.get('study_quiz_id')), None)
    active = selected or next((q for q in reversed(quizzes) if not q['completed']), None)
    if active is None:
        st.write(f'This pack has {len(document["questions"])} questions. A round uses up to five.')
        st.caption('Local mode uses recall questions extracted from notes; Gemini can generate application questions when supported by the source.')
        if st.button('Start adaptive quiz →', type='primary'):
            begin_quiz()
        return
    attempts = [a for a in state['attempts'] if a['quiz_id'] == active['id']]
    feedback = st.session_state.get('study_feedback')
    if feedback and feedback[0] == active['id']:
        question = get_question(state, feedback[1])
        answer = next(a for a in attempts if a['question_id'] == question['id'])
        (st.success if answer['correct'] else st.warning)('Correct on this question.' if answer['correct'] else 'This response needs another look.')
        st.markdown('**Your answer:** ' + question['options'][answer['selected_index']])
        st.markdown('**Reviewed answer:** ' + question['options'][question['correct_index']])
        st.write(question['explanation'])
        st.caption(f'{answer["hint_count"]} hints used. Help is recorded separately from correctness.')
        source_evidence(question)
        if st.button('View results →' if active['completed'] else 'Next question →', type='primary'):
            st.session_state.pop('study_feedback', None)
            st.rerun()
        return
    if active['completed']:
        correct = sum(a['correct'] for a in attempts)
        a, b, c = st.columns(3)
        a.metric('Correct responses', f'{correct}/{len(attempts)}')
        b.metric('Hints used', sum(a['hint_count'] for a in attempts))
        repeated = sum(any(old['question_id'] == a['question_id'] and old['quiz_id'] != active['id'] for old in state['attempts']) for a in attempts)
        c.metric('Previously seen items', repeated)
        st.caption('This is a quiz result, not a mastery badge. Repeats are practice and do not inflate first-response analytics.')
        for a in attempts:
            q = get_question(state, a['question_id'])
            with st.expander(('✓ ' if a['correct'] else '↻ ') + q['topic'] + ' · ' + q['prompt'][:90]):
                st.write(q['explanation']); source_evidence(q)
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
    prior = [a for a in state['attempts'] if a['question_id'] == question_id]
    if prior:
        st.info('Previously seen question — useful practice, counted separately from new-item evidence.')
    hint_key = 'study_hint_' + active['id'] + question_id
    hints_used = st.session_state.get(hint_key, 0)
    with st.form('answer_' + active['id'] + question_id):
        st.markdown('### ' + question['prompt'])
        answer = st.radio('Choose your answer', range(4), index=None, format_func=lambda i: question['options'][i], key='answer_' + active['id'] + question_id)
        if st.form_submit_button('Check my answer →', type='primary'):
            try:
                updated = answer_question(state, active['id'], question_id, answer, hints_used, active['id'] + ':' + question_id)
                commit(updated)
                st.session_state.study_feedback = (active['id'], question_id)
                st.session_state.study_quiz_id = active['id']
                st.rerun()
            except (DomainError, OSError) as exc:
                st.error(str(exc))
    for hint in question['hints'][:hints_used]:
        st.info(hint)
    if hints_used < 2 and st.button('Give me a hint', key='get_study_hint'):
        st.session_state[hint_key] = hints_used + 1
        st.rerun()
    st.caption('Two hints are available. Answers and source evidence appear after submission.')


def revision_page():
    hero('03 / SPACED REVISION', 'Retrieve. Reflect. Return.',
         'Try to recall before flipping the card. Your self-rating determines when it comes back.')
    if not require_document():
        return
    all_cards = [c for c in state['cards'] if c['document_id'] == document_id]
    due = [c for c in all_cards if datetime.fromisoformat(c['due_at']) <= clock()]
    st.caption(f'{len(due)} due now · {len(all_cards)} cards in {document["title"]}')
    preview = st.toggle('Preview all cards (future cards cannot be completed early)', key='preview_study_cards')
    cards = all_cards if preview else due
    if not cards:
        st.success('No cards due right now. Your next review is scheduled.')
        if all_cards:
            st.caption('Next due: ' + min(c['due_at'] for c in all_cards))
        return
    card_ids = [c['id'] for c in cards]
    card_id = st.selectbox('Revision card', card_ids,
                           format_func=lambda cid: next(c['front'][:85] for c in cards if c['id'] == cid), key='revision_card')
    card = next(c for c in cards if c['id'] == card_id)
    st.badge(card['topic'])
    with st.container(border=True):
        st.subheader(card['front'])
        reveal_key = 'reveal_' + card_id + '_' + str(card['review_count'])
        if not st.session_state.get(reveal_key):
            if st.button('Reveal answer', type='primary'):
                st.session_state[reveal_key] = True
                st.rerun()
        else:
            st.write(card['back'])
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
                        st.rerun()
                    except (DomainError, OSError) as exc:
                        st.error(str(exc))
    st.caption('Prototype intervals: Again = 10 minutes; Hard = 1 day; Good = 1, 3, 7, then 14 days; Easy skips one step. Self-rated recall is not an objective mastery measure.')


def insights_page():
    hero('04 / LEARNING PATH & WEAK TOPICS', 'Make the next step personal.',
         'See where your first responses were uncertain, where hints helped, and what deserves another practice session.')
    if not require_document():
        return
    stats = topic_stats(state, document_id)
    cols = st.columns(min(2, max(1, len(stats))))
    for i, row in enumerate(stats):
        accuracy = row['accuracy']
        bg = '#eef1f5' if accuracy is None else '#fdeee9' if accuracy < .5 else '#fff5d9' if accuracy < .8 else '#e3f3ec'
        score = 'Unseen' if accuracy is None else f'{round(accuracy * 100)}%'
        cols[i % len(cols)].markdown(f'<div class="topic-tile" style="background:{bg}"><strong>{escape(row["topic"])}</strong>'
            f'<p>{score}</p><small>{row["correct"]}/{row["attempted"]} first responses correct · {row["assisted"]} assisted</small></div>', unsafe_allow_html=True)
    st.caption('Heatmap = correctness on the first response to each question. Repeats do not inflate it. Small samples and AI-authored keys limit what this evidence means.')
    st.markdown('### Recommended learning path')
    weak = sorted(stats, key=lambda r: r['accuracy'] if r['accuracy'] is not None else -.1)
    for index, row in enumerate(weak):
        label = 'Start with a diagnostic check' if row['accuracy'] is None else 'Review the source, then practise' if row['accuracy'] < .7 else 'Maintain with spaced revision'
        with st.container(border=True):
            st.markdown(f'**{index + 1}. {row["topic"]}**')
            st.write(label)
    st.button('Practise with an adaptive quiz →', on_click=change_page, args=('Quiz',), type='primary')
    st.caption('Adaptive selection prioritizes weak topics and unseen items. It is a transparent heuristic, not a trained knowledge model.')


{'Dashboard': dashboard, 'Library': library, 'Quiz': quiz_page, 'Revision': revision_page,
 'Insights': insights_page}[page]()
st.divider()
st.caption('Phoenix Study · Based on your material · Local save enabled · AI content can be wrong; inspect its source evidence')
