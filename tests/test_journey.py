from copy import deepcopy
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
import study
import nlm
from journey import UNITS, journey, note_sections

ROOT=Path(__file__).resolve().parents[1]

class JourneyTests(unittest.TestCase):
    def test_units_cover_bank_once_and_notes_are_scoped(self):
        ids=[cid for unit in UNITS for cid in unit['concepts']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(set(ids),{c['id'] for c in nlm.load_pack()['concepts']})
        text=('Static friction is a contact force that matches the push until its limiting value. '
              'Limiting resistance is the largest static friction force before slipping begins. '
              'Surface roughness is a property that influences the resistance to relative slipping.')
        s,did,_=study.add_document(study.new_state(),'Friction lecture','friction.txt',text.encode(),use_ai=False)
        before=deepcopy(s)
        self.assertEqual(note_sections(s,'static')[0]['document_id'],did)
        self.assertEqual(note_sections(s,'impulse'),[])
        self.assertEqual(next(r for r in journey(s) if r['id']=='static')['notes'][0]['text'],s['documents'][0]['chunks'][0]['text'])
        self.assertEqual(s,before)
        self.assertEqual(study.import_state(study.export_state(s)),s)

    def test_topic_action_starts_correct_session_and_lesson_controls_differ(self):
        at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
        at.session_state['study']=study.new_state()
        at.session_state['study_persist']=False
        at.session_state['study_use_ai']=False
        at.run()
        at.radio(key='study_nav').set_value('Library').run()
        at.button(key='journey_practice_impulse').click().run()
        self.assertFalse(at.exception)
        sessions=at.session_state['study']['nlm']['sessions']
        self.assertEqual(sessions[0]['question_id'],'impulse-1')
        self.assertEqual(at.session_state['nlm_active_My learning'],sessions[0]['id'])
        at.radio(key='study_nav').set_value('Library').run()
        at.button(key='journey_learn_static').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['nlm_concept'],'static')
        self.assertTrue(any(s.label=='Applied force (N)' for s in at.slider))
        self.assertFalse(any(s.label=='Circular speed (m/s)' for s in at.slider))
        at.button(key='journey_learn_circular').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['nlm_concept'],'circular')
        self.assertTrue(any(s.label=='Circular speed (m/s)' for s in at.slider))
        self.assertFalse(any(s.label=='Applied force (N)' for s in at.slider))
