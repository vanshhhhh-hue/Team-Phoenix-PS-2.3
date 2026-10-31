"""Authored NLM lessons, persisted learning loop, linked recall and evidence views."""
from datetime import datetime
import streamlit as st

from engine import DomainError
from ledger import clock
from presentation import date_label
import nlm
import debugger as debugger_domain
from nlm_visuals import render, render_question
from journey import UNITS, journey, note_sections
from experiments import CONTROLS, scenario
from study_flow import record_experiment,save_draft
from workspace import card_queue,NLM_ID


def evidence(progress):
    rows=nlm.insights(progress,learner='My learning')
    st.subheader('Newton’s Laws · learning evidence')
    st.caption('Candidate explanations remain uncertain. First responses, assisted repair, transfer and delayed recall are separate evidence; none establishes mastery.')
    if rows:
        pack=nlm.load_pack(); candidates={m['id']:m['claim'] for m in pack['misconceptions']}
        for row in rows:
            with st.container(border=True):
                st.markdown('**'+row['learner']+' · '+row['concept'].title()+'**')
                st.write(row['status'].capitalize()+' · '+row['review'])
                st.caption(('First response correct' if row['first_correct'] else 'First response incorrect')
                           +f' · {row["hints_used"]} hint(s) · {row["retries"]} retry/retries'
                           +' · solution '+('revealed' if row['solution_revealed'] else 'not revealed'))
                candidate=row['candidate'].removeprefix('Your answer may suggest ')
                if candidate in candidates: st.write('Your answer may suggest: '+candidates[candidate]+'. This remains uncertain.')
                elif candidate=='calculation': st.write('Possible calculation / unit error; check algebra separately from physical reasoning.')
                if row['immediate_follow_up']:
                    st.write('Next: attempt a fresh transfer, then return for delayed review. Due: '+str(row['due_at']))
                else:
                    st.write('Next: revisit the linked concept and prerequisite scaffold, then answer a fresh related question.')
                if row['repeat_practice']: st.caption('Repeated primary item · practice, excluded from new first-response evidence.')
        with st.expander('Detailed response evidence'):
            st.dataframe(rows,hide_index=True,width='stretch')
    else: st.info('Answer a Newton’s Laws question to begin collecting evidence.')


def draft_editor(state,commit,material,activity,item,learner,label,key):
    draft=next((d for d in state['drafts'] if d['learner']==learner and d['activity_id']==activity and d['item_id']==item),None)
    text=st.text_area(label,value=draft['text'] if draft else '',max_chars=4000,key=key)
    st.caption(('Saved in this session · ungraded' if st.session_state.get('demo_workspace') else 'Saved locally · ungraded') if draft and text==draft['text'] else 'Unsaved writing · ungraded')
    if st.button('Save writing',key='save_'+key):
        try:
            commit(save_draft(state,material,activity,item,text,learner=learner));st.rerun()
        except (DomainError,OSError) as exc:st.error(str(exc))


def page(state,commit):
    pack=nlm.load_pack()
    if 'card_notice' in st.session_state:st.success(st.session_state.pop('card_notice'))
    st.title('Newton’s Laws of Motion')
    st.caption('JEE Main 2026 · Physics Unit 3 · Authored offline pack v1 · No API key needed')
    if not state['nlm']['installed']:
        st.write('Explore visual lessons, make a prediction, and practise with hints and fresh questions. Uploads and your existing progress remain in your library.')
        if st.button('Install authored Newton pack',type='primary'):
            commit(nlm.install(state)); st.rerun()
        return
    if st.session_state.get('demo_workspace'):
        learner='My learning'
        st.caption('User 1 · Sample material and practice history')
    else:
        with st.expander('Additional sample learners'):
            learner=st.selectbox('Learner workspace',['My learning','Demo Learner A','Demo Learner B'],key='nlm_learner')
            st.caption('Additional sample learners have separate evidence.')
    tab={'Quiz':'Practice','Flash Cards':'Flashcards','Insights':'Evidence'}.get(st.session_state.get('study_nav'),'Learn visually')
    st.session_state.nlm_tab=tab
    concepts={c['id']:c for c in pack['concepts']}

    def act(s,action,answer=None):
        try:
            revision=len(s['events'])
            updated=nlm.event(state,s['id'],action,answer,f'{s["id"]}:{revision}',revision)
            commit(updated); st.rerun()
        except (DomainError,OSError) as exc: st.error(str(exc))

    def practice(qid):
        try:
            updated,sid=nlm.start(state,qid,learner)
            commit(updated); st.session_state['nlm_active_'+learner]=sid
            st.session_state.nlm_next_tab='Practice'; st.rerun()
        except (DomainError,OSError) as exc: st.error(str(exc))

    if tab=='Learn visually':
        unit=st.selectbox('Learning unit',list(UNITS),format_func=lambda u:u['title'],key='nlm_unit')
        st.write(unit['outcome'])
        # Preserve a linked card's concept by selecting its containing unit.
        chosen=st.session_state.get('nlm_concept')
        if chosen not in unit['concepts']:
            st.session_state.nlm_concept=unit['concepts'][0]
        cid=st.selectbox('Concept',list(unit['concepts']),format_func=lambda c:concepts[c]['title'],key='nlm_concept')
        c=concepts[cid]
        st.subheader(c['title']); st.write(c['explanation'])
        st.info(c['formula_assumptions'])
        with st.expander('Prerequisite mini-lessons'):
            for dep in c['prerequisite_ids']:
                node=next(x for x in pack['prerequisites']+pack['concepts'] if x['id']==dep)
                st.markdown('**'+node['title']+'**'); st.write(node['explanation'])
        st.write('**Learning goals:** '+'; '.join(c['goals']))
        previous=[e for e in state['activity_events'] if e['kind']=='experiment' and e['learner']==learner and e['item_id']==cid]
        prior_parameters=previous[-1]['value']['parameters'] if previous else {}
        values={}
        for key,label,lo,hi,default in CONTROLS[cid]:
            values[key]=st.slider(label,float(lo),float(hi),float(prior_parameters.get(key,default)),.1 if hi<=1 or key.startswith('mass') or key=='duration' else .5,key='experiment_'+cid+'_'+key)
        observed=scenario(cid,**values)
        st.caption(observed['assumptions'])
        linked=note_sections(state,cid)
        if linked:
            st.subheader('From your uploaded notes')
            st.caption('Matched by topic phrases. These excerpts supplement this authored lesson; uploaded quizzes and cards use the uploaded source.')
            for note in linked:
                with st.expander(note['title']+' · '+note['chunk_id']):
                    st.write(note['text'])
                    st.caption('Matched: '+', '.join(note['matches']))
                    if st.button('Study this note’s quiz and cards',key='note_'+cid+note['document_id']+note['chunk_id']):
                        st.session_state.study_next_document=note['document_id']
                        st.session_state.study_next_page='Library'; st.rerun()
        signature=(cid,tuple(sorted(values.items())))
        if st.session_state.get('nlm_prediction_parameters')!=signature:
            st.session_state['predict_'+cid]=''
            st.session_state.pop('structured_predict_'+cid,None)
            st.session_state.nlm_prediction_parameters=signature
        prediction=st.radio('Choose a prediction',observed['prediction_options'],index=None,key='structured_predict_'+cid)
        explanation=st.text_input('Predict first: what changes, and why?',max_chars=4000,key='predict_'+cid)
        if st.button('Reveal experiment',disabled=prediction is None):
            try:
                commit(record_experiment(state,cid,values,observed['prediction_options'].index(prediction),explanation,learner));st.rerun()
            except (DomainError,OSError) as exc:st.error(str(exc))
        saved=[e for e in state['activity_events'] if e['kind']=='experiment' and e['learner']==learner and e['item_id']==cid]
        if saved and saved[-1]['value']['parameters']==observed['parameters']:
            last=saved[-1]['value']
            st.image(observed['svg'],width='stretch');st.caption(observed['alt'])
            st.write(observed['result'])
            st.write('Your saved prediction: '+observed['prediction_options'][last['prediction']])
            if last['explanation']:st.write('Your saved explanation (ungraded): '+last['explanation'])
            st.info('Your prediction matches this model.' if last['prediction']==0 else 'Compare your prediction with the model result and stated assumptions.')
            st.caption('Saved comparison · assisted learning, not an independent grade. Arrows are schematic; quantities and units are stated in text.')
            st.write('**Worked example (fixed scenario):** '+c['worked_example'])
        else:st.caption('Choose a prediction before revealing. Changed controls require a new prediction; previous saved comparisons remain in your backup.')
        if st.button('Practise this concept',type='primary'): practice(next(r['question_id'] for r in journey(state,learner) if r['id']==cid))
    elif tab=='Practice':
        primary=[q for q in pack['questions'] if q['role']=='primary']
        learner_sessions=[s for s in state['nlm']['sessions'] if s['learner']==learner]
        unfinished=[s for s in learner_sessions if nlm.view(s)['step'] not in ('COMPLETE','RECAP')]
        seen={r['question_id'] for s in learner_sessions for r in nlm.view(s)['responses']}
        stats=nlm.insights(state['nlm'],learner)
        weak={r['concept'] for r in stats if not r['first_correct'] and not r['repeat_practice']}
        eligible=sorted(primary,key=lambda q:(q['id'] in seen,q['concept_id'] not in weak,q['id']))
        default=unfinished[-1]['question_id'] if unfinished else eligible[0]['id']
        if not learner_sessions: default='second-1' if learner=='Demo Learner B' else 'inertia-1'
        st.caption('Suggested activity: resume unfinished work; otherwise unseen starting questions, prioritising concepts with incorrect first responses. You can choose another topic.')
        selected=st.selectbox('Choose a starting question',[q['id'] for q in primary],index=None if 'nlm_choose_'+learner in st.session_state else [q['id'] for q in primary].index(default),
                              format_func=lambda qid:concepts[nlm.question(qid)['concept_id']]['title']+' · '+nlm.question(qid)['prompt'][:65],key='nlm_choose_'+learner)
        if st.button('Start / resume this question',type='primary'): practice(selected)
        selected_concept=nlm.question(selected)['concept_id']
        if selected_concept in ('inertia','second'):
            if st.button('Investigate with history-aware debugger'):
                try:
                    updated,debug_sid=debugger_domain.start(state,'motion' if selected_concept=='inertia' else 'mass',learner)
                    commit(updated); st.session_state['debugger_active_'+learner]=debug_sid
                    st.session_state.debugger_learner=learner
                    st.session_state.study_next_page='Debugger'; st.rerun()
                except (DomainError,OSError) as exc: st.error(str(exc))
        sessions=[s for s in state['nlm']['sessions'] if s['learner']==learner]
        if not sessions: return
        ids=[s['id'] for s in sessions]
        active_key='nlm_active_'+learner
        if st.session_state.get(active_key) not in ids: st.session_state[active_key]=ids[-1]
        with st.expander('Previous practice'):
            sid=st.selectbox('Saved learning session',ids,format_func=lambda sid:next(nlm.question(s['question_id'])['prompt'][:70]+' · '+datetime.fromisoformat(s['created_at']).strftime('%d %b, %I:%M %p') for s in sessions if s['id']==sid),key=active_key)
        s=next(s for s in sessions if s['id']==sid); v=nlm.view(s); q=nlm.question(v['question_id'])
        st.badge({'UNANSWERED':'Try this question','HINT_1':'Try a hint','HINT_2':'Try another hint','FIRST_RESPONSE':'First answer saved','SOLUTION':'Review the explanation','FOLLOW_UP':'Try a new example','REMEDIATION':'Review this step','RECAP':'Review the recap','COMPLETE':'Check saved','TRANSFER':'Try a new situation','DELAYED_REVIEW':'Scheduled check'}.get(v['step'],'Continue practice'))
        st.caption('Actions are saved locally. Optional writing needs its Save button.')
        st.caption(str(nlm.remaining_unseen_checks(state,q['concept_id'],learner))+' unused reviewed checks remain for this concept.')
        st.markdown('### '+q['prompt']); st.caption(q['assumptions'])
        if q['scene']:
            svg,alt=render_question(q['scene']); st.image(svg,width='stretch'); st.caption(alt)
        answerable=v['step'] in ('UNANSWERED','HINT_1','HINT_2','RETRY','FOLLOW_UP','TRANSFER','DELAYED_REVIEW')
        if answerable:
            if v['step'].startswith('HINT'):
                st.warning('Your answer may suggest a gap. One response cannot identify its cause.')
                candidate=next((m for m in pack['misconceptions'] if m['id']==v['candidate']),None)
                if candidate:
                    st.info('Reasoning probe: '+candidate['probe'])
                    st.caption('Candidate: '+candidate['claim'])
                    st.info(candidate['hint'])
                elif v['candidate']=='calculation':
                    st.info('Calculation scaffold: keep the force direction; convert mass to kg, write a = F/m and check N/kg = m/s². A numerical slip does not establish a conceptual misconception.')
                if not v['probes']:
                    probe=st.radio('What best describes your reasoning?', ['I used a physical rule','I understood the rule but may have made a calculation / unit slip','I am unsure'],index=None,key='probe_'+sid)
                    if st.button('Record reasoning probe',disabled=probe is None):
                        act(s,'probe', ['concept','calculation','uncertain'][['I used a physical rule','I understood the rule but may have made a calculation / unit slip','I am unsure'].index(probe)])
                if q['concept_id']=='inertia':
                    svg,alt,_=render('block',force=0.)
                    st.image(svg,width='stretch')
                    st.caption('Smooth-floor model after release. Compare with rough ice: friction supplies a backward force. Predict what changes as friction tends to zero. '+alt)
            for hint in q['hints'][:v['hints']]: st.info(hint)
            with st.form('nlm_answer_'+sid+'_'+str(len(s['events']))):
                answer=st.radio('Your prediction / answer',range(4),format_func=lambda i:q['options'][i],index=None)
                if st.form_submit_button('Check response'):
                    act(s,'answer',answer)
            if v['phase']=='primary' and v['hints']<2:
                if st.button('Request a hint'): act(s,'hint')
            if v['phase']=='primary' and v['hints']>=1:
                if st.button('Show solution'): act(s,'solution')
            if v['phase']!='primary':
                st.caption('Fresh independently graded reasoning check. Its answer is hidden until you respond.')
        if v['step']=='FIRST_RESPONSE':
            st.success('Correct. Your first response is saved separately from later checks.')
            st.write('A correct option alone does not demonstrate understanding. Explain the principle in a changed situation next.')
            if nlm.eligible_check(state,sid,'continue'):
                if st.button('Try a fresh reasoning check'): act(s,'continue')
            else: st.info('No unused reasoning check remains for this concept. Review the lesson or choose another concept.')
        if v['solution']:
            st.subheader('Structured solution')
            st.write('Answer: '+q['options'][q['correct_index']])
            for step in q['solution_steps']: st.write(step)
            st.caption('Authored explanation · references: '+', '.join(q['evidence_refs']))
            for ref in q['evidence_refs']:
                source=pack['sources'][ref]
                st.markdown('['+ref+' · '+source['section']+']('+source['url']+')')
            draft_editor(state,commit,NLM_ID,sid,q['id'],learner,'Teach-back: what principle explains this result? (optional, not graded)','nlm_teach_'+sid+q['id'])
            c=concepts[q['concept_id']]
            st.write('**Visual recap:** '+c['explanation'])
            if q['concept_id']=='inertia':
                svg,alt,_=render('block',force=0.)
                st.image(svg,width='stretch'); st.caption('Released puck model: '+alt)
            st.write('**Prerequisite scaffold:**')
            for dep in c['prerequisite_ids']:
                node=next(x for x in pack['prerequisites']+pack['concepts'] if x['id']==dep)
                st.write(node['title']+': '+node['explanation'])
            if v['step'] in ('SOLUTION','REMEDIATION'):
                if nlm.eligible_check(state,sid,'continue'):
                    if st.button('Try a fresh related question'): act(s,'continue')
                else: st.info('No unused related check remains. Review this explanation or choose another concept. Repeated practice stays available.')
        if v['step'] in ('COMPLETE','RECAP'):
            if v['last_correct']:
                st.success('Check passed. This is immediate evidence, not a mastery claim.')
                st.write(q['solution_steps'][-1])
            else: st.info('Two remediation cycles reached. Read the recap and return for a scheduled retry.')
            st.caption('Scheduled check: '+date_label(v['due_at']))
            used={r['question_id'] for r in v['responses']}
            fresh=[x for x in pack['questions'] if x['concept_id']==q['concept_id'] and x['role'] in ('follow_up','transfer') and x['id'] not in used]
            if nlm.eligible_check(state,sid,'transfer') and v['step']=='COMPLETE' and v['transfer'] is None:
                if st.button('Try a further transfer'): act(s,'transfer')
            if nlm.eligible_check(state,sid,'delayed') and v['due_at'] and clock()>=datetime.fromisoformat(v['due_at']):
                if st.button('Start delayed review'): act(s,'delayed')
    elif tab=='Flashcards':
        all_cards=pack['flashcards']
        mode=st.radio('Card view',['Due reviews','New cards','Preview all'],index=0 if any(r['learner']==learner for r in state['nlm']['reviews']) else 1,horizontal=True,key='nlm_card_view')
        queue=card_queue(state,NLM_ID,{'Preview all':'preview','New cards':'new','Due reviews':'due'}[mode],learner=learner)
        cards=queue['items']
        st.caption(f"{queue['due_count']} due · {queue['new_count']} new · {queue['upcoming_count']} upcoming")
        if not cards:
            st.info('No scheduled reviews are due.' if mode=='Due reviews' else 'No new cards remain.' if mode=='New cards' else 'No cards available.')
            if queue['new_count']:st.write(f"Study {queue['new_count']} new cards using New cards.")
            if queue['next_due_at']:st.caption('Next scheduled review: '+date_label(queue['next_due_at']))
            return
        cardmap={c['id']:c for c in cards}
        if st.session_state.get('nlm_card') not in cardmap: st.session_state.nlm_card=cards[0]['id']
        cid=st.selectbox('Recall card',list(cardmap),format_func=lambda k:cardmap[k]['front'],key='nlm_card')
        c=cardmap[cid]; records=[r for r in state['nlm']['reviews'] if r['card_id']==cid and r['learner']==learner]
        due=not records or clock()>=datetime.fromisoformat(records[-1]['due_at'])
        st.caption(f'{len(cards)} cards remain in this view')
        st.subheader(c['front'])
        st.caption(c['category'].replace('_',' ')+' · open recall')
        if c['category']=='diagram_interpretation': st.caption('Predict the force directions before revealing the reviewed diagram.')
        draft_editor(state,commit,NLM_ID,'cards',cid,learner,'Write your recalled explanation before revealing','nlm_recall_'+learner+cid)
        key='nlm_reveal_'+learner+cid+str(len(records))
        if st.button('Reveal recall card'): st.session_state[key]=True
        if st.session_state.get(key):
            st.write(c['back'])
            visual=scenario(c['concept_id'])
            st.image(visual['svg'],width='stretch');st.caption(visual['alt']);st.write(visual['result'])
            concept=concepts[c['concept_id']]
            st.write(concept['explanation'])
            for ref in c['evidence_refs']:
                source=pack['sources'][ref]
                st.markdown('['+ref+' · '+source['section']+']('+source['url']+')')
            st.caption('Open recall · self-rated, not objectively graded. Ratings update the spaced schedule; flipping does not count as learning evidence.')
            for col,rating in zip(st.columns(4),('Again','Hard','Good','Easy')):
                if col.button(rating,key='nlm_rate_'+rating,disabled=not due):
                    try:
                        commit(nlm.review_card(state,cid,rating,learner+cid+str(len(records)),learner))
                        saved=[r for r in st.session_state.study['nlm']['reviews'] if r['learner']==learner and r['card_id']==cid][-1]
                        st.session_state.card_notice='Recall rating saved. Next review: '+date_label(saved['due_at']);st.rerun()
                    except (DomainError,OSError) as exc: st.error(str(exc))
        if not due: st.caption('Next due: '+date_label(records[-1]['due_at']))
        if st.button('Open linked visual lesson'):
            st.session_state.nlm_unit=next(u for u in UNITS if c['concept_id'] in u['concepts']); st.session_state.nlm_concept=c['concept_id']; st.session_state.nlm_next_tab='Learn visually'; st.rerun()
        if st.button('Practise linked concept'): practice(c['practice_id'])
    elif tab=='Evidence': evidence(state['nlm'])
    else:
        st.write(pack['provenance']); st.write(pack['source_note'])
        for key,source in pack['sources'].items():
            st.markdown(f'[{key} · {source["section"]}]({source["url"]}) · {source["role"]}')
        st.write('Inventory: 12 Unit 3 concepts, 4 prerequisite mini-lessons, 18 candidate misconceptions, 36 primary MCQs, 36 follow-ups, 24 open-recall cards, 8 deterministic visual templates.')
        st.caption('Vertical-circle energy and detailed collision mechanics are outside this core pack. Numerical situations currently use validated MCQ choices.')
    if learner.startswith('Demo Learner '):
        with st.expander('Demo-only reset'):
            st.caption('Only '+learner+' Newton and linked debugger records will be removed. Uploaded materials and My learning are preserved.')
            confirmed=st.checkbox('Reset only '+learner+' evidence',key='reset_'+learner)
            if st.button('Reset selected demo learner',disabled=not confirmed):
                commit(nlm.reset_demo(state,learner)); st.rerun()
