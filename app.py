"""Misconception Lab — a local, deterministic algebra experiment."""
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st

from engine import DomainError, evaluate, find_counterexample, load_packs, pack_by_id, question_by_id
from ledger import (clock, delayed_question, export_progress, get_record, import_progress,
                    new_progress, recommend_next, review, transfer_outcome)
from workflow import current_question, new_lab, request_help, submit_response

st.set_page_config(page_title='Misconception Lab', page_icon='🧪', layout='wide')
st.markdown('''<style>
    .block-container {max-width:1140px;padding-top:2.3rem;padding-bottom:4rem}
    h1 {letter-spacing:-.055em;font-weight:800!important}
    h2,h3 {letter-spacing:-.025em}
    [data-testid="stSidebar"] {border-right:1px solid #dde5eb}
    [data-testid="stMetric"] {background:#fff;border:1px solid #e0e7ec;border-radius:14px;padding:16px}
    div[data-testid="stForm"] {background:white;border-radius:16px;border:1px solid #dce5eb;padding:24px}
    .eyebrow {color:#087f74;font-size:.76rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase}
    .hero-note {max-width:650px;color:#526078;font-size:1.1rem;line-height:1.65}
    .lab-note {background:#e6f3ef;border-left:3px solid #087f74;border-radius:8px;padding:16px 20px;margin:12px 0}
    .step-strip {font-size:.8rem;color:#68758a;letter-spacing:.04em;padding:12px 0 20px}
    [data-testid="stCaptionContainer"] {color:#59677c}
</style>''', unsafe_allow_html=True)


@st.cache_data
def content_data():
    return load_packs(Path(__file__).parent / 'data' / 'packs.json')


try:
    content = content_data()
except DomainError as exc:
    st.error(f'Content validation failed: {exc}')
    st.stop()

if 'progress' not in st.session_state:
    st.session_state.progress = new_progress()
if 'labs' not in st.session_state:
    st.session_state.labs = {}
if 'navigation' not in st.session_state:
    st.session_state.navigation = 'Debug Lab'
if 'family' not in st.session_state:
    st.session_state.family = 'distribution'
if '_next_navigation' in st.session_state:
    st.session_state.navigation = st.session_state.pop('_next_navigation')


def navigate(page, family=None, restart=False):
    st.session_state.navigation = page
    if family:
        st.session_state.family = family
        if restart:
            st.session_state.labs[family] = new_lab(family)


def reset_demo():
    st.session_state.progress = new_progress()
    st.session_state.labs = {}
    st.session_state.navigation = 'Debug Lab'
    st.session_state.family = 'distribution'
    for key in list(st.session_state):
        if key.startswith(('review_help_', 'review_token_', 'preview_')) or key == '_next_navigation':
            del st.session_state[key]


with st.sidebar:
    st.markdown('### 🧪 Misconception Lab')
    st.caption('A small experiment in better reasoning')
    st.radio('Workspace', ['Debug Lab', 'Transfer Challenge', 'Repair Ledger'], key='navigation')
    st.divider()
    st.selectbox('Rule family', [p['id'] for p in content['packs']], key='family',
                 format_func=lambda fid: pack_by_id(content, fid)['title'])
    st.markdown('**Built-in rule engine**')
    st.caption('Works without an API key. Authored explanations; deterministic checks.')
    st.divider()
    st.download_button('Export progress ↓', export_progress(st.session_state.progress),
                       'progress-misconception-lab.json', 'application/json', width='stretch')
    with st.expander('Restore progress'):
        upload = st.file_uploader('Progress JSON (maximum 1 MiB)', type=['json'], key='progress_upload')
        if st.button('Import progress', width='stretch'):
            try:
                if upload is None:
                    raise DomainError('invalid_progress', 'Choose an exported JSON file first.')
                restored = import_progress(upload.getvalue().decode('utf-8'), content)
                st.session_state.progress = restored
                st.session_state.labs = {}
                st.success('Progress restored. Evidence and schedules retained.')
            except (DomainError, UnicodeDecodeError) as exc:
                st.error(f'Import rejected: {exc}. Your current progress is unchanged.')
    with st.expander('Reset demo'):
        st.caption('Export first if you want to keep your evidence. Reset clears this browser session.')
        st.button('Reset all progress', on_click=reset_demo, width='stretch')
    st.caption('Single student · explicit export persistence')

fid = st.session_state.family
pack = pack_by_id(content, fid)
if fid not in st.session_state.labs:
    st.session_state.labs[fid] = new_lab(fid)
lab = st.session_state.labs[fid]
progress = st.session_state.progress


def submit(response):
    try:
        next_lab, next_progress = submit_response(lab, response, lab['token'], clock(), progress, content)
        st.session_state.labs[fid] = next_lab
        st.session_state.progress = next_progress
        if next_lab['stage'] in ('TRANSFER', 'TRANSFER_FEEDBACK'):
            # Set the radio on the following rerun, before it is instantiated.
            st.session_state['_next_navigation'] = 'Transfer Challenge'
        elif next_lab['stage'] == 'LEDGER':
            st.session_state['_next_navigation'] = 'Repair Ledger'
        st.rerun()
    except DomainError as exc:
        st.error(str(exc))


def question_display(q):
    st.markdown(f'#### {q["prompt"]}')
    if q.get('latex'):
        st.latex(q['latex'])


def answer_radio(q, key='answer'):
    labels = {o['id']: o['text'] for o in q['options']}
    return st.radio('Your answer', list(labels), index=None, format_func=labels.get,
                    key=f'{lab["token"]}_{key}')


def reason_radio(key='reason', label='Why did you choose that answer?'):
    labels = {r['id']: r['text'] for r in pack['reason_options']}
    return st.radio(label, list(labels), index=None, format_func=labels.get,
                    key=f'{lab["token"]}_{key}')


def help_controls():
    q = current_question(lab, content)
    count = lab['help_counts'].get(q['id'], 0)
    hints = {h['id']: h['text'] for h in content['hints']}
    with st.expander('Need a hint?'):
        st.caption('Two hints, then the worked explanation. Help on a transfer item marks it assisted.')
        for hid in pack['hint_ids'][:min(count, 2)]:
            st.info(hints[hid])
        if count >= 3:
            st.write(pack['canonical_explanation'])
            st.latex(pack['correct_latex'])
        if count < 3 and st.button('Show next hint' if count < 2 else 'Show worked explanation', key='show_help'):
            st.session_state.labs[fid] = request_help(lab, content)
            st.rerun()


def bench_values(x, repaired=False):
    kind = 'correct' if repaired else 'faulty'
    original = evaluate(fid, 'original', pack['parameters'], x)
    rewritten = evaluate(fid, kind, pack['parameters'], x)
    a, b = st.columns(2)
    with a:
        st.latex(pack['original_latex'])
        st.metric('Original expression', original)
    with b:
        st.latex(pack['correct_latex'] if repaired else pack['faulty_latex'])
        st.metric('Repaired rewrite' if repaired else 'Rule rewrite', rewritten)
    if original != rewritten:
        st.warning(f'At x = {x}, {original} ≠ {rewritten}. This is a counterexample to the rewrite.')
    else:
        st.info('This test agrees; one agreement does not establish equivalence.')


def repair_summary():
    st.success('Rule repaired — now test it beyond this example.')
    st.write(pack['canonical_explanation'])
    st.latex(pack['correct_rule_latex'])
    rows = [{'x': x, 'Original': evaluate(fid, 'original', pack['parameters'], x),
             'Repaired': evaluate(fid, 'correct', pack['parameters'], x)} for x in (-1, 0, 1)]
    st.table(rows)
    st.caption('Three regression checks agree. The authored algebra rule supplies the general justification.')


def render_lab():
    st.markdown('<div class="eyebrow">01 / Misconception Debugger</div>', unsafe_allow_html=True)
    st.title('Put your rule to the test.')
    st.markdown('<p class="hero-note">A wrong answer is a starting point. Find the rule behind it, '
                'run an experiment, and see what needs to change.</p>', unsafe_allow_html=True)
    st.markdown('<div class="step-strip">YOUR RULE  →  TEST BENCH  →  WHAT BROKE  →  REPAIR</div>',
                unsafe_allow_html=True)
    st.subheader(pack['title'])
    st.caption(pack['subtitle'])
    stage = lab['stage']
    q = current_question(lab, content)
    if stage == 'PREDICT':
        with st.form(lab['token']):
            question_display(q)
            answer = answer_radio(q)
            if st.form_submit_button('Lock prediction →', type='primary'):
                submit({'selected_option_id': answer})
    elif stage == 'SELECT_REASON':
        st.caption('Prediction locked. No correctness feedback yet.')
        labels = {o['id']: o['text'] for o in q['options']}
        st.write('Your prediction: **' + labels[lab['pending_answer']] + '**')
        with st.form(lab['token']):
            reason = reason_radio()
            if st.form_submit_button('Test my reasoning →', type='primary'):
                submit({'reason_id': reason})
    elif stage == 'PROBE':
        st.info('Your answer and reason do not identify a clear rule. Try one more example before feedback.')
        with st.form(lab['token']):
            question_display(q)
            answer = answer_radio(q)
            reason = reason_radio()
            if st.form_submit_button('Submit probe →', type='primary'):
                submit({'selected_option_id': answer, 'reason_id': reason})
        help_controls()
    elif stage == 'UNCLEAR':
        st.warning('Cause unclear. These choices do not support a specific diagnosis.')
        st.write('Explore an authored example of a common rule error. It will be labelled as a guided example.')
        if st.button('Explore a guided example →', type='primary'):
            submit({'action': 'guided'})
    elif stage == 'TEST_RULE':
        st.info(lab['evidence'] if lab['candidate'] else 'Guided example — this rule is not an inferred diagnosis.')
        st.latex(pack['faulty_rule_latex'])
        counterexample = find_counterexample(fid, pack['parameters'])
        if counterexample is None:
            st.warning('No counterexample in this test set. This does not establish equivalence.')
        with st.form(lab['token']):
            x = st.number_input('Test value of x', -5, 5, counterexample['x'] if counterexample else 0, 1)
            prediction = st.radio('Will the original and rewrite have equal values?',
                                  ['They will agree', 'They will disagree'], index=None)
            if st.form_submit_button('Run test →', type='primary'):
                submit({'x': x, 'predict_equal': None if prediction is None else prediction == 'They will agree'})
    elif stage == 'INSPECT_CONTRADICTION':
        st.caption('Candidate rule' if lab['candidate'] else 'Guided example, not a diagnosis')
        x = st.slider('Change x and rerun the calculation', -5, 5, lab['test_result']['x'], key=f'bench_{lab["session_id"]}')
        bench_values(x)
        observed = lab['test_result']
        st.caption('Your initial test prediction: ' + ('agreement' if observed['predict_equal'] else 'disagreement') + '.')
        if fid == 'distribution':
            st.write('What broke: the constant stayed 2, but three groups contain 3 × 2 = 6.')
        elif fid == 'square':
            st.write('What broke: the two cross products were omitted. At x=0 they vanish, so that one test agrees.')
        else:
            st.write('What broke: the second term did not change sign with the rest of the bracket.')
        if st.button('Repair the rule →', type='primary'):
            submit({'action': 'repair'})
    elif stage == 'REPAIR_RULE':
        if lab['feedback']:
            st.warning(lab['feedback'])
        with st.form(lab['token']):
            question_display(q)
            answer = answer_radio(q)
            reason = st.radio('Complete the explanation', [pack['correct_rule_id'], pack['faulty_rule_id']], index=None,
                              format_func=lambda rid: pack['repair_reason'] if rid == pack['correct_rule_id']
                              else next(r['text'] for r in pack['reason_options'] if r['id'] == rid),
                              key=f'{lab["token"]}_repair_reason')
            if st.form_submit_button('Verify repair →', type='primary'):
                submit({'selected_option_id': answer, 'reason_id': reason})
        help_controls()
    elif stage == 'REPAIR_VERIFIED':
        repair_summary()
        if st.button('Try the Transfer Challenge →', type='primary'):
            submit({'action': 'transfer'})
    else:
        st.info('This lab is ready for transfer checks or has a result in the ledger.')
        st.button('Open Transfer Challenge →', on_click=navigate, args=('Transfer Challenge',), type='primary')
        st.button('Start a new investigation', on_click=navigate, args=('Debug Lab', fid, True))


def render_transfer():
    st.markdown('<div class="eyebrow">02 / Transfer Challenge</div>', unsafe_allow_html=True)
    st.title('Does the repair travel?')
    st.write('Two different problems. One symbolic check, then a change of representation.')
    st.caption('New-item correctness is limited evidence. It does not prove mastery or durable learning.')
    st.subheader(pack['title'])
    if lab['stage'] == 'TRANSFER':
        q = current_question(lab, content)
        st.progress(lab['transfer_index'] / 2, text=f'Check {lab["transfer_index"] + 1} of 2')
        if any(a['question_id'] == q['id'] for a in progress['attempts']):
            st.warning('You have already seen this item. This repeat is practice and cannot count as an unassisted pass.')
        if fid == 'distribution' and lab['transfer_index'] == 1:
            st.markdown('''<svg viewBox="0 0 400 135" width="360" role="img" aria-label="Rectangle with height 4 and width y plus 3">
                <rect x="65" y="20" width="270" height="80" rx="3" fill="#e6f3ef" stroke="#087f74" stroke-width="2"/>
                <text x="35" y="66" fill="#17253d" font-size="18">4</text>
                <text x="175" y="125" fill="#17253d" font-size="18">y + 3</text></svg>''', unsafe_allow_html=True)
        with st.form(lab['token']):
            question_display(q)
            answer = answer_radio(q)
            if st.form_submit_button('Submit check →', type='primary'):
                submit({'selected_option_id': answer})
        help_controls()
    elif lab['stage'] == 'TRANSFER_FEEDBACK':
        results = lab['transfer_results']
        if len(results) == 1:
            st.info('Response saved. Complete the second check before seeing the outcome.')
            if st.button('Next: change of representation →', type='primary'):
                submit({'action': 'next'})
        else:
            label, passed = transfer_outcome(results)
            (st.success if passed else st.warning)(label)
            for i, result in enumerate(results):
                q = question_by_id(content, result['question_id'])
                correct_text = next(o['text'] for o in q['options'] if o['id'] == q['correct_option_id'])
                st.write(f'**{"Symbolic" if i == 0 else "Representation"}:** '
                         f'{"Correct" if result["correct"] else "Needs practice"}'
                         f'{" · assisted / previously seen" if result["help_used"] else " · unassisted"}')
                st.caption('Reviewed answer: ' + correct_text)
            st.write(pack['canonical_explanation'])
            if st.button('Save outcome to ledger →', type='primary'):
                submit({'action': 'next'})
    else:
        st.info('Complete a rule investigation to unlock its transfer checks. Existing evidence is retained.')
        st.button('Go to Debug Lab →', on_click=navigate, args=('Debug Lab',), type='primary')
        if lab['stage'] == 'LEDGER':
            st.button('Open Repair Ledger →', on_click=navigate, args=('Repair Ledger',))


def render_review(record, rp):
    now = clock()
    due = record['next_check_at'] is not None and datetime.fromisoformat(record['next_check_at']) <= now
    if not record['next_check_at']:
        return
    st.caption('Next check: ' + datetime.fromisoformat(record['next_check_at']).astimezone(now.tzinfo).strftime('%d %b %Y, %I:%M %p IST'))
    if not due:
        if st.checkbox('Preview a future review (not recorded)', key=f'preview_{record["record_id"]}'):
            # Rehearse a worked item, never leak the actual unseen delayed question.
            st.info('Preview only: a worked-example rehearsal. No due date or evidence changes.')
            st.latex(rp['original_latex'])
            st.write(rp['canonical_explanation'])
            st.caption('The actual delayed question stays hidden until it is due.')
        return
    q = delayed_question(record, content)
    cycle = f'{record["record_id"]}_{len(record["events"])}'
    token_key = 'review_token_' + cycle
    if token_key not in st.session_state:
        st.session_state[token_key] = str(uuid4())
    st.markdown('#### Due retrieval check')
    st.caption('The small authored review bank is reused after three successes. This remains limited evidence.')
    if st.button('Show review help (marks this review assisted)', key='help_' + cycle):
        st.session_state['review_help_' + cycle] = True
    assisted = st.session_state.get('review_help_' + cycle, False)
    if assisted:
        st.info(rp['canonical_explanation'])
    with st.form('review_' + cycle):
        question_display(q)
        labels = {o['id']: o['text'] for o in q['options']}
        choice = st.radio('Review answer', list(labels), index=None, format_func=labels.get)
        reasons = {r['id']: r['text'] for r in rp['reason_options']}
        reason = st.radio('Review reasoning', list(reasons), index=None, format_func=reasons.get)
        if st.form_submit_button('Submit due review', type='primary'):
            try:
                st.session_state.progress = review(st.session_state.progress, rp['id'],
                    {'selected_option_id': choice, 'reason_id': reason, 'help_used': assisted},
                    st.session_state[token_key], now, content)
                st.rerun()
            except DomainError as exc:
                st.error(str(exc))


def render_ledger():
    st.markdown('<div class="eyebrow">03 / Repair Ledger</div>', unsafe_allow_html=True)
    st.title('Keep the evidence.')
    st.write('The rule, the experiment, the repair — and what happened when you tried it again.')
    suggested_fid, action, page = recommend_next(progress, clock())
    st.info('Recommended next action: ' + action + (f' · {pack_by_id(content, suggested_fid)["title"]}' if suggested_fid else ''))
    if suggested_fid:
        suggested_record = get_record(progress, suggested_fid)
        suggested_lab = st.session_state.labs.get(suggested_fid)
        restart = bool(suggested_record and (suggested_record['status'] == 'reopened'
                       or (suggested_lab and suggested_lab['stage'] == 'LEDGER'
                           and suggested_record['status'] in ('unclear', 'repaired'))))
        if suggested_lab and suggested_lab['stage'] in ('TRANSFER', 'TRANSFER_FEEDBACK'):
            page = 'Transfer Challenge'
        st.button('Continue recommended action →', on_click=navigate,
                  args=(page, suggested_fid, restart), type='primary')
    a, b, c = st.columns(3)
    a.metric('Rule families explored', len(progress['records']))
    b.metric('Transfer gates passed', sum(r['status'] in ('transfer_passed', 'delayed_check_passed') for r in progress['records']))
    c.metric('Delayed checks passed', sum(r['successful_delayed_checks'] for r in progress['records']))
    if not progress['records']:
        st.markdown('### Your first experiment starts in the lab.')
        st.caption('No evidence recorded yet. Predictions become evidence when their reasoning is submitted.')
    for record in progress['records']:
        rp = pack_by_id(content, record['family_id'])
        with st.container(border=True):
            st.subheader(rp['title'])
            st.badge(record['status'].replace('_', ' ').title())
            cols = st.columns(2)
            with cols[0]:
                st.markdown('**Original candidate**')
                if record['original_rule_id']:
                    st.latex(rp['faulty_rule_latex'])
                else:
                    st.caption('No specific faulty rule established by the recorded choices.')
                if record['counterexample']:
                    ce = record['counterexample']
                    st.write(f'Test: x={ce["x"]} → {ce["original_value"]} ≠ {ce["rewritten_value"]}')
                    if not record['original_rule_id']:
                        st.caption('Guided mathematical example, not a personal diagnosis.')
            with cols[1]:
                st.markdown('**Chosen repair**')
                if record['repaired_rule_id']:
                    st.latex(rp['correct_rule_latex'])
                else:
                    st.caption('No repair submitted; direct transfer can follow correct initial reasoning.')
                assisted = sum(a['help_used'] for a in progress['attempts'] if a['attempt_id'] in record['attempt_ids'])
                st.caption(f'{len(record["attempt_ids"])} recorded responses · {assisted} assisted / practice')
            with st.expander('Evidence timeline'):
                for e in record['events']:
                    date = datetime.fromisoformat(e['occurred_at']).astimezone(clock().tzinfo).strftime('%d %b %Y %H:%M IST')
                    st.markdown(f'**{e["kind"].title()} · {e["details"]["status"].replace("_", " ")}**')
                    st.caption(date)
                    st.write(e['details']['note'])
            render_review(record, rp)
            if record['status'] in ('reopened', 'unclear', 'candidate', 'tested', 'repaired'):
                saved_lab = st.session_state.labs.get(rp['id'])
                restart = record['status'] == 'reopened' or bool(saved_lab and saved_lab['stage'] == 'LEDGER')
                target = 'Transfer Challenge' if saved_lab and saved_lab['stage'] in ('TRANSFER', 'TRANSFER_FEEDBACK') else 'Debug Lab'
                st.button('Return to this rule →', key='return_' + record['record_id'],
                          on_click=navigate, args=(target, rp['id'], restart))
    st.caption('Intervals: 1 day after transfer, then 3 days, then 7 days. Prototype scheduling, not a calibrated memory model.')
    st.caption('Session progress can disappear on refresh or server restart. Export JSON to keep it.')


page = st.session_state.navigation
if page == 'Debug Lab':
    render_lab()
elif page == 'Transfer Challenge':
    render_transfer()
else:
    render_ledger()

st.divider()
st.caption('Authored algebra module · No live AI · Candidate rules, not certain diagnoses · No learning-efficacy claims')
