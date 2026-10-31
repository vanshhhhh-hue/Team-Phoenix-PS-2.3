"""Connected Phoenix contracts: preservation, reporting and resumable support."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import unittest
from streamlit.testing.v1 import AppTest
from engine import DomainError
import study
import nlm
from workspace import NLM_ID,materials,report

ROOT=Path(__file__).resolve().parents[1]
NOW=datetime(2026,10,31,tzinfo=timezone.utc)

class IntegrationTests(unittest.TestCase):
    def uploaded(self):
        return study.add_document(study.new_state(),'New biology notes','new-notes.md',
                                  (ROOT/'samples/users/user-1/demo-notes.md').read_bytes(),use_ai=False,now=NOW)[:2]

    def test_legacy_presentation_is_reversible_and_new_uploads_stay_active(self):
        s,did=self.uploaded(); original=deepcopy(s)
        self.assertTrue(all(m['visibility']=='active' for m in materials(s)))
        s['documents'][0]['created_at']='2026-10-30T22:52:08.280754+05:30'
        s['material_meta'][did]['visibility']='history'
        self.assertEqual(materials(s)[1]['visibility'],'history')
        before=deepcopy(s); report(s,now=NOW+timedelta(days=1)); materials(s)
        self.assertEqual(s,before)
        self.assertEqual(study.import_state(study.export_state(s)),s)
        self.assertEqual(original['documents'][0]['id'],s['documents'][0]['id'])

    def test_hint_retry_resume_stale_input_and_report_denominator(self):
        s,did=self.uploaded();s,qid=study.start_quiz(s,did,count=1,now=NOW)
        question=study.get_question(s,s['quizzes'][0]['question_ids'][0]); q=question['id']; key=question['correct_index']
        s=study.answer_question(s,qid,q,(key+1)%4,0,'first',now=NOW)
        self.assertEqual(study.practice_view(s,qid,q)['hints'],1)
        self.assertFalse(study.practice_view(s,qid,q)['solution'])
        s=study.practice_event(s,qid,q,'retry',(key+2)%4,'retry1',0,now=NOW)
        self.assertEqual(study.practice_view(s,qid,q)['hints'],2)
        saved=study.import_state(study.export_state(s)); self.assertEqual(saved,s)
        with self.assertRaises(DomainError): study.practice_event(s,qid,q,'retry',key,'stale',0,now=NOW)
        s=study.practice_event(s,qid,q,'retry',key,'retry2',1,now=NOW)
        self.assertEqual(study.practice_event(s,qid,q,'retry',key,'retry2',1,now=NOW),s)
        self.assertTrue(study.practice_view(s,qid,q)['solution'])
        r=report(s,did,now=NOW+timedelta(seconds=1))
        self.assertEqual((r['correct'],r['attempted'],r['retries']),(0,1,2))
        self.assertEqual(r['checks']['follow_up']['attempted'],0)
        self.assertEqual(r['assisted'],2)
        self.assertEqual(r['events'][0]['id'],'study:first')
        bad=deepcopy(s);bad['practice_events'][0]['revision']=3
        with self.assertRaises(DomainError):study.import_state(json.dumps(bad))

    def test_v4_migration_preserves_all_original_collections(self):
        s,did=self.uploaded(); old=deepcopy(s);old.pop('practice_events');old={k:v for k,v in old.items() if k in {'schema_version','documents','quizzes','attempts','cards','reviews','nlm','debugger'}}; old['schema_version']=4
        migrated=study.import_state(json.dumps(old))
        self.assertEqual(migrated['schema_version'],6)
        self.assertEqual(migrated['practice_events'],[])
        for k in old:
            if k!='schema_version':self.assertEqual(migrated[k],old[k])
        self.assertEqual(study.migrate_state(migrated),migrated)

    def test_newton_prior_exposure_cannot_become_fresh_check(self):
        s=nlm.install(study.new_state());s,sid=nlm.start(s,'inertia-1',now=NOW)
        s=nlm.event(s,sid,'answer',nlm.question('inertia-1')['correct_index'],'a',0,NOW)
        s=nlm.event(s,sid,'continue',None,'b',1,NOW)
        target=nlm.view(s['nlm']['sessions'][0])['question_id']
        s=nlm.event(s,sid,'answer',nlm.question(target)['correct_index'],'c',2,NOW)
        s,sid2=nlm.start(s,'inertia-1',now=NOW)
        s=nlm.event(s,sid2,'answer',nlm.question('inertia-1')['correct_index'],'d',0,NOW)
        before=deepcopy(s)
        alternative=nlm.event(s,sid2,'continue',None,'e',1,NOW)
        self.assertNotEqual(nlm.view(alternative['nlm']['sessions'][-1])['question_id'],target)
        self.assertEqual(s,before)
        self.assertEqual(report(s,NLM_ID,now=NOW)['attempted'],1)

    def test_report_retains_hint_history_after_fresh_check_and_pending_retention(self):
        s=nlm.install(study.new_state());s,sid=nlm.start(s,'inertia-1',now=NOW)
        wrong=(nlm.question('inertia-1')['correct_index']+1)%4
        s=nlm.event(s,sid,'answer',wrong,'wrong',0,NOW)
        s=nlm.event(s,sid,'solution',None,'solution',1,NOW)
        s=nlm.event(s,sid,'continue',None,'continue',2,NOW)
        q=nlm.view(s['nlm']['sessions'][0])['question_id']
        s=nlm.event(s,sid,'answer',nlm.question(q)['correct_index'],'check',3,NOW)
        r=report(s,NLM_ID,now=NOW)
        self.assertEqual((r['correct'],r['attempted']),(0,1))
        self.assertEqual(r['quizzes'][0]['hints'],1)
        self.assertEqual(r['checks']['follow_up']['correct'],1)
        self.assertEqual(r['pending'],0); self.assertEqual(r['upcoming'],1)
        self.assertEqual(r['solutions'],1)
        filtered=report(s,NLM_ID,now=NOW,topic_ids=['newton:second'])
        self.assertEqual(filtered['attempted'],0)
        self.assertEqual(filtered['checks']['follow_up']['attempted'],0)

    def test_navigation_compatibility_and_sample_mode_do_not_write_progress(self):
        for old,expected in [('Revision','Flash Cards'),('Newton’s Laws','Library'),('Debugger','Quiz')]:
            at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
            at.session_state['study']=study.new_state();at.session_state['study_persist']=False
            at.session_state['study_use_ai']=False;at.session_state['study_nav']=old
            at.run();self.assertFalse(at.exception,str(list(at.exception)))
            self.assertEqual(at.session_state['study_nav'],expected)
            self.assertEqual(at.radio(key='study_nav').options,['Dashboard','Library','Quiz','Flash Cards','Insights'])
        at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
        at.session_state['study']=self.uploaded()[0];at.session_state['study_persist']=False
        at.session_state['study_use_ai']=False;at.run()
        before=deepcopy(at.session_state['study'])
        at.radio(key='study_nav').set_value('Insights').run()
        self.assertFalse(at.exception);self.assertEqual(at.session_state['study'],before)
        self.assertFalse(any(toggle.key=='sample_overview' for toggle in at.toggle))

if __name__=='__main__':unittest.main()
