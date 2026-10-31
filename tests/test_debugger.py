from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import tempfile
import unittest

import debugger as db
import nlm
from debugger_content import QUESTIONS,validate_content
from learner_model import build_learner_summary
from learning_events import normalize_evidence
from source_retrieval import retrieve_repair_sources
from study import new_state,import_state,export_state,save_state,load_state,add_document
from engine import DomainError

NOW=datetime(2026,10,31,10,tzinfo=timezone.utc)


class DebuggerTests(unittest.TestCase):
    def begin(self,topic='mass',state=None,learner='My learning'):
        return db.start(state or new_state(),topic,learner,NOW)

    def act(self,s,sid,action,value=None,now=NOW):
        ep=db.get_episode(s,sid); rev=len(ep['events'])
        return db.event(s,sid,action,value,f'{sid}:{rev}',rev,now)

    def view(self,s,sid): return db.view(db.get_episode(s,sid))

    def answer(self,s,sid,option=None,now=NOW):
        q=QUESTIONS[self.view(s,sid)['pending']]
        return self.act(s,sid,'answer',dict(option=q['correct'] if option is None else option,confidence='unsure'),now)

    def repair(self,topic='mass'):
        s,sid=self.begin(topic)
        s=self.answer(s,sid,0 if topic=='mass' else 1)
        for _ in range(2):
            s=self.act(s,sid,'next')
            s=self.answer(s,sid,0)
        s=self.act(s,sid,'next')
        return s,sid

    def followup(self,s,sid):
        s=self.act(s,sid,'next'); s=self.answer(s,sid)
        s=self.act(s,sid,'next'); s=self.answer(s,sid)
        return s

    def test_content_keys_and_two_distinct_repairs(self):
        self.assertTrue(validate_content())
        self.assertEqual(QUESTIONS['mass-start']['options'][QUESTIONS['mass-start']['correct']],'3 m/s² right')
        s,sid=self.repair(); self.assertEqual(self.view(s,sid)['repair']['hypothesis'],'mass_rule')
        s,sid=self.repair('motion'); self.assertEqual(self.view(s,sid)['repair']['hypothesis'],'motion_force')
        h=build_learner_summary(s,'My learning',NOW)['hypotheses']['motion_force']
        self.assertEqual(h['status'],'supported_candidate')

    def test_same_wrong_answer_different_history_selects_different_probe(self):
        cold,sid=self.begin();cold=self.answer(cold,sid,0);cold=self.act(cold,sid,'next')
        prior,nid=nlm.start(nlm.install(new_state()),'second-3',now=NOW)
        prior=nlm.event(prior,nid,'answer',1,'old-event',0,NOW)
        warm,wid=self.begin(state=prior);warm=self.answer(warm,wid,0);warm=self.act(warm,wid,'next')
        self.assertEqual(self.view(cold,sid)['pending'],'mass-law-probe')
        self.assertEqual(self.view(warm,wid)['pending'],'mass-division-probe')
        self.assertTrue(self.view(warm,wid)['decision']['evidence_ids'])
        off=db.set_history(prior,'My learning',False)
        off,oid=self.begin(state=off);off=self.answer(off,oid,0);off=self.act(off,oid,'next')
        self.assertEqual(self.view(off,oid)['pending'],'mass-law-probe')

    def test_correct_relation_and_failed_division_get_execution_scaffold(self):
        s,sid=self.begin();s=self.answer(s,sid,0);s=self.act(s,sid,'next')
        s=self.answer(s,sid,1);s=self.act(s,sid,'next');s=self.answer(s,sid,0)
        s=self.act(s,sid,'next')
        self.assertEqual(self.view(s,sid)['repair']['hypothesis'],'execution')

    def test_new_counterevidence_changes_status_preserves_support(self):
        s,sid=self.repair()
        self.assertEqual(build_learner_summary(s,'My learning',NOW)['hypotheses']['mass_rule']['status'],'supported_candidate')
        s,nid=nlm.start(nlm.install(s),'second-3',now=NOW)
        s=nlm.event(s,nid,'answer',1,'counter',0,NOW)
        h=build_learner_summary(s,'My learning',NOW)['hypotheses']['mass_rule']
        self.assertEqual(h['status'],'mixed_evidence');self.assertEqual(len(h['support']),2)
        aged=build_learner_summary(s,'My learning',NOW+timedelta(days=31))
        self.assertEqual(aged['hypotheses']['mass_rule']['status'],'needs_recheck')

    def test_duplicate_stale_invalid_answers_do_not_mutate(self):
        s,sid=self.begin(); before=deepcopy(s)
        ep=db.get_episode(s,sid)
        self.assertEqual(db.event(s,sid,'next',token=ep['events'][0]['id'],revision=0,now=NOW),s)
        for val in (True,None,-1,99):
            with self.assertRaises(DomainError): self.act(s,sid,'answer',dict(option=val,confidence='unsure'))
        with self.assertRaises(DomainError): db.event(s,sid,'answer',{},'bad',0,NOW)
        self.assertEqual(s,before)

    def test_assisted_probe_does_not_support_candidate_and_skip_is_bounded(self):
        s,sid=self.begin();s=self.answer(s,sid,0);s=self.act(s,sid,'next')
        s=self.act(s,sid,'help');s=self.answer(s,sid,0)
        h=build_learner_summary(s,'My learning',NOW)['hypotheses']['mass_rule']
        self.assertEqual(h['status'],'candidate');self.assertEqual(len(h['support']),1)
        s=self.act(s,sid,'repair');self.assertEqual(self.view(s,sid)['phase'],'teach')

    def test_immediate_transfer_delayed_and_assistance_separate(self):
        s,sid=self.repair();s=self.followup(s,sid)
        self.assertEqual(self.view(s,sid)['repair_status'],'immediate_check_passed')
        with self.assertRaises(DomainError): self.act(s,sid,'review','delayed')
        s=self.act(s,sid,'review','transfer');s=self.act(s,sid,'next')
        s=self.act(s,sid,'help');s=self.answer(s,sid)
        self.assertEqual(self.view(s,sid)['repair_status'],'reopened')
        later=NOW+timedelta(days=1)
        s=self.act(s,sid,'review','delayed',later);s=self.act(s,sid,'next',now=later)
        s=self.answer(s,sid,now=later)
        v=self.view(s,sid)
        self.assertEqual(v['repair_status'],'delayed_check_passed')
        self.assertTrue(v['immediate']['correct']);self.assertTrue(v['transfer']['helped'])
        self.assertEqual(datetime.fromisoformat(v['due_at']),later+timedelta(days=3))
        self.assertEqual(import_state(export_state(s)),s)

    def test_global_exposure_and_bank_exhaustion_are_honest(self):
        s,sid=self.repair();s=self.followup(s,sid)
        s,sid2=self.begin(state=s);s=self.answer(s,sid2)
        s=self.act(s,sid2,'next');self.assertEqual(self.view(s,sid2)['pending'],'mass-fresh-2')
        s=self.answer(s,sid2)
        s,sid3=self.begin(state=s);s=self.answer(s,sid3);s=self.act(s,sid3,'next')
        self.assertTrue(self.view(s,sid3)['unavailable'])
        rows=normalize_evidence(s)
        self.assertTrue(any(r['repeat'] for r in rows))

    def test_migration_roundtrip_rejection_and_atomic_save(self):
        s,sid=self.repair()
        old=new_state();old.pop('debugger');old.pop('practice_events',None); old={k:v for k,v in old.items() if k in {'schema_version','documents','quizzes','attempts','cards','reviews','nlm'}}; old['schema_version']=3
        migrated=import_state(json.dumps(old))
        self.assertEqual(migrated['nlm'],old['nlm']);self.assertEqual(migrated['schema_version'],6)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.json';s=save_state(s,path)
            bad=deepcopy(s);bad['debugger']['episodes'][0]['events'][1]['value']['option']=True
            with self.assertRaises(DomainError):save_state(bad,path)
            self.assertEqual(load_state(path),s)
        bad=deepcopy(s);bad['debugger']['episodes'][0]['events'][0]['value']['evidence_ids']=['missing']
        with self.assertRaises(DomainError):import_state(json.dumps(bad))

    def test_history_controls_are_scoped_and_legacy_metadata_stays_unknown(self):
        s,nid=nlm.start(nlm.install(new_state()),'inertia-1',now=NOW)
        s=nlm.event(s,nid,'answer',1,'native',0,NOW)
        legacy=deepcopy(s['nlm']);s,sid=self.begin(state=s)
        s,demo=self.begin(state=s,learner='Demo Learner A')
        rows=normalize_evidence(s)
        self.assertEqual(next(r for r in rows if r['origin']=='newton')['exposed'],'unknown')
        deleted=db.delete_history(s,'My learning')
        self.assertEqual(deleted['nlm'],legacy)
        self.assertEqual([ep['id'] for ep in deleted['debugger']['episodes']],[demo])
        self.assertFalse(deleted['debugger']['history']['My learning'])
        self.assertEqual(import_state(export_state(deleted)),deleted)

    def test_import_rejects_cross_learner_and_future_decision_references(self):
        s,sid=self.repair()
        s,did=self.begin(state=s,learner='Demo Learner A')
        s=self.answer(s,did,0)
        foreign='debugger:'+db.get_episode(s,did)['events'][1]['id']
        bad=deepcopy(s)
        bad['debugger']['episodes'][0]['events'][0]['value']['evidence_ids']=[foreign]
        with self.assertRaises(DomainError): import_state(export_state(bad))
        bad=deepcopy(s)
        bad['debugger']['episodes'][0]['events'][1]['at']=(NOW+timedelta(days=1)).isoformat()
        with self.assertRaises(DomainError): import_state(export_state(bad))
        bad=deepcopy(s);bad['debugger']['content_version']=2
        with self.assertRaises(DomainError): import_state(export_state(bad))

    def test_demo_reset_clears_only_linked_demo_cases_and_failed_delayed_reopens(self):
        s,sid=self.repair();s=self.followup(s,sid)
        later=NOW+timedelta(days=1)
        s=self.act(s,sid,'review','delayed',later);s=self.act(s,sid,'next',now=later)
        s=self.answer(s,sid,0,now=later)
        self.assertEqual(self.view(s,sid)['repair_status'],'reopened')
        s,nid=nlm.start(nlm.install(s),'second-3','Demo Learner A',NOW)
        s=nlm.event(s,nid,'answer',1,'demo-native',0,NOW)
        s,did=self.begin(state=s,learner='Demo Learner A');s=self.answer(s,did,0);s=self.act(s,did,'next')
        reset=nlm.reset_demo(s,'Demo Learner A')
        self.assertEqual([ep['id'] for ep in reset['debugger']['episodes']],[sid])
        self.assertEqual(import_state(export_state(reset)),reset)

    def test_upload_review_retrieval_and_no_unsupported_diagnosis(self):
        text=('Resultant is the vector sum of external forces that produces acceleration. '
              'Mass is a positive measure of inertia measured in kilograms. '
              'Velocity is the rate of change of position in an inertial frame. '
              'Acceleration is the rate of change of velocity under a resultant force. '
              'Newton is the SI unit of force equal to a kilogram metre per second squared. '
              'Friction is an interaction between surfaces opposing their relative sliding. ')
        s,did,_=add_document(new_state(),'Force notes','notes.txt',text.encode(),use_ai=False,now=NOW)
        before=deepcopy(s['documents']);q=s['documents'][0]['questions'][0]
        s,sid=db.start(s,'upload',now=NOW,origin={'document_id':did,'question_id':q['id']})
        refs=retrieve_repair_sources(s,did,'resultant force acceleration')
        self.assertTrue(refs);self.assertIn(refs[0]['quote'],s['documents'][0]['text'])
        self.assertEqual(self.view(s,sid)['phase'],'source')
        s=self.act(s,sid,'source_complete')
        self.assertEqual(self.view(s,sid)['repair_status'],'reviewed_source')
        self.assertEqual(s['documents'],before);self.assertEqual(import_state(export_state(s)),s)


if __name__=='__main__':unittest.main()
