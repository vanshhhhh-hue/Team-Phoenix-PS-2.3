"""Behavioral checks for bounded reinforcement and independent physics answer keys."""
import unittest
from engine import DomainError
from physics_practice import start_round, current_question, respond, advance, first_responses
from showcase import load_showcase, student_report, record_response


class PhysicsPracticeTests(unittest.TestCase):
    def setUp(self):
        self.data=load_showcase();self.bank=self.data['bank']
        self.concepts=[c['id'] for c in self.data['chapters'][:5]]

    def test_correct_round_finishes_at_five_and_cannot_double_submit(self):
        round_=start_round(self.bank,self.concepts)
        for _ in range(5):
            q=current_question(round_,self.bank)
            round_=respond(round_,self.bank,q['correct_index'])
            with self.assertRaises(DomainError):respond(round_,self.bank,q['correct_index'])
            round_=advance(round_,self.bank)
        self.assertEqual(round_['stage'],'complete');self.assertEqual(len(round_['queue']),5)
        self.assertEqual(len(first_responses(round_)),5)

    def test_mistake_requires_hint_retry_solution_and_fresh_same_concept(self):
        round_=start_round(self.bank,self.concepts);q=current_question(round_,self.bank)
        with self.assertRaises(DomainError):respond(round_,self.bank,None)
        with self.assertRaises(DomainError):advance(round_,self.bank)
        round_=respond(round_,self.bank,(q['correct_index']+1)%4)
        self.assertEqual(round_['stage'],'hint')
        with self.assertRaises(DomainError):advance(round_,self.bank)
        round_=respond(round_,self.bank,(q['correct_index']+1)%4)
        self.assertEqual(round_['stage'],'approach')
        with self.assertRaises(DomainError):advance(round_,self.bank)
        round_=respond(round_,self.bank,(q['correct_index']+1)%4)
        self.assertEqual(round_['stage'],'solution')
        round_=advance(round_,self.bank)
        fresh=current_question(round_,self.bank)
        self.assertEqual(fresh['concept'],q['concept']);self.assertNotEqual(fresh['id'],q['id'])
        round_=respond(round_,self.bank,fresh['correct_index']);round_=advance(round_,self.bank)
        self.assertEqual(current_question(round_,self.bank)['concept'],self.concepts[1])
        self.assertFalse(first_responses(round_)[0]['correct'])

    def test_persistent_errors_never_exceed_fifteen_and_exhausted_round_ends(self):
        round_=start_round(self.bank,self.concepts)
        while round_['stage']!='complete':
            q=current_question(round_,self.bank)
            for _ in range(3):round_=respond(round_,self.bank,(q['correct_index']+1)%4)
            round_=advance(round_,self.bank)
            self.assertLessEqual(len(round_['queue']),15)
        self.assertTrue(round_['limit_reached']);self.assertEqual(len(first_responses(round_)),15)
        self.assertEqual(len(set(round_['queue'])),15)

    def test_correct_retry_still_gets_fresh_check_and_history_keeps_first_error(self):
        round_=start_round(self.bank,self.concepts);q=current_question(round_,self.bank)
        round_=respond(round_,self.bank,(q['correct_index']+1)%4)
        self.data=record_response(self.data,'user-1',round_['id'],round_['responses'][-1])
        attempted=student_report(self.data,'user-1')['attempted']
        round_=respond(round_,self.bank,q['correct_index'])
        self.data=record_response(self.data,'user-1',round_['id'],round_['responses'][-1])
        self.assertEqual(student_report(self.data,'user-1')['attempted'],attempted)
        self.assertFalse(self.data['students'][0]['history'][-1]['correct'])
        self.assertTrue(self.data['students'][0]['history'][-1]['retry_correct'])
        round_=advance(round_,self.bank)
        self.assertEqual(current_question(round_,self.bank)['concept'],q['concept'])

    def test_all_computed_keys_against_independent_equations(self):
        for q in self.bank:
            n=int(q['id'].rsplit('-',1)[1])
            answers={'kinematics':(n+1)*(n+2),'forces':(n+1)*(n+2),
                'energy':n*(n+2)**2,'gravitation':16/(n+1)**2,
                'electrostatics':9e9*(n+1)*1e-6*1e-6/.1**2,
                'current':6*n/3,'optics':(20*n)/2,'thermal':100*n+100-40*n}
            observed=float(q['options'][q['correct_index']].split()[0])
            self.assertAlmostEqual(observed,answers[q['concept']],delta=max(.001,abs(answers[q['concept']])*.003))


if __name__=='__main__':unittest.main()
