from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from study import new_state
import nlm

ROOT=Path(__file__).resolve().parents[1]


class NLMAppTests(unittest.TestCase):
    def app(self,state=None):
        at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
        at.session_state['study']=state or new_state()
        at.session_state['study_use_ai']=False; at.session_state['study_persist']=False
        at.run(); self.assertFalse(at.exception)
        return at

    def click(self,at,label):
        next(b for b in at.button if b.label==label).click().run()
        self.assertFalse(at.exception,str(list(at.exception)))

    def test_existing_browser_session_v2_migrates_without_reset(self):
        old=new_state(); old.pop('nlm'); old.pop('debugger'); old.pop('practice_events',None); old={k:v for k,v in old.items() if k in {'schema_version','documents','quizzes','attempts','cards','reviews'}}; old['schema_version']=2
        at=self.app(old)
        self.assertEqual(at.session_state['study']['schema_version'],6)
        self.click(at,'Try sample material')
        self.assertTrue(at.session_state['study']['nlm']['installed'])

    def test_conceptual_route_hides_solution_then_fresh_question_and_reload(self):
        at=self.app(); self.click(at,'Try sample material')
        at.radio(key='study_nav').set_value('Quiz').run()
        self.click(at,'Start / resume this question')
        q=nlm.question('inertia-1'); wrong=q['options'].index('It slows without a force')
        next(r for r in at.radio if r.label=='Your prediction / answer').set_value(wrong)
        self.click(at,'Check response')
        self.assertTrue(any('gap' in w.value for w in at.warning))
        self.assertFalse(any('Structured solution' in s.value for s in at.subheader))
        self.assertFalse(any('Answer: '+q['options'][q['correct_index']] in m.value for m in at.markdown))
        self.assertTrue(any('continuous forward force' in c.value for c in at.caption))
        saved=at.session_state['study']
        reopened=self.app(saved)
        reopened.radio(key='study_nav').set_value('Quiz').run()
        reopened.radio(key='study_nav').set_value('Quiz').run()
        self.assertTrue(any('gap' in w.value for w in reopened.warning))
        self.click(reopened,'Show solution')
        self.assertTrue(any('Structured solution' in s.value for s in reopened.subheader))
        self.click(reopened,'Try a fresh related question')
        self.assertFalse(any('Structured solution' in s.value for s in reopened.subheader))
        session=reopened.session_state['study']['nlm']['sessions'][0]
        v=nlm.view(session); self.assertEqual(v['question_id'],'inertia-4')
        follow=nlm.question(v['question_id'])
        next(r for r in reopened.radio if r.label=='Your prediction / answer').set_value(follow['correct_index'])
        self.click(reopened,'Check response')
        self.assertTrue(any('not a mastery claim' in x.value for x in reopened.success))

    def test_calculation_route_correct_route_flashcard_and_visual_gating(self):
        at=self.app(); self.click(at,'Try sample material')
        at.selectbox(key='nlm_learner').set_value('Demo Learner B').run()
        at.radio(key='study_nav').set_value('Quiz').run(); self.click(at,'Start / resume this question')
        q=nlm.question('second-1')
        next(r for r in at.radio if r.label=='Your prediction / answer').set_value(q['options'].index('12 m/s²'))
        self.click(at,'Check response')
        self.assertTrue(any('Calculation scaffold' in i.value for i in at.info))
        next(r for r in at.radio if r.label=='Your prediction / answer').set_value(q['correct_index'])
        self.click(at,'Check response'); self.click(at,'Try a fresh reasoning check')
        session=at.session_state['study']['nlm']['sessions'][0]
        v=nlm.view(session); self.assertEqual(v['question_id'],'second-4')
        at.radio(key='study_nav').set_value('Flash Cards').run()
        self.assertFalse(at.session_state['study']['nlm']['reviews'])
        self.click(at,'Reveal recall card'); self.click(at,'Reveal recall card')
        self.assertFalse(at.session_state['study']['nlm']['reviews'])
        self.click(at,'Good'); self.assertEqual(len(at.session_state['study']['nlm']['reviews']),1)
        self.click(at,'Open linked visual lesson')
        self.assertEqual(at.session_state['nlm_tab'],'Learn visually')
        self.assertTrue(next(b for b in at.button if b.label=='Reveal experiment').disabled)
        next(t for t in at.text_input if t.label.startswith('Predict first')).set_value('No net horizontal force means no acceleration').run()
        next(r for r in at.radio if r.label=='Choose a prediction').set_value('Zero resistance preserves velocity; resistance changes it').run()
        self.click(at,'Reveal experiment')
        self.assertTrue(any('Initial velocity' in c.value for c in at.caption))


if __name__=='__main__': unittest.main()
