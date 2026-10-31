"""Shared class priorities, teaching scaffolds and recall-deck behavior."""
from copy import deepcopy
import unittest
from engine import DomainError
from physics_practice import start_round, respond, current_question, upgrade_round
from physics_teaching import TEACHING, recall_cards, guided_approach, worked_explanation
from physics_cards import flashcard_html
from showcase import load_showcase, teaching_report, record_response


class TeachingTests(unittest.TestCase):
    def setUp(self):self.data=load_showcase()

    def test_class_totals_priorities_and_single_student_scope(self):
        class_=teaching_report(self.data)
        rows=[r for s in self.data['students'] for r in s['history']]
        self.assertEqual(class_['attempted'],len(rows))
        self.assertEqual(class_['correct'],sum(r['correct'] for r in rows))
        self.assertEqual(sum(t['attempted'] for t in class_['topics']),len(rows))
        scores=[p['score'] for p in class_['priorities']]
        self.assertEqual(scores,sorted(scores,reverse=True))
        for p in class_['priorities']:
            self.assertEqual(p['errors'],sum(s['errors'] for s in p['affected']))
            self.assertEqual(p['errors'],sum(x['count'] for x in p['patterns']))
            self.assertEqual(len(p['steps']),3)
            self.assertTrue(p['exit_is_fresh'])
            self.assertNotIn(p['exit_question_id'],{r['question_id'] for r in rows})
            self.assertTrue(p['counter'] and p['exit_question'] and p['exit_answer'])
            self.assertAlmostEqual(p['score'],.6*(p['errors']/p['attempted'])+.25*len(p['affected'])/len(class_['students'])+.15*p['recent_error'])
        single=teaching_report(self.data,['user-1'])
        self.assertEqual(len(single['students']),1)
        self.assertEqual(single['attempted'],len(self.data['students'][0]['history']))
        self.assertTrue(all(all(s['id']=='user-1' for s in p['affected']) for p in single['priorities']))

    def test_class_priorities_change_with_errors_not_supported_retry_grades(self):
        data=deepcopy(self.data)
        keys={q['id']:q['correct_index'] for q in data['bank']}
        for student in data['students']:
            for r in student['history']:r.update(correct=True,selected_index=keys[r['question_id']])
        self.assertEqual(teaching_report(data)['priorities'],[])
        target=data['students'][0]['history'][0]
        target.update(correct=False,selected_index=(keys[target['question_id']]+1)%4)
        changed=teaching_report(data)
        self.assertEqual(len(changed['priorities']),1)
        self.assertEqual(changed['priorities'][0]['id'],target['concept'])

    def test_three_attempts_are_separate_and_guidance_has_no_computed_answer(self):
        bank=self.data['bank'];round_=start_round(bank,[c['id'] for c in self.data['chapters'][:5]])
        q=current_question(round_,bank);wrong=(q['correct_index']+1)%4
        for attempt in [1,2,3]:
            round_=respond(round_,bank,wrong)
            self.data=record_response(self.data,'user-1',round_['id'],round_['responses'][-1])
            self.assertEqual(round_['responses'][-1]['attempt'],attempt)
        with self.assertRaises(DomainError):respond(round_,bank,wrong)
        row=self.data['students'][0]['history'][-1]
        self.assertTrue(row['hint_used'] and row['approach_used'] and row['solution_used'])
        self.assertEqual(len(row['support_attempts']),2)
        self.assertFalse(row['correct'])
        for question in bank:
            idea,steps,check=guided_approach(question)
            self.assertEqual(len(steps),3)
            self.assertNotIn(question['solution'],str((idea,steps,check)))
            self.assertEqual(worked_explanation(question)['answer'],question['options'][question['correct_index']])

    def test_existing_two_attempt_round_upgrades_without_losing_answers(self):
        round_=start_round(self.data['bank'],[c['id'] for c in self.data['chapters'][:5]])
        q=current_question(round_,self.data['bank']);wrong=(q['correct_index']+1)%4
        round_=respond(respond(round_,self.data['bank'],wrong),self.data['bank'],wrong)
        round_.pop('protocol_version');round_['stage']='solution'
        upgraded=upgrade_round(round_)
        self.assertEqual(upgraded['stage'],'approach')
        self.assertEqual(upgraded['responses'],round_['responses'])
        self.assertEqual(upgraded['queue'],round_['queue'])

    def test_deck_covers_every_chapter_and_flip_markup_is_accessible_and_escaped(self):
        deck=recall_cards(self.data['chapters'])
        self.assertEqual(len(deck),24)
        self.assertEqual(len({c['id'] for c in deck}),24)
        for cid in TEACHING:
            cards=[c for c in deck if c['concept']==cid]
            self.assertEqual({c['kind'] for c in cards},{'concept','relation','pitfall'})
            self.assertTrue(all(c['mnemonic'] and c['example'] and c['answer'] for c in cards))
        card=dict(deck[0],prompt='<unsafe "prompt">')
        html=flashcard_html(card)
        self.assertIn('&lt;unsafe &quot;prompt&quot;&gt;',html)
        self.assertIn('aria-pressed="false"',html)
        self.assertIn('prefers-reduced-motion',html)
        self.assertIn('rotateY(180deg)',html)
        self.assertNotIn('src="https://',html)


if __name__=='__main__':unittest.main()
