from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from engine import DomainError
from study import new_state, export_state, import_state, save_state, load_state
import nlm
from nlm_visuals import quantities, render, render_question

NOW=datetime(2026,10,30,18,0,tzinfo=timezone.utc)


class NLMTests(unittest.TestCase):
    def begin(self,qid='inertia-1',learner='My learning'):
        state=nlm.install(new_state())
        return nlm.start(state,qid,learner,NOW)

    def act(self,state,sid,action,answer=None,now=NOW):
        s=next(s for s in state['nlm']['sessions'] if s['id']==sid)
        rev=len(s['events'])
        return nlm.event(state,sid,action,answer,'event-'+str(rev),rev,now)

    def current(self,state):
        s=state['nlm']['sessions'][-1]; return nlm.view(s)

    def answer(self,state,sid,correct=True):
        q=nlm.question(self.current(state)['question_id'])
        return self.act(state,sid,'answer',q['correct_index'] if correct else (q['correct_index']+1)%4)

    def test_pack_inventory_references_and_rejection(self):
        p=nlm.load_pack()
        self.assertEqual(len(p['concepts']),12); self.assertEqual(len(p['misconceptions']),18)
        self.assertEqual(sum(q['role']=='primary' for q in p['questions']),36)
        self.assertEqual(sum(q['role']=='follow_up' for q in p['questions']),36)
        self.assertEqual(sum(q['role']=='transfer' for q in p['questions']),4)
        self.assertEqual(len(p['flashcards']),24)
        for mutate in (lambda p:p['visuals'][0].update(family='<script>'),
                       lambda p:p['questions'][0].update(follow_up_ids=['missing']),
                       lambda p:p['questions'][0].update(correct_index=True),
                       lambda p:p['concepts'][0].update(prerequisite_ids=['inertia']),
                       lambda p:p['questions'][0].update(evidence_refs=['fake'])):
            bad=deepcopy(p); mutate(bad)
            with self.assertRaises(DomainError): nlm.validate_pack(bad)

    def test_first_error_hidden_solution_retries_and_explicit_reveal(self):
        state,sid=self.begin(); state=self.answer(state,sid,False)
        v=self.current(state)
        self.assertEqual(v['step'],'HINT_1'); self.assertFalse(v['solution'])
        first=deepcopy(v['first_response'])
        state=self.answer(state,sid,False)
        self.assertEqual(self.current(state)['step'],'HINT_2'); self.assertFalse(self.current(state)['solution'])
        state=self.answer(state,sid,False)
        self.assertEqual(self.current(state)['step'],'SOLUTION'); self.assertTrue(self.current(state)['solution'])
        self.assertEqual(self.current(state)['first_response'],first)
        other,oid=self.begin('second-1'); other=self.answer(other,oid,False)
        other=self.act(other,oid,'solution')
        self.assertTrue(self.current(other)['solution'])
        fresh,fid=self.begin()
        with self.assertRaises(DomainError): self.act(fresh,fid,'solution')

    def test_followup_correct_route_independent_grading_and_transfer(self):
        state,sid=self.begin(); state=self.answer(state,sid)
        self.assertEqual(self.current(state)['step'],'FIRST_RESPONSE')
        state=self.act(state,sid,'continue'); v=self.current(state)
        self.assertEqual(v['step'],'FOLLOW_UP'); self.assertNotEqual(v['question_id'],'inertia-1')
        self.assertFalse(v['solution']); self.assertIsNone(v['follow_up'])
        state=self.answer(state,sid)
        self.assertTrue(self.current(state)['follow_up']['correct'])
        state=self.act(state,sid,'transfer')
        self.assertEqual(self.current(state)['phase'],'transfer')
        state=self.answer(state,sid,False)
        self.assertFalse(self.current(state)['transfer']['correct'])
        self.assertTrue(self.current(state)['first_response']['correct'])

    def test_followup_failure_bounded_remediation_and_delayed(self):
        state,sid=self.begin(); state=self.answer(state,sid,False)
        state=self.act(state,sid,'solution'); state=self.act(state,sid,'continue')
        state=self.answer(state,sid,False)
        self.assertEqual(self.current(state)['step'],'REMEDIATION')
        state=self.act(state,sid,'continue'); state=self.answer(state,sid,False)
        self.assertEqual(self.current(state)['step'],'RECAP')
        with self.assertRaises(DomainError): self.act(state,sid,'continue')
        with self.assertRaises(DomainError): self.act(state,sid,'delayed')
        state=self.act(state,sid,'delayed',now=NOW+timedelta(days=1))
        q=nlm.question(self.current(state)['question_id'])
        state=self.act(state,sid,'answer',q['correct_index'],NOW+timedelta(days=1))
        self.assertTrue(self.current(state)['delayed']['correct'])

    def test_duplicate_stale_events_and_pause_resume(self):
        state,sid=self.begin(); state=self.answer(state,sid,False)
        duplicate=nlm.event(state,sid,'answer',state['nlm']['sessions'][0]['events'][0]['answer'],'event-0',0,NOW)
        self.assertEqual(duplicate,state)
        with self.assertRaises(DomainError): nlm.event(state,sid,'answer',0,'stale',0,NOW)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'progress.json'; state=save_state(state,path)
            resumed=load_state(path)
            self.assertEqual(nlm.start(resumed,'inertia-1',now=NOW)[1],sid)
            self.assertEqual(self.current(resumed)['step'],'HINT_1')
            corrupt=deepcopy(state); corrupt['nlm']['sessions'][0]['events'][0]['answer']=True
            with self.assertRaises(DomainError): save_state(corrupt,path)
            self.assertEqual(load_state(path),state)

    def test_migration_and_malformed_import_preserve_state(self):
        old=new_state(); old.pop('nlm'); old.pop('debugger'); old.pop('practice_events',None); old={k:v for k,v in old.items() if k in {'schema_version','documents','quizzes','attempts','cards','reviews'}}; old['schema_version']=2
        migrated=import_state(json.dumps(old)); self.assertEqual(migrated['schema_version'],6); self.assertEqual(migrated['documents'],[])
        state,sid=self.begin(); state=self.answer(state,sid)
        self.assertEqual(import_state(export_state(state)),state)
        bad=deepcopy(state); bad['nlm']['sessions'][0]['question_id']='missing'
        with self.assertRaises(DomainError): import_state(json.dumps(bad))
        self.assertEqual(self.current(state)['step'],'FIRST_RESPONSE')

    def test_help_and_first_response_analytics_separate(self):
        state,sid=self.begin('second-1'); state=self.act(state,sid,'hint')
        state=self.answer(state,sid,False); state=self.answer(state,sid)
        state=self.act(state,sid,'continue'); state=self.answer(state,sid)
        row=nlm.insights(state['nlm'])[0]
        self.assertFalse(row['first_correct']); self.assertEqual(row['pre_answer_help'],1)
        self.assertEqual(row['retries'],1); self.assertEqual(row['status'],'follow-up passed')
        self.assertEqual(row['review'],'delayed review pending'); self.assertIsNone(row['delayed_recall'])

    def test_probe_uncertainty_and_demo_reset_isolation(self):
        state,sid=self.begin('inertia-1','Demo Learner A'); state=self.answer(state,sid,False)
        state=self.act(state,sid,'probe','uncertain')
        self.assertEqual(nlm.insights(state['nlm'])[0]['probe_response'],'uncertain')
        with self.assertRaises(DomainError): self.act(state,sid,'probe','concept')
        state,other=nlm.start(state,'second-1','My learning',NOW)
        reset=nlm.reset_demo(state,'Demo Learner A')
        self.assertEqual([s['id'] for s in reset['nlm']['sessions']],[other])
        with self.assertRaises(DomainError): nlm.reset_demo(state,'My learning')

    def test_recall_schedule_reveal_does_not_inflate_and_validation(self):
        state=nlm.install(new_state()); cid='card-inertia-0'
        state=nlm.review_card(state,cid,'Good','r1',now=NOW)
        self.assertEqual(state,nlm.review_card(state,cid,'Good','r1',now=NOW))
        with self.assertRaises(DomainError): nlm.review_card(state,cid,'Good','r2',now=NOW)
        self.assertEqual(state['nlm']['reviews'][0]['due_at'],(NOW+timedelta(days=1)).isoformat())
        state=nlm.review_card(state,cid,'Good','r2',now=NOW+timedelta(days=1))
        self.assertEqual(state['nlm']['reviews'][-1]['due_at'],(NOW+timedelta(days=4)).isoformat())
        self.assertEqual(import_state(export_state(state)),state)
        bad=deepcopy(state); bad['nlm']['reviews'][-1]['step']=0
        with self.assertRaises(DomainError): import_state(export_state(bad))

    def test_offline_no_provider_call(self):
        with patch('ai_provider.generate',side_effect=AssertionError('Unexpected network call')):
            state,sid=self.begin(); state=self.answer(state,sid)
            state=self.act(state,sid,'continue'); state=self.answer(state,sid)
            self.assertEqual(self.current(state)['step'],'COMPLETE')

    def test_visual_boundaries_and_physics_consistency(self):
        for family in sorted(nlm.FAMILIES):
            for params in ({},{'mass':.1,'force':0.,'angle':0.,'speed':0.,'radius':.5},
                           {'mass':100.,'force':100.,'angle':75.,'speed':20.,'radius':100.}):
                svg,alt,p=render(family,**params)
                self.assertTrue(alt); self.assertNotIn('<script',svg)
                self.assertAlmostEqual(p['acceleration']*p['mass'],p['force'])
                self.assertAlmostEqual(p['circle_acceleration']*p['radius'],p['speed']**2)
        self.assertEqual(quantities('friction',mass=2,force=3)['friction'],3)
        self.assertFalse(quantities('friction',mass=2,force=8)['slipping'])
        self.assertTrue(quantities('friction',mass=2,force=8.01)['slipping'])
        self.assertAlmostEqual(quantities('incline',angle=60)['incline_normal'],10)
        for params in ({'mass':0},{'mass':True},{'speed':float('nan')},{'radius':-.5},{'mu_s':.1,'mu_k':.5}):
            with self.assertRaises(DomainError): quantities('block',**params)

    def test_independent_physics_answer_keys(self):
        # Independent expected answers, not read from the build script or explanations.
        expected={
         'second-1':'3 m/s²','second-2':'6 N left','second-4':'6 m/s along the force','second-6':'4 m/s² right',
         'second-7':'4 m/s² right','second-8':'3 m/s²',
         'normal-1':'600 N','normal-2':'mg/2','normal-4':'Zero','normal-5':'15 N','normal-6':'400 N',
         'tension-1':'22 N','tension-3':'4 N','tension-4':'30 N','tension-5':'14 N','tension-6':'2 m/s²',
         'equilibrium-1':'5 N','equilibrium-3':'100/√3 N','equilibrium-4':'20 N upward','equilibrium-6':'12 N west',
         'static-1':'3 N','static-3':'15 N','kinetic-1':'10 N left','kinetic-4':'6 N right','kinetic-6':'Zero',
         'momentum-3':'2 m/s left','momentum-5':'6 kg m/s right',
         'impulse-1':'12 N s','impulse-3':'12 N s','impulse-4':'-8 N s','impulse-5':'Zero',
         'circular-1':'8 m/s²','circular-2':'Up and left','circular-4':'4',
         'roads-1':'10 m/s','roads-2':'10 m/s','roads-4':'1','roads-5':'2','roads-6':'mg'}
        for qid,answer in expected.items():
            q=nlm.question(qid); self.assertEqual(q['options'][q['correct_index']],answer,qid)
        self.assertEqual(6/2,3); self.assertEqual(50*(10+2),600)
        self.assertEqual(.5*4*6,12); self.assertEqual(2*(-1-3),-8)

    def test_question_graphs_match_givens_without_computed_answer(self):
        for q in nlm.load_pack()['questions']:
            if q['scene']:
                svg,alt=render_question(q['scene'])
                self.assertIn('<svg',svg); self.assertTrue(alt)
                self.assertNotIn('Answer:',svg); self.assertNotIn('area =',svg)
        def area(scene):
            points=scene['points']
            return sum((b[0]-a[0])*(a[1]+b[1])/2 for a,b in zip(points,points[1:]))
        self.assertEqual(area(nlm.question('impulse-1')['scene']),12)
        self.assertEqual(area(nlm.question('impulse-3')['scene']),12)
        self.assertEqual(area(nlm.question('impulse-5')['scene']),0)
        points=nlm.question('second-2')['scene']['points']
        self.assertEqual((points[1][1]-points[0][1])/(points[1][0]-points[0][0]),-2)
        bad=nlm.load_pack(); bad['questions'][0]['scene']={'kind':'script','code':'danger'}
        with self.assertRaises(DomainError): nlm.validate_pack(bad)

    def test_real_legacy_records_survive_migration_and_idempotent_pack_install(self):
        from study import add_document
        text=(Path(__file__).resolve().parents[1]/'samples/users/user-1/demo-notes.md').read_bytes()
        legacy,_,_=add_document(new_state(),'Old notes','old.md',text,use_ai=False,now=NOW)
        old=deepcopy(legacy); old.pop('nlm'); old.pop('debugger'); old.pop('practice_events',None); old={k:v for k,v in old.items() if k in {'schema_version','documents','quizzes','attempts','cards','reviews'}}; old['schema_version']=2
        migrated=import_state(json.dumps(old))
        for key in ('documents','quizzes','attempts','cards','reviews'): self.assertEqual(migrated[key],old[key])
        state=nlm.install(migrated); state,sid=nlm.start(state,'inertia-1',now=NOW)
        state=self.answer(state,sid,False)
        self.assertEqual(nlm.install(state),state)
        for key in ('documents','quizzes','attempts','cards','reviews'): self.assertEqual(state[key],legacy[key])


if __name__=='__main__': unittest.main()
