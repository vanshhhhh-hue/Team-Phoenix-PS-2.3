from copy import deepcopy
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from study import new_state,add_document
import debugger as db
from debugger_content import QUESTIONS

ROOT=Path(__file__).resolve().parents[1]


class DebuggerAppTests(unittest.TestCase):
    def app(self,state=None,page='Debugger'):
        at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
        at.session_state['study']=state or new_state()
        at.session_state['study_use_ai']=False;at.session_state['study_persist']=False
        at.session_state['study_nav']=page
        at.run();self.assertFalse(at.exception,str(list(at.exception)))
        return at

    def click(self,at,label):
        next(b for b in at.button if b.label==label).click().run()
        self.assertFalse(at.exception,str(list(at.exception)))

    def answer(self,at,option=None):
        ep=at.session_state['study']['debugger']['episodes'][-1]
        q=QUESTIONS[db.view(ep)['pending']]
        next(r for r in at.radio if r.label=='Your answer').set_value(q['correct'] if option is None else option)
        self.click(at,'Submit response')

    def test_complete_mass_journey_hidden_keys_experiment_transfer_and_reload(self):
        at=self.app();at.selectbox(key='debugger_topic').set_value('mass').run()
        self.click(at,'Start / resume repair');self.answer(at,0)
        self.assertFalse(any('a = F_net/m = 6/2' in x.value for x in at.markdown))
        for _ in range(2):
            self.click(at,'Continue to next step');self.answer(at,0)
        self.click(at,'Choose targeted support')
        self.assertTrue(any('Compare two masses' in x.value for x in at.markdown))
        pred=next(r for r in at.radio if r.label=='Your prediction')
        self.assertIsNone(pred.value);self.assertFalse(at.metric)
        pred.set_value(pred.options[0]).run();self.click(at,'Run comparison')
        self.assertEqual(len(at.metric),2)
        next(s for s in at.slider if s.label=='Mass of trolley A (kg)').set_value(3).run()
        self.assertFalse(at.metric)
        self.assertIsNone(next(r for r in at.radio if r.label=='Your prediction').value)
        self.click(at,'Continue to next step');self.answer(at)
        self.click(at,'Continue to next step')
        self.assertFalse(any('Compare two masses' in x.value for x in at.markdown))
        self.answer(at)
        self.assertTrue(any('Independent check passed' in x.value for x in at.success))
        self.click(at,'Try a changed representation');self.click(at,'Continue to next step');self.answer(at)
        ep=at.session_state['study']['debugger']['episodes'][-1]
        self.assertEqual(db.view(ep)['repair_status'],'transfer_check_passed')
        saved=deepcopy(at.session_state['study'])
        at=self.app(saved);at.radio(key='debugger_tab').set_value('Previous support').run()
        self.click(at,'Open repair case')
        self.assertTrue(any('Independent check passed' in x.value for x in at.success))
        self.assertEqual(at.session_state['study'],saved)

    def test_toggle_and_delete_scoped_history(self):
        at=self.app();self.click(at,'Start / resume repair')
        next(t for t in at.toggle if t.label=='Use earlier attempts to personalise support').set_value(False).run()
        self.assertFalse(at.session_state['study']['debugger']['history']['My learning'])
        next(c for c in at.checkbox if c.label=='Delete only this learner’s debugger episodes').check().run()
        self.click(at,'Delete debugger history')
        self.assertEqual(at.session_state['study']['debugger']['episodes'],[])
        self.assertFalse(at.exception)

    def test_upload_feedback_opens_labelled_source_review(self):
        s,did,_=add_document(new_state(),'My notes','notes.md',(ROOT/'samples/users/user-1/demo-notes.md').read_bytes(),use_ai=False)
        from study import start_quiz,answer_question,get_question
        s,qid=start_quiz(s,did,count=1)
        question=get_question(s,s['quizzes'][0]['question_ids'][0])
        s=answer_question(s,qid,question['id'],(question['correct_index']+1)%4,0,'wrong')
        at=self.app(s,'Quiz')
        at.selectbox(key='study_material').set_value(did).run()
        at.session_state['study_feedback']=(qid,question['id']);at.session_state['study_quiz_id']=qid;at.run()
        self.click(at,'Show worked explanation')
        self.click(at,'Review this difficulty in Debugger')
        self.assertEqual(at.session_state['study_nav'],'Quiz')
        self.assertTrue(any('source review, not reviewed diagnosis' in x.value for x in at.caption))
        self.click(at,'Record source review complete')
        self.assertTrue(any('Independent understanding has not been assessed' in x.value for x in at.success))


if __name__=='__main__':unittest.main()
