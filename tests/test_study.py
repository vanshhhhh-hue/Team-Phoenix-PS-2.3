from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai_provider import ProviderError, Settings
from engine import DomainError
from study import (add_document, answer_question, build_pack, export_state, extract_upload,
                   get_question, grade_card, import_state, load_state, local_pack, new_state,
                   recommendations, save_state, start_quiz, topic_stats, validate_state)
from test_core import NOW

SAMPLE = (Path(__file__).resolve().parents[1] / 'samples/users/user-1/demo-notes.md').read_bytes()


def sample_state():
    return add_document(new_state(), 'Cell Energy', 'lecture.md', SAMPLE, use_ai=False, now=NOW)[0]


class StudyTests(unittest.TestCase):
    def test_upload_creates_grounded_local_pack_and_cards(self):
        state = sample_state(); doc = state['documents'][0]
        self.assertEqual(doc['mode'], 'local')
        self.assertEqual(len(doc['questions']), 6)
        self.assertEqual(len(state['cards']), 6)
        sources = {c['id']: c['text'] for c in doc['chunks']}
        for q in doc['questions']:
            self.assertIn(q['evidence_quote'], sources[q['source_chunk_id']])
        self.assertEqual(import_state(export_state(state)), state)

    def test_duplicate_upload_preserves_progress(self):
        state = sample_state()
        repeated, did, msg = add_document(state, 'Different title', 'other.md', SAMPLE, use_ai=False, now=NOW)
        self.assertEqual(repeated, state)
        self.assertIn('already', msg)

    def test_ai_success_and_failed_provider_fallback(self):
        _, chunks = extract_upload('notes.md', SAMPLE)
        content = local_pack(chunks, 6)
        pack, mode, _ = build_pack(chunks, generator=lambda *args: content)
        self.assertEqual(mode, 'gemini')
        for error in (ProviderError('quota'), TimeoutError(), ValueError('bad JSON')):
            with patch('study.generate', side_effect=error):
                self.assertEqual(build_pack(chunks)[1], 'local')
        bad = deepcopy(content); bad['questions'][0]['evidence_quote'] = 'A fabricated quote that never appears in the source.'
        self.assertEqual(build_pack(chunks, generator=lambda *args: bad)[1], 'local')

    def test_ai_credentials_not_in_repr_or_exports(self):
        self.assertNotIn('super-secret-value', repr(Settings('super-secret-value')))
        self.assertNotIn('API_KEY', export_state(sample_state()))

    def test_invalid_uploads(self):
        for name, payload in [('x.exe', b'hello'), ('x.pdf', b'not a PDF'), ('x.txt', b'a'),
                              ('x.txt', b'\xff' * 100), ('x.pdf', b'%PDF-invalid')]:
            with self.assertRaises(DomainError):
                extract_upload(name, payload)
        with self.assertRaises(DomainError):
            extract_upload('large.txt', b'a' * (10 * 1024 * 1024 + 1))

    def test_pdf_text_extraction_and_scan_error(self):
        # A small hand-authored PDF fixture exercises the real parser, not a mock.
        text = 'Photosynthesis is the process by which plants store chemical energy. Chlorophyll is the green pigment that absorbs light. Mitochondria are sites of respiration.'
        stream = ('BT /F1 10 Tf 40 740 Td (' + text + ') Tj ET').encode()
        objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
                   b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                   b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
                   b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
        pdf = b'%PDF-1.4\n'; offsets = [0]
        for i, obj in enumerate(objects, 1):
            offsets.append(len(pdf)); pdf += str(i).encode() + b' 0 obj\n' + obj + b'\nendobj\n'
        xref = len(pdf)
        pdf += b'xref\n0 6\n0000000000 65535 f \n'
        pdf += b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets[1:])
        pdf += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
        extracted, chunks = extract_upload('lecture.pdf', pdf)
        self.assertIn('Photosynthesis', extracted)
        self.assertEqual(chunks[0]['page'], 1)
        with patch('pypdf.PdfReader') as reader:
            reader.return_value.is_encrypted = False
            reader.return_value.pages = []
            with self.assertRaises(DomainError):
                extract_upload('scan.pdf', b'%PDF-1.4')

    def test_quiz_grading_atomic_deduplicated_and_resumable(self):
        state = sample_state(); doc = state['documents'][0]
        state, qid = start_quiz(state, doc['id'], 3, now=NOW)
        same, same_id = start_quiz(state, doc['id'], 3, now=NOW)
        self.assertEqual(qid, same_id)
        question_id = state['quizzes'][0]['question_ids'][0]
        q = get_question(state, question_id)
        with self.assertRaises(DomainError):
            answer_question(state, qid, question_id, None, 0, 'bad', NOW)
        self.assertFalse(state['attempts'])
        answered = answer_question(state, qid, question_id, q['correct_index'], 1, 'submit', NOW)
        self.assertTrue(answered['attempts'][0]['correct'])
        self.assertEqual(answered, answer_question(answered, qid, question_id, q['correct_index'], 1, 'submit', NOW))
        with self.assertRaisesRegex(DomainError,'reused'):answer_question(answered,qid,question_id,(q['correct_index']+1)%4,1,'submit',NOW)
        self.assertEqual(import_state(export_state(answered)), answered)

    def test_adaptive_selection_prioritizes_unseen_and_does_not_inflate_heatmap(self):
        state = sample_state(); doc = state['documents'][0]
        state, qid = start_quiz(state, doc['id'], 3, now=NOW)
        for i, question_id in enumerate(state['quizzes'][0]['question_ids']):
            q = get_question(state, question_id)
            state = answer_question(state, qid, question_id, (q['correct_index'] + 1) % 4, 0, f'a{i}', NOW)
        first = topic_stats(state)
        self.assertEqual(sum(r['attempted'] for r in first), 3)
        state, next_id = start_quiz(state, doc['id'], 3, now=NOW)
        self.assertTrue(set(state['quizzes'][0]['question_ids']).isdisjoint(state['quizzes'][1]['question_ids']))
        # A repeated answer on a later round cannot rewrite the first-response evidence.
        repeated = deepcopy(state['attempts'][0]); repeated['id'] = 'repeat'; repeated['correct'] = True
        state['attempts'].append(repeated)
        self.assertEqual(topic_stats(state), first)

    def test_card_scheduling_preview_and_duplicate(self):
        state = sample_state(); card_id = state['cards'][0]['id']
        state = grade_card(state, card_id, 'Good', 'r1', NOW)
        self.assertEqual(state['cards'][0]['due_at'], (NOW + timedelta(days=1)).isoformat())
        self.assertEqual(state, grade_card(state, card_id, 'Good', 'r1', NOW))
        with self.assertRaises(DomainError):
            grade_card(state, card_id, 'Good', 'early', NOW)
        state = grade_card(state, card_id, 'Good', 'r2', NOW + timedelta(days=1))
        self.assertEqual(state['cards'][0]['due_at'], (NOW + timedelta(days=4)).isoformat())
        state = grade_card(state, card_id, 'Again', 'r3', NOW + timedelta(days=4))
        self.assertEqual(state['cards'][0]['due_at'], (NOW + timedelta(days=4, minutes=10)).isoformat())
        self.assertEqual(import_state(export_state(state)), state)

    def test_persistence_and_bad_imports(self):
        state = sample_state()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'study.json'
            state = save_state(state, path)
            self.assertEqual(load_state(path), state)
            mutated = deepcopy(state); mutated['documents'][0]['questions'][0]['correct_index'] = True
            with self.assertRaises(DomainError):
                save_state(mutated, path)
            self.assertEqual(load_state(path), state)
        for text in ('{}', '[]', 'not json', '[' * 2000):
            with self.assertRaises(DomainError):
                import_state(text)
        bad = deepcopy(state); bad['API_KEY'] = 'should not persist'
        with self.assertRaises(DomainError):
            import_state(json.dumps(bad))


if __name__ == '__main__':
    unittest.main()
