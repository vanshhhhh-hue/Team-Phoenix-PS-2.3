"""No-account showcase isolation, navigation and teacher reporting."""
from pathlib import Path
import os
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from demo import load_demo
from showcase import load_showcase, student_report, confusion_report
import study

ROOT=Path(__file__).resolve().parents[1]

class DemoTests(unittest.TestCase):
    def test_legacy_fixture_remains_valid_and_private_state_is_not_a_source(self):
        state=load_demo();study.validate_state(state)
        state['documents'].clear()
        self.assertTrue(load_demo()['documents'])
        data=load_showcase()
        self.assertEqual(len(data['students']),6)
        self.assertEqual(len(data['chapters']),8)
        self.assertTrue(all((ROOT/'samples/users/user-1/physics'/c['filename']).is_file() for c in data['chapters']))
        self.assertTrue(confusion_report(data,'user-1'))

    def test_showcase_navigation_isolation_and_student_report_actions(self):
        with patch.dict(os.environ,{'PHOENIX_MODE':'demo'}),patch('storage.read_workspace',side_effect=AssertionError('Private checkpoint accessed')):
            first=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
            self.assertFalse(first.exception,str(list(first.exception)))
            initial=first.session_state['physics_data']
            for page in ['Library','Quiz','Flash Cards','Insights','Teacher Dashboard','Dashboard']:
                first.radio(key='physics_nav').set_value(page).run()
                self.assertFalse(first.exception,str(list(first.exception)))
            second=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
            first.session_state['physics_data']['students'][0]['name']='Changed'
            self.assertEqual(second.session_state['physics_data']['students'][0]['name'],'User 1')
            first.radio(key='physics_nav').set_value('Teacher Dashboard').run()
            first.button(key='student_aarav').click().run()
            self.assertFalse(first.exception)
            self.assertEqual(first.selectbox(key='physics_teacher_student').value,'aarav')
            self.assertTrue(any('Aarav Sharma' in h.value for h in first.subheader))
            next(b for b in first.button if b.label=='Restart workspace').click().run()
            self.assertEqual(first.session_state['physics_data']['students'][0]['name'],'User 1')
            next(b for b in first.button if b.label=='Study your own material').click().run()
            self.assertFalse(first.exception,str(list(first.exception)))
            self.assertEqual(first.session_state['workspace_view'],'Uploads')
            self.assertFalse(first.session_state['study_persist'])
            next(b for b in first.button if b.label=='← Back to learning workspace').click().run()
            self.assertFalse(first.exception,str(list(first.exception)))

    def test_recall_navigation_and_class_analysis_precede_roster(self):
        with patch.dict(os.environ,{'PHOENIX_MODE':'demo'}):
            at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
            at.radio(key='physics_nav').set_value('Flash Cards').run()
            self.assertFalse(at.exception,str(list(at.exception)))
            self.assertTrue(any('of 24' in c.value for c in at.caption))
            next(b for b in at.button if b.label=='Next →').click().run()
            self.assertEqual(at.session_state['physics_card_index'],1)
            at.selectbox(key='physics_card_filter').set_value('thermal').run()
            self.assertEqual(at.session_state['physics_card_index'],0)
            self.assertTrue(any('of 3' in c.value for c in at.caption))
            at.button(key='recall_Recalled well').click().run()
            self.assertIn('thermal-concept',at.session_state['physics_cards'])
            at.radio(key='physics_nav').set_value('Teacher Dashboard').run()
            self.assertFalse(at.exception,str(list(at.exception)))
            headings=[h.value for h in at.subheader]
            self.assertLess(headings.index('Class concept heatmap'),headings.index('Student overview'))
            self.assertLess(headings.index('Priority teaching plan'),headings.index('Student overview'))
            at.button(key='student_user-1').click().run()
            self.assertTrue(any(h.value=='Priority teaching plan' for h in at.subheader))

    def test_wrong_retry_solution_same_concept_and_teacher_history(self):
        with patch.dict(os.environ,{'PHOENIX_MODE':'demo'}):
            at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
            before=student_report(at.session_state['physics_data'],'user-1')['attempted']
            at.radio(key='physics_nav').set_value('Quiz').run()
            next(b for b in at.button if b.label=='Start 5-question round').click().run()
            bank=at.session_state['physics_data']['bank'];round_=at.session_state['physics_round']
            q=next(q for q in bank if q['id']==round_['queue'][0]);wrong=(q['correct_index']+1)%4
            next(r for r in at.radio if r.label=='Your answer').set_value(wrong)
            next(b for b in at.button if b.label=='Check answer').click().run()
            self.assertEqual(at.session_state['physics_round']['stage'],'hint')
            self.assertFalse(any(x.value=='Worked solution' for x in at.markdown))
            next(r for r in at.radio if r.label=='Your answer').set_value(wrong)
            next(b for b in at.button if b.label=='Check retry').click().run()
            self.assertEqual(at.session_state['physics_round']['stage'],'approach')
            self.assertTrue(any('Understand the concept' in m.value for m in at.markdown))
            self.assertFalse(any('**Worked solution**' in m.value for m in at.markdown))
            next(r for r in at.radio if r.label=='Your answer').set_value(wrong)
            next(b for b in at.button if b.label=='Check final attempt').click().run()
            self.assertEqual(at.session_state['physics_round']['stage'],'solution')
            next(b for b in at.button if b.label=='Continue →').click().run()
            round_=at.session_state['physics_round']
            self.assertEqual(len(round_['queue']),6)
            fresh=next(q for q in bank if q['id']==round_['queue'][1])
            self.assertEqual(fresh['concept'],q['concept']);self.assertNotEqual(fresh['id'],q['id'])
            self.assertEqual(student_report(at.session_state['physics_data'],'user-1')['attempted'],before+1)
            at.radio(key='physics_nav').set_value('Teacher Dashboard').run()
            self.assertFalse(at.exception)
            at.button(key='student_user-1').click().run()
            self.assertTrue(any(m.label=='Correct / attempted' and m.value.endswith('/ '+str(before+1)) for m in at.metric))

if __name__=='__main__':unittest.main()
