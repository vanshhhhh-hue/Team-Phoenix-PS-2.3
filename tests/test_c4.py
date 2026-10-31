"""Regression evidence for core audit failures; never opens the owner's checkpoint."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from multiprocessing import get_context
import hashlib
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import study
import nlm
import storage
from study_flow import show_hint, submit_answer, upload_activity_view, hint_level, save_draft
from workspace import card_queue, pending_tasks, NLM_ID
from navigation import NavigationTarget, validate_target
from test_core import NOW

ROOT=Path(__file__).resolve().parents[1]


def fixture():
    return study.add_document(study.new_state(),'Biology','notes.md',(ROOT/'samples/users/user-1/demo-notes.md').read_bytes(),use_ai=False,now=NOW)[0]


def writer(path,base,updated,gate,out):
    gate.wait(10)
    result=storage.commit_snapshot(path,base,updated)
    out.put((result.status,result.revision))


class StorageTests(unittest.TestCase):
    def test_real_processes_do_not_overwrite_each_other(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json'; base=study.save_state(fixture(),path)
            quiz,_=study.start_quiz(base,base['documents'][0]['id'],now=NOW)
            card=study.grade_card(base,base['cards'][0]['id'],'Good','rating',NOW)
            import subprocess,sys
            basefile=Path(folder)/'base.json';basefile.write_text(json.dumps(base))
            gate=Path(folder)/'gate';workers=[]
            for i,updated in enumerate((quiz,card)):
                payload=Path(folder)/f'updated{i}.json';payload.write_text(json.dumps(updated))
                workers.append(subprocess.Popen([sys.executable,str(ROOT/'scripts/storage_probe.py'),str(path),str(basefile),str(payload),str(gate)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True))
            gate.write_text('ready')
            results=[]
            for process in workers:
                stdout,stderr=process.communicate(timeout=20)
                self.assertEqual(process.returncode,0,stderr);results.append(json.loads(stdout))
            self.assertEqual(sorted(r['status'] for r in results),['committed','conflict'])
            final=study.load_state(path)
            self.assertEqual(final['revision'],base['revision']+1)
            self.assertEqual(bool(final['quizzes'])+bool(final['reviews']),1)

    def test_idempotency_payload_conflict_and_workspace_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json'; base=study.save_state(fixture(),path)
            updated,_=study.start_quiz(base,base['documents'][0]['id'],now=NOW)
            first=storage.commit_snapshot(path,base,updated,command_id='one')
            self.assertEqual(first.status,'committed')
            self.assertEqual(storage.commit_snapshot(path,base,updated,command_id='one').status,'already_applied')
            changed=deepcopy(updated); changed['material_meta'][base['documents'][0]['id']]['title']='Changed'
            self.assertEqual(storage.commit_snapshot(path,base,changed,command_id='one').status,'rejected')
            alien=deepcopy(first.state); alien['workspace_id']=study.new_state()['workspace_id']
            self.assertEqual(storage.commit_snapshot(path,alien,alien).status,'conflict')
            self.assertEqual(study.load_state(path),first.state)

    def test_failed_replace_and_backup_preserve_exact_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json'; base=study.save_state(fixture(),path); original=path.read_bytes()
            updated,_=study.start_quiz(base,base['documents'][0]['id'],now=NOW)
            for target in ('storage.os.replace','storage.os.fsync'):
                with patch(target,side_effect=OSError('disk full')):
                    result=storage.commit_snapshot(path,base,updated)
                self.assertEqual(result.status,'io_error'); self.assertEqual(path.read_bytes(),original)
                self.assertEqual(list(path.parent.glob('*.tmp')),[])

    def test_restore_preview_conflict_corrupt_start_and_undo_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json'; base=study.save_state(fixture(),path)
            preview=storage.prepare_restore(path,study.export_state(base).encode())
            updated,_=study.start_quiz(base,base['documents'][0]['id'],now=NOW)
            newer=storage.commit_snapshot(path,base,updated).state
            self.assertEqual(storage.apply_restore(path,preview,preview.revision).status,'conflict')
            self.assertEqual(study.load_state(path),newer)
            path.write_bytes(b'{broken'); corrupt=path.read_bytes()
            loaded=storage.read_workspace(path)
            self.assertEqual(loaded.status,'recoverable_error');self.assertEqual(path.read_bytes(),corrupt)
            preview=storage.prepare_restore(path,study.export_state(base).encode())
            restored=storage.apply_restore(path,preview,preview.revision)
            self.assertEqual(restored.status,'committed');self.assertNotEqual(restored.state['workspace_id'],base['workspace_id'])
            self.assertEqual(path.with_suffix('.json.pre-restore').read_bytes(),corrupt)
            self.assertEqual(restored.state['attempts'],base['attempts'])

    def test_v2_through_v6_migrate_without_rewriting_records(self):
        original=fixture()
        from schema_v6 import LEGACY
        for version in (2,3,4,5):
            keys=set(LEGACY)
            if version<5:keys.remove('practice_events')
            if version<4:keys.remove('debugger')
            if version<3:keys.remove('nlm')
            old={k:deepcopy(original[k]) for k in keys};old['schema_version']=version
            migrated=study.import_state(json.dumps(old))
            self.assertEqual(migrated['schema_version'],6)
            for key in keys-{'schema_version'}:self.assertEqual(migrated[key],old[key])
            self.assertEqual(migrated['activity_events'],[])
            self.assertEqual(study.import_state(study.export_state(migrated)),migrated)
        bad=deepcopy(original); bad['schema_version']=7
        with self.assertRaises(Exception):study.import_state(json.dumps(bad))


class SafetyTests(unittest.TestCase):
    def test_busy_lock_in_another_process_returns_a_bounded_failure(self):
        import subprocess,sys,time
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json';base=study.save_state(fixture(),path);original=path.read_bytes()
            ready=Path(folder)/'ready';release=Path(folder)/'release'
            process=subprocess.Popen([sys.executable,str(ROOT/'scripts/storage_probe.py'),'--hold',str(path),str(ready),str(release)])
            try:
                deadline=time.monotonic()+5
                while not ready.exists():
                    self.assertLess(time.monotonic(),deadline);time.sleep(.02)
                lock=storage.workspace_lock
                with patch('storage.workspace_lock',side_effect=lambda p:lock(p,timeout=.1)):
                    result=storage.commit_snapshot(path,base,base)
                self.assertEqual(result.status,'io_error');self.assertIn('busy',result.message)
                self.assertEqual(path.read_bytes(),original)
            finally:
                release.write_text('release');process.wait(timeout=10)
            self.assertEqual(process.returncode,0)

    def test_historical_answer_cannot_be_rewritten_even_with_a_consistent_key(self):
        with tempfile.TemporaryDirectory() as folder:
            s=fixture();mid=s['documents'][0]['id'];s,qid=study.start_quiz(s,mid,1,now=NOW)
            q=s['quizzes'][0]['question_ids'][0];s=submit_answer(s,qid,q,study.get_question(s,q)['correct_index'],'original',NOW)
            path=Path(folder)/'state.json';s=study.save_state(s,path)
            changed=deepcopy(s);changed['attempts'][0]['selected_index']=(changed['attempts'][0]['selected_index']+1)%4;changed['attempts'][0]['correct']=False
            study.validate_state(changed)
            self.assertEqual(storage.commit_snapshot(path,s,changed).status,'rejected')
            self.assertEqual(study.load_state(path),s)

    def test_schedule_tampering_and_wrong_configured_model_are_rejected(self):
        from ai_provider import connection_check,Settings
        s=fixture();s['cards'][0]['due_at']=(NOW+timedelta(days=5)).isoformat()
        with self.assertRaisesRegex(Exception,'schedule'):study.validate_state(s)
        with patch('ai_provider.settings',return_value=Settings('not-a-real-key','missing-model')):
            with patch('ai_provider._request',return_value={'supportedGenerationMethods':[]}) as request:
                self.assertFalse(connection_check());self.assertEqual(request.call_args.args[0],'models/missing-model')

    def test_legacy_newton_transition_replays_without_reselection(self):
        s=nlm.install(study.new_state());s,sid=nlm.start(s,'inertia-1',now=NOW)
        s=nlm.event(s,sid,'answer',nlm.question('inertia-1')['correct_index'],'a',0,NOW)
        s=nlm.event(s,sid,'continue',None,'b',1,NOW)
        old=deepcopy(s)
        event=old['nlm']['sessions'][0]['events'][1];event['action']='continue';event['answer']=None
        before=nlm.view(old['nlm']['sessions'][0])
        from schema_v6 import LEGACY
        old={k:old[k] for k in LEGACY};old['schema_version']=5
        loaded=study.import_state(json.dumps(old))
        self.assertEqual(nlm.view(loaded['nlm']['sessions'][0]),before)
        self.assertEqual(loaded['nlm'],old['nlm'])

    def test_extraction_preview_survives_fresh_session_without_generation(self):
        at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
        at.session_state['study']=study.new_state();at.session_state['study_persist']=False;at.session_state['study_use_ai']=False
        at.run();at.radio(key='study_nav').set_value('Library').run()
        next(t for t in at.text_input if t.label=='Title for pasted notes').set_value('Draft notes')
        next(t for t in at.text_area if t.label=='Paste notes or syllabus').set_value((ROOT/'samples/users/user-1/demo-notes.md').read_text())
        next(b for b in at.button if b.label=='Build from pasted notes →').click().run()
        self.assertFalse(at.exception);saved=study.import_state(study.export_state(at.session_state['study']))
        self.assertEqual(saved['documents'],[]);self.assertIn('source_preview',saved['preferences'])
        reopened=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
        reopened.session_state['study']=saved;reopened.session_state['study_persist']=False;reopened.session_state['study_use_ai']=False;reopened.session_state['study_nav']='Library'
        reopened.run();self.assertFalse(reopened.exception)
        self.assertTrue(any(b.label=='Confirm source and build pack' for b in reopened.button))


class ActivityTests(unittest.TestCase):
    def test_hint_reload_correct_retry_and_pending_last_wrong_answer(self):
        state=fixture();state,qid=study.start_quiz(state,state['documents'][0]['id'],5,now=NOW)
        ids=state['quizzes'][0]['question_ids']
        for i,q in enumerate(ids):
            key=study.get_question(state,q)['correct_index']
            if i==4:
                state=show_hint(state,qid,q,1,NOW)
                state=study.import_state(study.export_state(state))
                self.assertEqual(hint_level(state,qid,q),1)
                self.assertEqual(show_hint(state,qid,q,1,NOW),state)
            state=submit_answer(state,qid,q,(key+1)%4 if i==4 else key,'answer'+str(i),NOW)
        first=deepcopy(state['attempts'])
        v=upload_activity_view(state,qid)
        self.assertTrue(v['scoring_complete']);self.assertFalse(v['recovery_complete'])
        self.assertEqual(v['pending_support_question_id'],ids[-1])
        self.assertEqual(pending_tasks(state,material_id=state['documents'][0]['id'],now=NOW)[0]['status'],'unfinished')
        key=study.get_question(state,ids[-1])['correct_index']
        state=study.practice_event(state,qid,ids[-1],'retry',key,'retry',0,NOW)
        self.assertTrue(upload_activity_view(state,qid)['latest_retry']['correct'])
        self.assertEqual(state['attempts'],first)
        state=study.practice_event(state,qid,ids[-1],'finish',None,'finish',1,NOW)
        self.assertTrue(upload_activity_view(state,qid)['recovery_complete'])
        self.assertEqual(pending_tasks(state,material_id=state['documents'][0]['id'],now=NOW),[])

    def test_card_queue_disjoint_and_due_boundary(self):
        state=fixture();mid=state['documents'][0]['id']; cid=state['cards'][0]['id']
        q=card_queue(state,mid,now=NOW)
        self.assertEqual((q['new_count'],q['due_count'],q['upcoming_count']),(6,0,0))
        state=study.grade_card(state,cid,'Again','review',NOW)
        q=card_queue(state,mid,now=NOW)
        self.assertEqual((q['new_count'],q['due_count'],q['upcoming_count']),(5,0,1))
        self.assertEqual(q['next_due_at'],(NOW+timedelta(minutes=10)).isoformat())
        self.assertEqual([c['id'] for c in card_queue(state,mid,now=NOW+timedelta(minutes=10))['items']],[cid])
        self.assertEqual(len(card_queue(state,mid,'preview',NOW)['items']),6)

    def test_regeneration_keeps_old_keys_and_card_schedules(self):
        s=fixture();mid=s['documents'][0]['id'];s,qid=study.start_quiz(s,mid,1,now=NOW)
        q=s['quizzes'][0]['question_ids'][0];s=submit_answer(s,qid,q,study.get_question(s,q)['correct_index'],'answer',NOW)
        s=study.grade_card(s,s['cards'][0]['id'],'Good','review',NOW)
        old=deepcopy(s);s,_=study.regenerate_document(s,mid,use_ai=False,now=NOW)
        self.assertEqual(s['attempts'],old['attempts']);self.assertEqual(s['reviews'],old['reviews'])
        self.assertEqual(s['cards'][:6],old['cards']);self.assertEqual(study.get_question(s,q),study.get_question(old,q))
        self.assertEqual(len(s['pack_versions']),2)
        s,new=study.start_quiz(s,mid,1,now=NOW)
        self.assertNotIn(s['quizzes'][-1]['question_ids'][0],old['quizzes'][0]['question_ids'])
        study.validate_state(s)

    def test_local_key_rejected_even_with_valid_quote(self):
        s=fixture();bad=deepcopy(s);bad['documents'][0]['questions'][0]['correct_index']=(bad['documents'][0]['questions'][0]['correct_index']+1)%4
        with self.assertRaisesRegex(Exception,'reconstruct'):study.validate_state(bad)

    def test_draft_is_bounded_ungraded_and_roundtrips(self):
        s=fixture();mid=s['documents'][0]['id'];s,qid=study.start_quiz(s,mid,now=NOW);q=s['quizzes'][0]['question_ids'][0]
        s=save_draft(s,mid,qid,q,'My ungraded explanation',NOW)
        self.assertEqual(study.import_state(study.export_state(s)),s);self.assertEqual(s['attempts'],[])
        with self.assertRaises(Exception):save_draft(s,mid,qid,q,'x'*4001,NOW)


class NavigationAppTests(unittest.TestCase):
    def app(self,state=None,material=None,page='Dashboard'):
        at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
        at.session_state['study']=deepcopy(state or fixture());at.session_state['study_persist']=False
        at.session_state['study_use_ai']=False;at.session_state['study_nav']=page
        at.session_state['study_material']=material or NLM_ID
        at.run();self.assertFalse(at.exception,str(list(at.exception)));return at

    def click(self,at,label):
        next(b for b in at.button if b.label==label).click().run()
        self.assertFalse(at.exception,str(list(at.exception)))

    def test_dashboard_cross_material_actions_and_explore(self):
        s=fixture();mid=s['documents'][0]['id']
        for target in ('Library','Quiz'):
            at=self.app(s)
            at.button(key='active_'+target+mid).click().run()
            self.assertFalse(at.exception,str(list(at.exception)))
            self.assertEqual(at.session_state['study_material'],mid);self.assertEqual(at.session_state['study_nav'],target)
        at=self.app(s,mid);at.button(key='active_Library'+NLM_ID).click().run()
        self.assertEqual(at.session_state['study_material'],NLM_ID)
        self.assertEqual(at.session_state['study_nav'],'Library')

    def test_report_resume_and_last_wrong_refresh_correct_retry_copy(self):
        s=fixture();mid=s['documents'][0]['id'];s,qid=study.start_quiz(s,mid,1,now=NOW)
        q=s['quizzes'][0]['question_ids'][0];key=study.get_question(s,q)['correct_index']
        s=submit_answer(s,qid,q,(key+1)%4,'first',NOW)
        at=self.app(s,mid);at.button(key='report_'+qid).click().run()
        self.assertFalse(at.exception,str(list(at.exception)))
        self.assertTrue(any(r.label=='Retry your answer' for r in at.radio))
        next(r for r in at.radio if r.label=='Retry your answer').set_value(key)
        self.click(at,'Check retry')
        self.assertTrue(any('Correct on retry, with help.' in x.value for x in at.success))
        saved=at.session_state['study'];at=self.app(saved,mid,'Quiz')
        self.assertTrue(any('Correct on retry, with help.' in x.value for x in at.success))
        self.click(at,'View results →');self.assertEqual(at.session_state['study']['attempts'][0]['correct'],False)

    def test_foreign_activity_link_rejected(self):
        s=fixture();s,qid=study.start_quiz(s,s['documents'][0]['id'],now=NOW)
        with self.assertRaises(Exception):validate_target(s,NavigationTarget('Quiz',NLM_ID,activity_kind='upload_quiz',activity_id=qid))


class ManagementTests(unittest.TestCase):
    def test_archive_reactivate_and_rename_preserve_learning_and_schedules(self):
        from workspace import update_material,materials,default_material
        s=fixture();mid=s['documents'][0]['id'];s=study.grade_card(s,s['cards'][0]['id'],'Good','rating',NOW)
        old=deepcopy(s)
        s=update_material(s,mid,title='Renamed notes',visibility='archived')
        self.assertEqual(next(m for m in materials(s) if m['id']==mid)['title'],'Renamed notes')
        self.assertEqual(default_material(s),NLM_ID)
        s=update_material(s,mid,visibility='active')
        self.assertEqual(default_material(s),mid)
        for key in ('documents','attempts','cards','reviews'):self.assertEqual(s[key],old[key])
        self.assertEqual(study.import_state(study.export_state(s)),s)

    def test_duplicate_at_twenty_documents_opens_existing_pack_without_generation(self):
        s=fixture();original=(ROOT/'samples/users/user-1/demo-notes.md').read_bytes()
        for i in range(1,20):s,_,_=study.add_document(s,'Material '+str(i),'notes.md',original+f' Unique explanatory identifier number {i}.'.encode(),use_ai=False,now=NOW)
        before=deepcopy(s)
        duplicate,mid,message=study.add_document(s,'Existing notes','notes.md',original,now=NOW,generator=lambda *a:self.fail('duplicate must not generate'))
        self.assertEqual(duplicate,before);self.assertEqual(mid,s['documents'][0]['id']);self.assertIn('already',message)
        with self.assertRaises(Exception):study.add_document(s,'New notes','notes.md',original+b' A genuinely different explanation.',now=NOW,generator=lambda *a:self.fail('capacity must fail before generation'))

    def test_utf8_byte_limit_returns_failure_and_preserves_disk(self):
        from workspace import update_material
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json';s=study.save_state(fixture(),path);original=path.read_bytes()
            updated=update_material(s,s['documents'][0]['id'],title='अध्ययन सामग्री')
            text=study.export_state(updated);limit=(len(text)+len(text.encode('utf-8')))//2
            self.assertLess(len(text),limit);self.assertGreater(len(text.encode('utf-8')),limit)
            with patch.object(study,'MAX_STATE',limit):result=storage.commit_snapshot(path,s,updated)
            self.assertEqual(result.status,'rejected');self.assertEqual(path.read_bytes(),original)


class FollowupTests(unittest.TestCase):
    def test_generated_checks_reserve_exposure_and_keep_original_score(self):
        from followups import build_followup
        from workspace import report
        s=fixture();mid=s['documents'][0]['id'];s,qid=study.start_quiz(s,mid,1,now=NOW)
        origin=s['quizzes'][0]['question_ids'][0];q=study.get_question(s,origin)
        s=submit_answer(s,qid,origin,(q['correct_index']+1)%4,'wrong',NOW)
        # Reviewed synthetic output fixture tests plumbing; it is not a live model result.
        prompts=['A leaf receives sunlight but has no green pigment. Which process is directly impaired?',
                 'A sealed plant chamber loses light energy input. Which stored-energy pathway is first affected?',
                 'A researcher measures sugar accumulation after illuminating a green leaf. Which mechanism explains the change?']
        qs=[dict(q,prompt=prompt,options=['Light energy capture','Protein assembly','Water diffusion','Cell division'],correct_index=0,
                 hints=['Consider the energy entering the system.','Follow the light-to-chemical conversion described by the source.']) for prompt in prompts]
        pack=dict(summary='Synthetic changed-situation fixture',topics=[q['topic']],questions=qs,cards=[dict(front=prompt,back='Light energy capture',topic=q['topic'],source_chunk_id=q['source_chunk_id'],evidence_quote=q['evidence_quote']) for prompt in prompts])
        s,_=build_followup(s,mid,origin,now=NOW,generator=lambda *a,**kw:deepcopy(pack),reviewer=lambda *a,**kw:True)
        self.assertEqual(s['pack_versions'][-1]['kind'],'independent')
        s,check=study.start_quiz(s,mid,3,now=NOW)
        self.assertEqual(sum(e['kind']=='present' and e['activity_id']==check for e in s['activity_events']),3)
        ids=s['quizzes'][-1]['question_ids']
        for index,item in enumerate(ids):
            if index==1:s=show_hint(s,check,item,1,NOW)
            s=submit_answer(s,check,item,0,'check'+str(index),NOW)
        r=report(s,mid,now=NOW)
        self.assertEqual((r['correct'],r['attempted']),(0,1))
        self.assertEqual(r['checks']['follow_up'],dict(attempted=3,correct=2,assisted=1))
        study.validate_state(s)
        with self.assertRaises(Exception):study.start_quiz(s,mid,3,now=NOW)

    def test_corrupt_start_renders_recovery_before_normal_app(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json';path.write_bytes(b'{broken')
            with patch.object(study,'STATE_PATH',path):
                at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
                at.run()
                self.assertFalse(at.exception,str(list(at.exception)))
                self.assertTrue(any(t.value=='Recover your workspace' for t in at.title))
                self.assertTrue(any(b.label=='Preview recovery backup' for b in at.button))
                self.assertEqual(path.read_bytes(),b'{broken')


class ExperimentTests(unittest.TestCase):
    def test_all_concepts_have_bounded_meaningful_models(self):
        from experiments import scenario,CONTROLS
        expected={'inertia':('speed_after_3s',4),'second':('acceleration',3),'third':('force_on_a',-6),
            'normal':('support',20),'tension':('support',20),'equilibrium':('magnitude',5),
            'static':('can_stick',True),'kinetic':('acceleration',1),'momentum':('momentum',2),
            'impulse':('impulse',18),'circular':('acceleration',8)}
        for concept,controls in CONTROLS.items():
            result=scenario(concept)
            self.assertIn('<title>',result['svg']);self.assertTrue(result['assumptions'])
            if concept in expected:
                key,value=expected[concept];self.assertAlmostEqual(result['outputs'][key],value)
            for key,label,lo,hi,default in controls:
                other=hi if default!=hi else lo
                self.assertNotEqual(scenario(concept,**{key:other})['result'],result['result'],(concept,key))
            with self.assertRaises(Exception):scenario(concept,unrelated=4)
        self.assertEqual(scenario('normal',acceleration=-12)['outputs']['support'],0)
        self.assertEqual(scenario('impulse',force=-6)['outputs']['impulse'],-18)
        self.assertEqual(scenario('inertia',force=30)['outputs']['speed_after_3s'],0)
        self.assertFalse(scenario('static',force=30)['outputs']['can_stick'])

    def test_prediction_observation_is_saved_without_grades(self):
        from study_flow import record_experiment
        s=study.new_state();s=record_experiment(s,'second',{'mass':2.,'force':6.},0,'a=F/m',now=NOW)
        self.assertEqual(len(s['activity_events']),1);self.assertEqual(s['attempts'],[])
        self.assertEqual(study.import_state(study.export_state(s)),s)
        self.assertEqual(record_experiment(s,'second',{'mass':2.,'force':6.},0,'a=F/m',now=NOW),s)


class QualityTests(unittest.TestCase):
    def test_disputed_item_excluded_without_losing_original_grade(self):
        from content_quality import flag_item
        from workspace import report
        s=fixture();mid=s['documents'][0]['id'];s,qid=study.start_quiz(s,mid,1,now=NOW)
        q=s['quizzes'][0]['question_ids'][0];s=submit_answer(s,qid,q,study.get_question(s,q)['correct_index'],'first',NOW)
        first=deepcopy(s['attempts']);s=flag_item(s,q,'answer seems wrong',now=NOW)
        self.assertEqual(s['attempts'],first);r=report(s,mid,now=NOW)
        self.assertEqual(r['attempted'],0);self.assertEqual(r['excluded'],1)
        s,_=study.start_quiz(s,mid,5,now=NOW);self.assertNotIn(q,s['quizzes'][-1]['question_ids'])
        study.validate_state(s)

    def test_combined_failure_preserves_source_and_nonenglish_is_specific(self):
        from ai_provider import ProviderError
        s=study.new_state();before=deepcopy(s)
        with self.assertRaisesRegex(Exception,'AI generation failed and local recall'):
            study.add_document(s,'Sparse','notes.txt',b'Topic headings only; '+b'x'*100,generator=lambda *a:(_ for _ in ()).throw(ProviderError('quota')),now=NOW)
        self.assertEqual(s,before)
        with self.assertRaisesRegex(Exception,'English prose'):
            study.add_document(s,'Notes','notes.txt',('यह एक शिक्षण दस्तावेज है। '*20).encode(),use_ai=False,now=NOW)

    def test_generation_review_rejection_never_promotes_candidate(self):
        from followups import build_followup
        s=fixture();mid=s['documents'][0]['id'];s,qid=study.start_quiz(s,mid,1,now=NOW)
        origin=s['quizzes'][0]['question_ids'][0];q=study.get_question(s,origin)
        s=submit_answer(s,qid,origin,(q['correct_index']+1)%4,'wrong',NOW);before=deepcopy(s)
        pack=study.local_pack(s['documents'][0]['chunks'],3)
        with self.assertRaisesRegex(Exception,'unavailable'):
            build_followup(s,mid,origin,now=NOW,generator=lambda *a,**kw:pack,reviewer=lambda *a,**kw:False)
        self.assertEqual(s,before)

    def test_regenerated_identical_prompt_is_repeat_evidence(self):
        from learning_events import normalize_evidence
        s=fixture();mid=s['documents'][0]['id'];s,qid=study.start_quiz(s,mid,1,now=NOW)
        q=s['quizzes'][0]['question_ids'][0];s=submit_answer(s,qid,q,study.get_question(s,q)['correct_index'],'first',NOW)
        s,_=study.regenerate_document(s,mid,use_ai=False,now=NOW)
        original=study.get_question(s,q)['prompt']
        s,qid=study.start_quiz(s,mid,1,now=NOW)
        q=next(item['id'] for item in s['documents'][0]['questions'] if item['prompt']==original and item['id']!=q)
        s['quizzes'][-1]['question_ids']=[q]
        s=submit_answer(s,qid,q,study.get_question(s,q)['correct_index'],'second',NOW)
        self.assertTrue(normalize_evidence(s)[-1]['repeat'])


if __name__=='__main__':unittest.main()
