"""Warm, restrained student and teacher views for the no-account physics showcase."""
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from engine import DomainError
from physics_practice import start_round, current_question, respond, advance, first_responses, MAX_QUESTIONS, upgrade_round
from showcase import DATA_DIR, PAGES, load_showcase, student_report, confusion_report, record_response, teaching_report

from physics_teaching import guided_approach, worked_explanation, recall_cards
from physics_cards import flashcard_html

ROOT=Path(__file__).resolve().parents[2]
st.set_page_config(page_title='Phoenix · Learning workspace',page_icon=str(ROOT/'assets/phoenix-logo.jpeg'),layout='wide')
st.markdown('''<style>
:root{--ink:#34382f;--muted:#77796c;--line:#e0dbcd;--paper:#fbf9f3;--olive:#596747}
[data-testid=stAppViewContainer]{background-color:#f3efe5;background-image:radial-gradient(#afa58d19 .65px,transparent .65px);background-size:7px 7px}
.block-container{max-width:1240px;padding-top:1.4rem;padding-bottom:3rem}
[data-testid=stSidebar]{background:#eae7dc;border-right:1px solid var(--line)}
[data-testid=stSidebar] .block-container{padding-top:1.5rem}
h1,h2,h3{color:var(--ink);letter-spacing:-.035em}h1{font-family:Georgia,'Times New Roman',serif!important;font-size:2.55rem!important;font-weight:500!important}
h2{font-size:1.45rem!important}h3{font-size:1.12rem!important;font-weight:600!important}
p,label,button,li{line-height:1.65}button{border-radius:9px!important}
[data-testid=stMetric]{background:var(--paper);border:1px solid var(--line);padding:19px;border-radius:12px;min-height:110px}
[data-testid=stMetricValue]{font-family:Georgia,serif;font-size:2rem!important;color:var(--ink)}
[data-testid=stMetricLabel] p{color:var(--muted)!important;white-space:normal}
[data-testid=stVerticalBlockBorderWrapper]>div{border-color:var(--line)!important;border-radius:12px!important}
[data-testid=stForm]{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:22px}
.wordmark{font-family:Georgia,serif;font-size:2.1rem!important;line-height:1.1!important;color:var(--ink);letter-spacing:-.065em;margin:0}
.kicker{font-size:.69rem;letter-spacing:.15em;text-transform:uppercase;color:var(--olive);font-weight:700;margin:0 0 10px}
.muted{color:var(--muted);font-size:.9rem}.profile{display:flex;justify-content:flex-end}
.chapter{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:22px;min-height:185px;margin:5px 0 10px}
.chapter h3{font-family:Georgia,serif;font-size:1.35rem!important;margin:9px 0}
.heat-tile{padding:17px;border-radius:10px;min-height:130px;margin:5px 0 12px;border:1px solid #00000008}
.heat-tile strong{font-size:.88rem}.heat-tile .score{font:1.8rem Georgia,serif;margin:8px 0 3px}.heat-tile small{font-size:.74rem}
.question{font:1.45rem/1.55 Georgia,serif;color:var(--ink);padding:18px 0}.formula{font-family:Georgia,serif;font-size:1.2rem;background:#e9eadc;padding:14px 18px;border-radius:9px}
.activity-grid{display:grid;grid-template-columns:repeat(21,minmax(0,1fr));gap:5px;margin:15px 0}.activity-grid span{aspect-ratio:1;border-radius:4px}
@media(max-width:640px){.block-container{padding:1rem!important}h1{font-size:2rem!important}.chapter{min-height:0}.question{font-size:1.2rem}.activity-grid{gap:3px}[data-testid=stRadio] label,button{min-height:44px}}
</style>''',unsafe_allow_html=True)

if 'physics_data' not in st.session_state:st.session_state.physics_data=load_showcase()
if st.session_state.physics_data.get('version')!=2:
    latest=load_showcase()
    st.session_state.physics_data.update(version=2,bank=latest['bank'],chapters=latest['chapters'])
data=st.session_state.physics_data
student_id='user-1'
report=student_report(data,student_id)
chapters={c['id']:c for c in data['chapters']}


def go(page,concept=None):
    st.session_state.physics_nav=page
    if concept:st.session_state.physics_concept=concept


def start_upload_workspace():
    from study import new_state
    st.session_state.workspace_view='Uploads'
    st.session_state.study=new_state()
    st.session_state.study_persist=False
    st.session_state.study_use_ai=False
    st.session_state.demo_workspace=False
    st.session_state.study_nav='Library'
    st.query_params.clear()


with st.sidebar:
    st.markdown('<p class="wordmark">Phoenix<span style="color:#78835b">.</span></p>',unsafe_allow_html=True)
    st.caption('A clearer way to learn')
    st.divider()
    st.radio('WORKSPACE',PAGES,key='physics_nav',label_visibility='visible')
    st.divider()
    st.markdown('**JEE Main preparation**')
    st.caption('Class 12 · Physics\n\n8 chapters in your library')
    if st.session_state.physics_nav == 'Teacher Dashboard':
        class_reports=[student_report(data,s['id']) for s in data['students']]
        class_accuracy=sum(r['correct'] for r in class_reports)/sum(r['attempted'] for r in class_reports)
        st.progress(class_accuracy,text=f'{class_accuracy:.0%} class accuracy')
    else:
        st.progress(report['accuracy'],text=f"{report['accuracy']:.0%} practice accuracy")
    with st.expander('Workspace'):
        st.button('Study your own material',on_click=start_upload_workspace,width='stretch')
        st.download_button('Export learning history',json.dumps(data,ensure_ascii=False,indent=2),'phoenix-learning-history.json','application/json')
        if st.button('Restart workspace'):
            for key in list(st.session_state):
                if key.startswith('physics_'):del st.session_state[key]
            st.rerun()

is_teacher = st.session_state.physics_nav == 'Teacher Dashboard'
top,profile=st.columns([3,1.4])
with top:st.markdown('<p class="kicker">'+('TEACHING' if is_teacher else 'LEARNING')+' WORKSPACE / JEE PHYSICS</p>',unsafe_allow_html=True)
with profile:
    with st.popover('KR · Kavya Rao' if is_teacher else 'U1 · User 1',width='stretch'):
        if is_teacher:
            st.markdown('### Kavya Rao')
            st.write('Physics faculty · JEE Main')
            st.caption('JEE Physics · Batch A · 6 students')
        else:
            st.markdown('### User 1')
            st.write('Class 12 · JEE Main')
            st.caption('JEE Physics · Batch A\n\nTarget attempt: January 2027')
            st.write(f"{report['attempted']} questions practised · {len(report['days'])} active days")


def heading(title,subtitle):
    st.title(title);st.caption(subtitle)


def heatmap(topics,columns=4):
    cols=st.columns(columns)
    for i,t in enumerate(topics):
        pct=t['accuracy'] or 0
        bg='#ead6c5' if pct<.55 else '#e8dfbb' if pct<.75 else '#dce4cf'
        label='Needs attention' if pct<.55 else 'Keep practising' if pct<.75 else 'On track'
        with cols[i%columns]:
            st.markdown(f'<div class="heat-tile" style="background:{bg}"><strong>{escape(t["title"])}</strong><div class="score">{pct:.0%}</div><small>{label} · {t["correct"]}/{t["attempted"]} correct</small></div>',unsafe_allow_html=True)


def dashboard():
    heading('Your learning overview','Welcome back, User 1. Pick up where you left off.')
    a,b,c,d=st.columns(4)
    a.metric('Practice accuracy',f"{report['accuracy']:.0%}")
    b.metric('Questions practised',report['attempted'])
    c.metric('Study time',f"{report['minutes']//60}h {report['minutes']%60}m")
    d.metric('Active study days',len(report['days']))
    st.write('')
    left,right=st.columns([1.55,1])
    with left:
        with st.container(border=True):
            weak=report['weak'][0]
            st.markdown('<p class="kicker">YOUR NEXT STEP</p>',unsafe_allow_html=True)
            st.subheader('A fresh look at '+weak['title'].lower())
            st.write(weak['concept']+' is worth another focused round. Start with five questions; get targeted support where you need it.')
            st.button('Start focused practice →',type='primary',on_click=go,args=('Quiz',weak['id']),width='stretch')
    with right:
        with st.container(border=True):
            st.markdown('<p class="kicker">REVISION DESK</p>',unsafe_allow_html=True)
            st.subheader('Keep the essentials close')
            st.write('Review key relations and explain them from memory before revealing the answer.')
            st.button('Open flash cards →',on_click=go,args=('Flash Cards',),width='stretch')
    st.subheader('Your concept map')
    heatmap(report['topics'])
    st.caption('First-attempt accuracy by chapter · rust: below 55% · sand: 55–74% · sage: 75% and above')
    a,b=st.columns([1.3,1])
    with a:
        st.subheader('Practice over time')
        st.line_chart(pd.DataFrame(report['trend']),x='date',y='accuracy',color='#78835b',height=200,x_label='Study date',y_label='Accuracy (%)')
    with b:
        st.subheader('Recent activity')
        for row in sorted(report['person']['history'],key=lambda r:r['at'],reverse=True)[:4]:
            st.markdown('**'+chapters[row['concept']]['title']+'**')
            st.caption(datetime.fromisoformat(row['at']).astimezone(ZoneInfo('Asia/Kolkata')).strftime('%d %b · %H:%M')+' · '+('Correct answer' if row['correct'] else 'Concept to revisit'))


def library():
    heading('Your physics library','Chapters, notes and practice — organised around your JEE preparation.')
    search=st.text_input('Find a chapter',placeholder='Search kinematics, optics, electricity…')
    for offset in range(0,len(data['chapters']),2):
        cols=st.columns(2)
        for col,chapter in zip(cols,data['chapters'][offset:offset+2]):
            if search and search.casefold() not in (chapter['title']+' '+chapter['unit']).casefold():continue
            with col:
                st.markdown(f'<div class="chapter"><div class="kicker">{escape(chapter["unit"])}</div><h3>{escape(chapter["title"])}</h3><p class="muted">{escape(chapter["concept"])}<br>Notes · 11 practice questions · 3 recall cards</p></div>',unsafe_allow_html=True)
                with st.expander('Read '+chapter['title']+' notes'):
                    st.markdown((DATA_DIR/chapter['filename']).read_text(encoding='utf-8'))
                st.button('Practise '+chapter['title'],key='chapter_'+chapter['id'],on_click=go,args=('Quiz',chapter['id']),width='stretch')
    st.divider()
    st.subheader('Bring your own course material')
    st.caption('Upload a text-based PDF, TXT or Markdown file, or paste your notes to build a source-grounded study pack.')
    st.button('Add your material →',on_click=start_upload_workspace,type='primary')


def quiz():
    heading('Focused practice','Five core questions. Extra concept checks when needed. Fifteen questions at most.')
    active=st.session_state.get('physics_round')
    if active is not None:
        active=upgrade_round(active)
        st.session_state.physics_round=active
    if active is None:
        focus=st.selectbox('Start with a concept',list(chapters),format_func=lambda cid:chapters[cid]['title'],
                           index=list(chapters).index(st.session_state.get('physics_concept','forces')))
        st.markdown(f'<div class="formula">{escape(chapters[focus]["formula"])}</div>',unsafe_allow_html=True)
        st.write('Three attempts: answer → hint → retry → concept and approach → final try → full solution. A fresh question checks the same concept before you move on.')
        if st.button('Start 5-question round',type='primary'):
            ordered=[focus]+[t['id'] for t in report['weak'] if t['id']!=focus]
            st.session_state.physics_round=start_round(data['bank'],ordered[:5]);st.rerun()
        return
    if active['stage']=='complete':
        first=first_responses(active)
        st.success('Round complete')
        a,b,c=st.columns(3);a.metric('Questions completed',len(first));b.metric('Correct first time',sum(r['correct'] for r in first));c.metric('Extra concept checks',len(active['queue'])-5)
        if active['limit_reached']:st.info('You reached the fifteen-question limit. Review the concepts below and return for another round when ready.')
        unresolved={r['concept'] for r in first if not r['correct']}
        for cid in unresolved:
            rows=[r for r in first if r['concept']==cid]
            st.write('**'+chapters[cid]['title']+'** · '+('Fresh check answered correctly' if rows[-1]['correct'] else 'Schedule another focused review'))
        st.caption('Supported retries are recorded separately from first answers. A successful check is evidence for this question, not a guarantee of mastery.')
        if st.button('Start another round',type='primary'):
            st.session_state.pop('physics_round');st.rerun()
        st.button('View learning insights →',on_click=go,args=('Insights',))
        return
    question=current_question(active,data['bank'])
    st.caption(f"Question {active['position']+1} of {len(active['queue'])} · Maximum 15 · {chapters[question['concept']]['title']}")
    st.progress(active['position']/len(active['queue']))
    if active['position'] and question['concept']==next(q['concept'] for q in data['bank'] if q['id']==active['queue'][active['position']-1]):
        st.caption('CONCEPT CHECK · Same principle, a new set of values')
    st.markdown('<div class="question">'+escape(question['prompt'])+'</div>',unsafe_allow_html=True)
    if active['stage']=='hint':
        st.info(question['hint'])
        st.caption('Attempt 2 of 3 · Use the hint to reconsider your answer.')
    if active['stage']=='approach':
        st.markdown('### Understand the concept and approach')
        idea,steps,check=guided_approach(question)
        st.info(idea)
        for number,step in enumerate(steps,1):st.write(f'{number}. {step}')
        st.caption('Before you calculate: '+check)
        st.caption('One final attempt. Apply these steps to the values in this question.')
    if active['stage'] in ('answer','hint','approach'):
        if active['stage']=='answer':st.caption('Attempt 1 of 3')
        with st.form('physics_answer_'+active['id']+str(active['position'])+active['stage']):
            answer=st.radio('Your answer',range(4),format_func=lambda i:question['options'][i],index=None)
            submitted=st.form_submit_button('Check final attempt' if active['stage']=='approach' else 'Check retry' if active['stage']=='hint' else 'Check answer',type='primary')
        if submitted:
            try:
                result=respond(active,data['bank'],answer)
                st.session_state.physics_data=record_response(data,student_id,active['id'],result['responses'][-1])
                st.session_state.physics_round=result;st.rerun()
            except DomainError as exc:st.warning(str(exc))
    else:
        if active['stage']=='feedback':st.success('Correct. Well reasoned.' if active['responses'][-1]['phase']=='first' else 'Correct with support. Now check the concept on a fresh question.')
        else:st.info('Let’s work through the principle before the next concept check.')
        st.markdown('**Worked solution**')
        explanation=worked_explanation(question,active['responses'][-1]['selected_index'])
        st.write('**1. Identify the principle.** '+explanation['principle'])
        st.write('**2. Set up the approach.**')
        for step in explanation['steps']:st.write('• '+step)
        st.write('**3. Substitute and calculate.** '+explanation['calculation'])
        st.success('**Answer:** '+explanation['answer'])
        st.write('**4. Check the reasoning.** '+explanation['check'])
        if active['stage']=='solution':st.write('**What to correct:** '+explanation['correction'])
        missed=any(r['question_id']==question['id'] and r['phase']=='first' and not r['correct'] for r in active['responses'])
        if missed and len(active['queue'])<MAX_QUESTIONS:st.caption('Next: a fresh question on this same concept.')
        if st.button('Continue →',type='primary'):
            st.session_state.physics_round=advance(active,data['bank']);st.rerun()


def cards():
    heading('Your revision desk','One idea at a time. Recall it, flip it, make it stick.')
    deck=recall_cards(data['chapters'])
    ratings=st.session_state.setdefault('physics_cards',{})
    def reset_card_index():st.session_state.physics_card_index=0
    scope=st.selectbox('Chapter',['all',*chapters],format_func=lambda x:'All chapters' if x=='all' else chapters[x]['title'],key='physics_card_filter',on_change=reset_card_index)
    filtered=[card for card in deck if scope=='all' or card['concept']==scope]
    index=st.session_state.get('physics_card_index',0)%len(filtered)
    card=filtered[index]
    st.caption(f"Card {index+1} of {len(filtered)} · {card['title']} · {card['kind'].title()}")
    st.progress((index+1)/len(filtered))
    st.iframe(flashcard_html(card),height='content',tab_index=0,alt=card['title']+' interactive recall card')
    prev,middle,nxt=st.columns([1,2,1])
    if prev.button('← Previous',width='stretch'):
        st.session_state.physics_card_index=(index-1)%len(filtered);st.rerun()
    with middle:st.caption('Click the card or focus it and press Enter / Space to flip.')
    if nxt.button('Next →',width='stretch'):
        st.session_state.physics_card_index=(index+1)%len(filtered);st.rerun()
    st.markdown('**How well did you recall it?**')
    for col,label in zip(st.columns(3),['Review again','Getting there','Recalled well']):
        if col.button(label,key='recall_'+label,width='stretch'):
            ratings[card['id']]=dict(rating=label,at=datetime.now().isoformat())
            st.session_state.physics_card_notice=label+' · recall rating saved.'
            st.rerun()
    if st.session_state.get('physics_card_notice'):st.success(st.session_state.pop('physics_card_notice'))
    st.caption(f'{sum(c["id"] in ratings for c in deck)} of {len(deck)} cards reviewed · recall ratings are self-reported')
    if card['id'] in ratings:st.caption('Your last rating on this card: '+ratings[card['id']]['rating'])



def insights():
    heading('Your learning insights','See the patterns in your practice, then decide what deserves attention next.')
    a,b=st.columns([1,2])
    period=a.selectbox('Time period',['All history','Last 7 days','Last 14 days'])
    selected=b.multiselect('Chapters',list(chapters),format_func=lambda x:chapters[x]['title'])
    scoped=json.loads(json.dumps(data))
    if period!='All history':
        from datetime import timedelta, timezone
        cutoff=(datetime.now(timezone.utc)-timedelta(days=7 if period=='Last 7 days' else 14)).isoformat()
        next(s for s in scoped['students'] if s['id']==student_id)['history']=[r for r in report['person']['history'] if r['at']>=cutoff]
    if selected:
        person=next(s for s in scoped['students'] if s['id']==student_id)
        person['history']=[r for r in person['history'] if r['concept'] in selected]
    summary=student_report(scoped,student_id)
    a,b,c=st.columns(3);a.metric('First-attempt accuracy',f"{summary['accuracy']:.0%}");b.metric('Questions attempted',summary['attempted']);c.metric('Answers with support',sum(r.get('hint_used',False) for r in summary['person']['history']))
    st.subheader('Chapter performance')
    heatmap([t for t in summary['topics'] if not selected or t['id'] in selected])
    st.caption('Rust: below 55% · sand: 55–74% · sage: 75% and above. Colours describe practice accuracy, not mastery.')
    st.subheader('Study consistency')
    days=sorted(report['days'])[-21:]
    st.markdown('<div class="activity-grid">'+''.join(f'<span title="{day}: {report["days"][day]} answers" style="background:{"#758362" if report["days"][day]>=8 else "#b8c1a6"}"></span>' for day in days)+'</div>',unsafe_allow_html=True)
    st.caption(f'{len(days)} active days shown · darker squares indicate 8 or more answers')
    left,right=st.columns([1.2,1])
    with left:
        st.subheader('Accuracy trend')
        if summary['trend']:st.line_chart(pd.DataFrame(summary['trend']),x='date',y='accuracy',color='#78835b',height=230)
    with right:
        st.subheader('Concepts to revisit')
        for topic in summary['weak'][:3]:
            st.markdown('**'+topic['title']+'**')
            st.caption(topic['concept']+f" · {topic['errors']} incorrect first answers")
            st.button('Practise '+topic['title'],key='weak_'+topic['id'],on_click=go,args=('Quiz',topic['id']))
    st.subheader('Practice history')
    rows=[dict(Date=datetime.fromisoformat(r['at']).astimezone(ZoneInfo('Asia/Kolkata')).strftime('%d %b %Y · %H:%M'),Chapter=chapters[r['concept']]['title'],Result='Correct' if r['correct'] else 'Needs review',Support='Hint used' if r.get('hint_used') else 'Independent',Question=r['question_id']) for r in sorted(summary['person']['history'],key=lambda r:r['at'],reverse=True)]
    st.dataframe(rows,hide_index=True,width='stretch')


def teaching_plan(analysis,scope_label):
    st.subheader('Priority teaching plan')
    st.caption('Priorities combine first-answer error rate (60%), share of students affected (25%), and error rate on each student’s latest five answers (15%). These are teaching heuristics, not diagnoses.')
    if not analysis['priorities']:
        st.info('No recorded errors in this scope. Use fresh practice to identify the next teaching need.')
        return
    st.dataframe([dict(Priority=p['rank'],Topic=p['title'],Accuracy=f"{p['accuracy']:.0%}",Students=len(p['affected']),Errors=p['errors'],Recent_errors=f"{p['recent_error']:.0%}") for p in analysis['priorities']],hide_index=True,width='stretch')
    for item in analysis['priorities']:
        with st.expander(f"{item['rank']:02d} · {item['title']} — {len(item['affected'])} student(s) to support"):
            st.write('**Why this comes next:** '+f"{item['errors']} errors in {item['attempted']} first answers; {item['recent_error']:.0%} incorrect on recent practice.")
            st.write('**Counter this confusion:** '+item['counter'])
            for pattern in item['patterns'][:3]:st.write('• '+pattern['pattern']+f" ({pattern['count']} responses)")
            st.write('**Students to check in with:** '+', '.join(s['name'] for s in item['affected']))
            st.markdown('**Suggested 20-minute teaching sequence**')
            for minutes,label,step in zip([3,7,5],['Elicit the reasoning','Rebuild the concept','Contrast and apply'],item['steps']):
                st.write(f'**{minutes} min · {label}:** '+step)
            st.write('**3 min · '+('Fresh exit check' if item['exit_is_fresh'] else 'Review exit check')+':** '+item['exit_question'])
            if not item['exit_is_fresh']:st.caption('All authored items for this topic have recorded exposure. Use a new teacher-authored example to check fresh transfer.')
            with st.expander('Teacher answer key'):st.write(item['exit_answer'])
            st.write('**2 min · Next step:** Ask for an explanation, not only a numerical answer. Recheck the same principle with new values in the next session; retain support if it remains unclear.')
    st.download_button('Download '+scope_label+' teaching plan',json.dumps(dict(scope=scope_label,priorities=analysis['priorities']),ensure_ascii=False,indent=2),scope_label+'-teaching-plan.json','application/json',key='plan_'+scope_label)


def class_analysis(analysis):
    st.subheader('Class concept heatmap')
    heatmap(analysis['topics'])
    st.caption('Combined first-answer accuracy across the class. Rust: below 55% · sand: 55–74% · sage: 75% and above.')
    with st.expander('Student × topic heatmap'):
        matrix=pd.DataFrame({r['person']['name']:{topic['title']:round(100*topic['accuracy']) if topic['accuracy'] is not None else None for topic in r['topics']} for r in analysis['reports']}).T
        def shade(value):
            if pd.isna(value):return 'background-color:#eeeade'
            return 'background-color:'+('#ead6c5' if value<55 else '#e8dfbb' if value<75 else '#dce4cf')+';color:#30372d'
        st.dataframe(matrix.style.map(shade).format('{:.0f}%',na_rep='No attempts'),width='stretch')
    st.subheader('Where the class is getting stuck')
    patterns=[]
    for topic in analysis['topics']:
        for pattern in topic['patterns']:patterns.append(dict(Chapter=topic['title'],Potential_confusion=pattern['pattern'],Responses=pattern['count'],Students_with_chapter_errors=len(topic['affected'])))
    patterns.sort(key=lambda row:-row['Responses'])
    st.dataframe(patterns,hide_index=True,width='stretch')
    st.caption('Patterns reflect selected distractors and should be checked by asking students to explain their reasoning.')
    a,b,c=st.columns(3)
    a.metric('Hint-supported questions',analysis['hint_support'])
    b.metric('Needed concept guidance',analysis['approach_support'])
    c.metric('Needed full solution',analysis['solution_support'])
    teaching_plan(analysis,'class')


def teacher():
    detail=st.session_state.get('physics_teacher_open',False)
    heading('Student learning report' if detail else 'Teacher dashboard','JEE Physics · Batch A — follow each learner’s progress and areas of confusion.')
    analysis=teaching_report(data)
    reports=analysis['reports']
    if not detail:
        a,b,c,d=st.columns(4);a.metric('Students',len(reports));b.metric('Class accuracy',f"{sum(r['correct'] for r in reports)/sum(r['attempted'] for r in reports):.0%}");c.metric('Questions attempted',sum(r['attempted'] for r in reports));d.metric('Chapters covered',len(chapters))
    if not st.session_state.get('physics_teacher_open'):
        class_analysis(analysis)
        st.divider()
        st.subheader('Student overview')
        for offset in range(0,len(reports),3):
            for col,r in zip(st.columns(3),reports[offset:offset+3]):
                with col,st.container(border=True):
                    st.markdown('**'+r['person']['initials']+' · '+r['person']['name']+'**')
                    st.caption(r['person']['grade']+' · '+r['person']['goal'])
                    st.progress(r['accuracy'],text=f"{r['accuracy']:.0%} first-attempt accuracy")
                    st.caption('Focus: '+r['weak'][0]['title'])
                    if st.button('Open student report',key='student_'+r['person']['id'],width='stretch'):
                        st.session_state.physics_teacher_student=r['person']['id'];st.session_state.physics_teacher_open=True;st.rerun()
        st.caption('Open a student report to inspect chapter performance, errors and confusion patterns.')
        return
    if st.button('← Back to student overview'):
        st.session_state.physics_teacher_open=False;st.rerun()
    ids=[s['id'] for s in data['students']]
    sid=st.selectbox('Student report',ids,format_func=lambda x:next(s['name'] for s in data['students'] if s['id']==x),key='physics_teacher_student')
    r=student_report(data,sid)
    st.subheader(r['person']['name']+' · Learning report')
    a,b,c=st.columns(3);a.metric('Correct / attempted',f"{r['correct']} / {r['attempted']}");b.metric('First-answer errors',r['attempted']-r['correct']);c.metric('Hint-supported answers',sum(x.get('hint_used',False) for x in r['person']['history']))
    heatmap(r['topics'])
    teaching_plan(teaching_report(data,[sid]),sid)
    st.subheader('Misconceptions & confusion patterns')
    st.caption('Potential explanations to investigate in conversation with the student. An answer pattern alone is not a diagnosis.')
    patterns=confusion_report(data,sid)
    for topic in r['weak']:
        related=[pattern for pattern in patterns if pattern['concept']==topic['id']]
        if not related:continue
        chapter=chapters[topic['id']]
        with st.expander(chapter['title']+' · '+str(sum(p['count'] for p in related))+' related errors',expanded=False):
            for pattern in related:
                st.markdown('**'+pattern['pattern']+'** · '+str(pattern['count'])+' responses')
            st.write('**Teaching prompt:** Ask the student to identify the quantities and explain why this relation applies before substituting values.')
            st.write('**Principle to revisit:** '+chapter['notes'])
            st.caption('Suggested follow-up: a fresh numerical example, then a check in a later session.')
    st.subheader('Recent errors')
    bank={q['id']:q for q in data['bank']}
    errors=sorted([x for x in r['person']['history'] if not x['correct']],key=lambda x:x['at'],reverse=True)
    st.dataframe([dict(Date=x['at'][:10],Chapter=chapters[x['concept']]['title'],Question=bank[x['question_id']]['prompt'],Chosen=bank[x['question_id']]['options'][x['selected_index']],Expected=bank[x['question_id']]['options'][bank[x['question_id']]['correct_index']],Support='Hint + retry' if x.get('hint_used') else 'Review needed') for x in errors],hide_index=True,width='stretch')
    st.download_button('Download student report',json.dumps(dict(profile=r['person'],topics=r['topics'],confusion_patterns=patterns),ensure_ascii=False,indent=2),sid+'-learning-report.json','application/json')


{'Dashboard':dashboard,'Library':library,'Quiz':quiz,'Flash Cards':cards,'Insights':insights,'Teacher Dashboard':teacher}[st.session_state.physics_nav]()
st.divider();st.caption('Phoenix · Your learning, connected.')
