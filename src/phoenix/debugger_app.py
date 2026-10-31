"""Student-facing repair workspace. No model calls or opaque learner scores."""
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
import debugger as db
from debugger_content import QUESTIONS,TOPICS,REPAIRS
from learner_model import build_learner_summary
from learning_events import exposed_questions
from source_retrieval import retrieve_repair_sources
from ledger import clock
from engine import DomainError
from study_flow import record_debugger_experiment
from experiments import debugger_comparison
from workspace import NLM_ID


def local_date(value):
    return datetime.fromisoformat(value).astimezone(ZoneInfo('Asia/Kolkata')).strftime('%d %b %Y, %I:%M %p IST')


def experiment(topic,key,state,commit,ep):
    """An original bounded comparison; changing conditions clears the prediction."""
    with st.container(border=True):
        st.subheader('Predict, compare, explain')
        if topic=='motion':
            speed=st.slider('Initial rightward speed (m/s)',2,10,6,key=key+'speed')
            mass=st.slider('Mass in experiment (kg)',1,5,2,key=key+'mass')
            force=st.slider('Opposing sliding friction (N)',1,6,2,key=key+'force')
            signature=(speed,mass,force)
            labels=['The smooth-track object keeps its speed; the rough-track object slows',
                    'Both objects need a forward resultant to keep moving']
            st.caption('Inertial frame; horizontal track; vertical forces balance. Rough-track friction opposes sliding. At rest the object stays at rest.')
        else:
            mass=st.slider('Mass of trolley A (kg)',1,5,2,key=key+'mass')
            force=st.slider('Same resultant on both trolleys (N)',1,20,8,key=key+'force')
            signature=(mass,force); labels=['B, with twice the mass, has half the acceleration','B has twice the acceleration']
            st.caption('Inertial frame; positive constant masses; both trolleys experience the stated constant resultant.')
        signature_key=key+'signature'
        if st.session_state.get(signature_key)!=signature:
            st.session_state[signature_key]=signature
            st.session_state.pop(key+'revealed',None)
            st.session_state.pop(key+'prediction',None)
        prediction=st.radio('Your prediction',labels,index=None,key=key+'prediction')
        parameters=dict(mass=mass,force=force)
        if topic=='motion':parameters['speed']=speed
        if st.button('Run comparison',key=key+'run',disabled=prediction is None):
            try:
                commit(record_debugger_experiment(state,ep['id'],parameters,labels.index(prediction)));st.rerun()
            except (DomainError,OSError) as exc:st.error(str(exc))
        saved=[e for e in state['activity_events'] if e['kind']=='debugger_experiment' and e['activity_id']==ep['id']]
        if saved and saved[-1]['value']['parameters']==parameters:
            st.info('Your saved prediction matches this model.' if saved[-1]['value']['prediction']==0 else 'Compare your saved prediction with the model result.')
            if topic=='motion':
                data={'Time (s)':list(range(5)),'Ideal smooth track (m/s)':[speed]*5,
                      'Rough track (m/s)':[max(0,speed-force/mass*t) for t in range(5)]}
                st.line_chart(data,x='Time (s)',y=['Ideal smooth track (m/s)','Rough track (m/s)'])
                st.write('Zero horizontal resultant preserves velocity. Friction produces a change of velocity; while sliding, acceleration is leftward.')
                st.caption('Text alternative: smooth-track speed stays '+str(speed)+' m/s. Rough-track speeds at seconds 0–4: '+', '.join(f'{v:g}' for v in data['Rough track (m/s)'])+' m/s.')
            else:
                st.metric('A acceleration',f'{force/mass:g} m/s²')
                st.metric('B acceleration (twice the mass)',f'{force/(2*mass):g} m/s²')
                st.write('a = F_net/m. A larger positive mass gives a smaller acceleration at fixed resultant.')
            st.caption('This experiment is assisted learning, not an independent assessment. Changing a control requires a new prediction.')


def evidence(state,learner='My learning',episode_id=None):
    summary=build_learner_summary(state,learner,clock(),episode_id)
    with st.expander('Learning evidence and support history'):
        st.caption('Revisable prototype rules. Counts are observations, not diagnostic probabilities or proof that an explanation caused improvement.')
        st.dataframe([dict(cause=h['label'],status=h['status'],support=len(h['support']),
                           counterevidence=len(h['contradict'])) for h in summary['hypotheses'].values()],hide_index=True,width='stretch')
        for name,row in summary['support_outcomes'].items():
            st.write(f'{name}: {row["passed"]}/{row["attempted"]} independent checks passed; delayed {row["delayed_passed"]}/{row["delayed"]}.')
        if summary['events']:
            st.dataframe([dict(evidence_id=r['id'],origin=r['origin'],role=r['role'],correct=r['correct'],
                               assistance=r['helped'],repeat=r['repeat'],previous_exposure=r['exposed'],confidence_self_report=r['confidence'])
                          for r in summary['events']],hide_index=True,width='stretch')


def page(state,commit):
    st.title('Misconception Debugger')
    st.write('Locate the difficulty. Try a targeted repair. Check it on something new.')
    st.caption('Reviewed Newton activities · local history · no API request · candidate explanations stay revisable')
    upload_scope=st.session_state.get('study_material',NLM_ID)!=NLM_ID
    learner='My learning' if upload_scope or st.session_state.get('demo_workspace') else st.selectbox('Debugger learner',db.LEARNERS,key='debugger_learner')
    if 'debugger_next_tab' in st.session_state:
        st.session_state.debugger_tab=st.session_state.pop('debugger_next_tab')
    if 'debugger_history_next_'+learner in st.session_state:
        st.session_state['debugger_history_'+learner]=st.session_state.pop('debugger_history_next_'+learner)
    current=state['debugger']['history'].get(learner,True)
    enabled=st.toggle('Use earlier attempts to personalise support',value=current,key='debugger_history_'+learner)
    if enabled!=current:
        commit(db.set_history(state,learner,enabled)); st.rerun()
    st.caption('When off, only this episode informs support. Previously displayed tasks still count as exposed. History stays on this PC and is not sent to Gemini.')
    with st.expander('History controls'):
        st.write('Study backups include debugger attempts and evidence references. No personality or ability labels are stored.')
        confirm=st.checkbox('Delete only this learner’s debugger episodes',key='debugger_delete_'+learner)
        st.caption('Existing uploads, quizzes, cards and Newton records stay in their original workspaces. History-based support will be switched off; no derived profile is retained.')
        if st.button('Delete debugger history',disabled=not confirm):
            commit(db.delete_history(state,learner)); st.session_state.pop('debugger_active_'+learner,None)
            st.session_state['debugger_history_next_'+learner]=False; st.rerun()
    if st.session_state.get('debugger_tab')=='Repair ledger':st.session_state.debugger_tab='Previous support'
    tabs=st.radio('Support history',['Repair','Previous support'],horizontal=True,key='debugger_tab')
    episodes=[ep for ep in state['debugger']['episodes'] if ep['learner']==learner and (not upload_scope or ep['origin'] and ep['origin']['document_id']==st.session_state.study_material)]
    if tabs=='Previous support':
        for ep in reversed(episodes):
            v=db.view(ep)
            with st.container(border=True):
                st.markdown('**'+TOPICS.get(ep['topic'],{'title':'Uploaded material review'})['title']+'**')
                st.write(v['repair_status'].replace('_',' '))
                st.caption(local_date(ep['created_at'])+(' · review due '+local_date(v['due_at']) if v['due_at'] else ''))
                for role in ('immediate','transfer','delayed'):
                    r=v[role]
                    st.write(role.title()+': '+('not checked' if r is None else 'passed independently' if r['correct'] and not r['helped'] else 'needs another check / assisted'))
                if st.button('Open repair case',key='ledger_'+ep['id']):
                    st.session_state['debugger_active_'+learner]=ep['id']
                    st.session_state['debugger_next_tab']='Repair'; st.rerun()
        if not episodes: st.info('Start a repair to collect evidence.')
        evidence(state,learner)
        return

    if not upload_scope:
        topic=st.selectbox('Reviewed topic',list(TOPICS),format_func=lambda t:TOPICS[t]['title'],key='debugger_topic')
        def start():
            try:
                updated,sid=db.start(state,topic,learner)
                commit(updated); st.session_state['debugger_active_'+learner]=sid; st.rerun()
            except (DomainError,OSError) as exc: st.error(str(exc))
        if st.button('Start / resume repair',type='primary'): start()
    sid=st.session_state.get('debugger_active_'+learner)
    ep=next((ep for ep in episodes if ep['id']==sid),None)
    if ep is None:
        st.info('Choose a reviewed topic, or open a repair case from your ledger. Uploaded quiz feedback also links here for a source-guided review.')
        evidence(state,learner); return
    v=db.view(ep)
    st.subheader(TOPICS.get(ep['topic'],{'title':'Review your uploaded material'})['title'])
    st.caption('Previous support · '+v['repair_status'].replace('_',' '))
    def act(action,value=None):
        try:
            rev=len(ep['events'])
            commit(db.event(state,sid,action,value,token=f'{sid}:{rev}',revision=rev)); st.rerun()
        except (DomainError,OSError) as exc: st.error(str(exc))
    if ep['topic']=='upload':
        d=next(d for d in state['documents'] if d['id']==ep['origin']['document_id'])
        q=next(q for q in d['questions'] if q['id']==ep['origin']['question_id'])
        st.write(q['prompt']); st.info(q['explanation'])
        st.caption(('AI-generated material' if d['mode']=='gemini' else 'Local extractive recall')+' · source review, not reviewed diagnosis or fresh transfer')
        chunks=retrieve_repair_sources(state,d['id'],q['topic']+' '+q['prompt'])
        for c in chunks:
            st.markdown('**'+d['title']+' · '+c['chunk_id']+(' · page '+str(c['page']) if c['page'] else '')+'**')
            st.write(c['quote']); st.caption(c['relevance'])
        if not chunks: st.info('No relevant passage found by local keyword search. Inspect the source in Library or add fuller teaching notes.')
        st.write('Identify what the question asks, locate the supporting statement, and explain how it supports the answer. A matching quote does not establish semantic correctness.')
        if v['phase']=='source' and st.button('Record source review complete'): act('source_complete')
        if v['phase']=='source_done': st.success('Source review recorded. Independent understanding has not been assessed.')
        st.caption('This review uses only your selected material. Separate reviewed Newton activities are available through the Library.')
        evidence(state,learner,sid); return

    if v['decision']:
        with st.expander('Why this recommendation?'):
            st.write(v['decision']['reason_code'].replace('_',' '))
            st.caption('Policy '+v['decision']['policy_version']+' · content v'+str(v['decision']['content_version']))
            st.write('Evidence: '+(', '.join(v['decision']['evidence_ids']) or 'No earlier relevant evidence. Start with a neutral check.'))
    if v['repair'] and v['phase'] not in ('follow_up','transfer','delayed'):
        title,text=REPAIRS[v['repair']['hypothesis']]
        st.markdown('### '+title); st.write(text)
        st.caption('Selection: '+v['repair']['reason_code'].replace('_',' ')+'. This support choice is not a certain diagnosis.')
        with st.expander('Why this support?'):
            summary=build_learner_summary(state,learner,clock(),sid)
            for hid in TOPICS[ep['topic']]['hypotheses']:
                h=summary['hypotheses'][hid]
                st.write(h['label']+': '+h['status'].replace('_',' '))
            st.caption('Selection evidence: '+(', '.join(v['repair']['evidence_ids']) or 'Not enough diagnostic evidence; a guided or student-chosen explanation is offered.'))
        if v['phase']=='teach':
            experiment(ep['topic'],sid+':experiment:',state,commit,ep)
        with st.expander('Try another explanation / give feedback'):
            alternative=st.selectbox('Choose another support approach',['unclear']+TOPICS[ep['topic']]['hypotheses'],
                                     format_func=lambda h:REPAIRS[h][0],key=sid+'alt')
            if st.button('Use this explanation'): act('alternate',alternative)
            if st.button('That does not match my reasoning'): act('disagree')
            st.caption(f'{v["disagreements"]} disagreement(s) recorded. Objective grades stay unchanged.')
            a,b=st.columns(2)
            if a.button('This helped'): act('feedback','helped')
            if b.button('This did not help'): act('feedback','did not help')
        st.markdown('[Teaching reference: OpenStax University Physics]('+TOPICS[ep['topic']]['source']+')')

    if v['pending']:
        q=QUESTIONS[v['pending']]
        st.caption(q['role'].replace('_',' ').title()+(' · assisted learning' if q['role']=='teach' else ''))
        if q['role']=='primary' and any(r['question_id']==q['id'] for old in episodes if old['id']!=sid for r in db.view(old)['answers']):
            st.info('Previously seen starting item — practice, not new independent evidence.')
        if q['id'] in ('motion-transfer','motion-delayed-2'):
            speed=-4 if q['id']=='motion-transfer' else 9
            st.line_chart({'Time (s)':[0,1,2,3],'Velocity (m/s)':[speed]*4},x='Time (s)',y='Velocity (m/s)')
        if q['id']=='mass-transfer':
            st.line_chart({'Acceleration (m/s²)':[0,2,4,6,8],'Resultant force (N)':[0,8,16,24,32]},
                          x='Acceleration (m/s²)',y='Resultant force (N)')
        st.markdown('### '+q['prompt'])
        if v['helped']:
            st.info(q['explanation']); st.caption('Worked support revealed. This response cannot pass an independent check.')
        with st.form('debugger_answer_'+sid+':'+str(len(ep['events']))):
            option=st.radio('Your answer',range(len(q['options'])),format_func=lambda i:q['options'][i],index=None)
            confidence=st.selectbox('How sure are you? (optional)',['not given','sure','unsure','guessing'])
            if st.form_submit_button('Submit response',type='primary'): act('answer',dict(option=option,confidence=confidence))
        if not v['helped'] and st.button('I need the worked solution'): act('help')
        if q['role'] in ('primary','probe') and st.button('Skip diagnosis and get support'): act('repair')
    elif v['unavailable']:
        st.info('More independent evidence needed. No unused item is available for this check. Earlier answers have not been counted again.')
        if st.button('Review the explanation instead'): act('repair')
    elif v['phase']=='complete':
        r=v['feedback']
        if r:
            (st.success if r['correct'] and not r['helped'] else st.warning)('Independent check passed.' if r['correct'] and not r['helped'] else 'Repair needs another check; assisted work stays separate.')
            st.write(QUESTIONS[r['question_id']]['explanation'])
        if v['due_at']: st.write('Next delayed check: '+local_date(v['due_at']))
        if v['immediate'] and v['immediate']['correct'] and not v['immediate']['helped'] and v['transfer'] is None:
            if st.button('Try a changed representation'): act('review','transfer')
        if v['due_at'] and clock()>=datetime.fromisoformat(v['due_at']):
            if st.button('Start due delayed check'): act('review','delayed')
        else: st.caption('Future review is not yet available; previewing cannot complete it early.')
        if v['repair_status']=='reopened':
            if st.button('Try another fresh follow-up'): act('review','retry')
            if st.button('Revisit targeted support'): act('repair')
        if st.button('Return to Insights'):
            st.session_state.study_next_page='Insights'; st.rerun()
    else:
        if v['feedback']:
            r=v['feedback']
            if r['role'] in ('primary','probe'): st.info('Response recorded. We will use the evidence to choose useful support; the full explanation stays hidden until repair.')
            else:
                (st.success if r['correct'] else st.warning)('Teach-back recorded correctly.' if r['correct'] else 'Let’s revisit the explanation before an independent check.')
        label='Choose targeted support' if v['phase']=='repair' else 'Continue to next step'
        if st.button(label,type='primary'): act('next')
        if v['phase']=='probe' and st.button('Skip remaining probes and get support'): act('repair')
    evidence(state,learner,sid)
