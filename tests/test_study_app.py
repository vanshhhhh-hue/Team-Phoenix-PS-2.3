from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest

from study import get_question, new_state

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (ROOT / 'samples/users/user-1/demo-notes.md').read_text(encoding='utf-8')


class StudyAppTests(unittest.TestCase):
    def app(self):
        at = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=15)
        at.session_state['study'] = new_state()
        at.session_state['study_use_ai'] = False
        at.session_state['study_persist'] = False
        at.run()
        self.assertFalse(at.exception)
        return at

    def button(self, at, label):
        next(b for b in at.button if b.label == label).click().run()
        self.assertFalse(at.exception, str(list(at.exception)))

    def upload(self, at):
        at.radio(key='study_nav').set_value('Library').run()
        next(t for t in at.text_input if t.label == 'Title for pasted notes').set_value('My biology notes')
        at.text_area[0].set_value(SAMPLE)
        self.button(at, 'Build from pasted notes →')
        self.assertEqual(len(at.session_state['study']['documents']),0)
        self.button(at,'Confirm source and build pack')
        self.assertEqual(len(at.session_state['study']['documents']), 1)

    def test_uploaded_notes_through_quiz_hints_insights_and_revision(self):
        at = self.app(); self.upload(at)
        self.button(at, 'Take an adaptive quiz →')
        self.button(at, 'Start adaptive quiz →')
        self.button(at, 'Give me a hint')
        for i in range(5):
            state = at.session_state['study']
            quiz = state['quizzes'][0]
            question = get_question(state, quiz['question_ids'][i])
            next(r for r in at.radio if r.label == 'Choose your answer').set_value(
                (question['correct_index'] + 1) % 4 if i == 0 else question['correct_index'])
            self.button(at, 'Check my answer →')
            if i == 0:
                self.assertFalse(any(question['evidence_quote'] == x.value for x in at.info))
                self.button(at, 'Show worked explanation')
            self.assertTrue(any(question['evidence_quote'] == x.value for x in at.info))
            self.button(at, 'View results →' if i == 4 else 'Next question →')
        self.assertEqual(len(at.session_state['study']['attempts']), 5)
        self.assertEqual(at.session_state['study']['attempts'][0]['hint_count'], 1)
        self.button(at, 'See weak topics →')
        self.assertEqual(at.session_state['study_nav'], 'Insights')
        self.assertTrue(any('first responses' in m.value for m in at.markdown))
        at.radio(key='study_nav').set_value('Flash Cards').run()
        self.button(at, 'Reveal answer')
        self.button(at, 'Good')
        self.assertEqual(len(at.session_state['study']['reviews']), 1)
        self.assertFalse(at.exception)

    def test_sidebar_lab_is_supporting_module_and_back_navigation_works(self):
        at = self.app()
        self.button(at, '🧪 Open Misconception Lab')
        self.assertEqual(at.session_state['workspace_view'], 'Lab')
        self.assertTrue(any('Put your rule' in t.value for t in at.title))
        self.button(at, '← Back to Phoenix')
        self.assertEqual(at.session_state['workspace_view'], 'Study')
        self.assertTrue(any('Start studying' in t.value for t in at.title))

    def test_empty_submission_reports_readable_error_and_preserves_library(self):
        at = self.app()
        at.radio(key='study_nav').set_value('Library').run()
        self.button(at, 'Build from pasted notes →')
        self.assertTrue(at.error)
        self.assertEqual(at.session_state['study']['documents'], [])


if __name__ == '__main__':
    unittest.main()
