"""Rebuild fictional sample history offline using the application's domain operations."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/phoenix'))
import study
import nlm


def build():
    now = datetime(2026, 10, 24, 9, tzinfo=timezone.utc)
    sample = ROOT / 'samples/users/user-1'
    state, did, _ = study.add_document(study.new_state(), 'Cell Biology — lecture notes',
        'demo-notes.md', (sample / 'demo-notes.md').read_bytes(), count=9, use_ai=False, now=now)
    state, qid = study.start_quiz(state, did, count=9, now=now)
    quiz = next(q for q in state['quizzes'] if q['id'] == qid)
    for i, item in enumerate(quiz['question_ids']):
        question = study.get_question(state, item)
        answer = (question['correct_index'] + (1 if i % 3 == 0 else 0)) % 4
        state = study.answer_question(state, qid, item, answer, 0, f'sample-answer-{i}', now=now + timedelta(minutes=i+1))
    for i, card in enumerate(state['cards'][:3]):
        state = study.grade_card(state, card['id'], ['Good', 'Hard', 'Again'][i], f'sample-card-{i}', now=now + timedelta(hours=1))
    state = nlm.install(state)
    primaries = [q for q in nlm.load_pack()['questions'] if q['role'] == 'primary']
    for i, question in enumerate(primaries[:12]):
        at = now + timedelta(days=1, minutes=i)
        state, sid = nlm.start(state, question['id'], now=at)
        answer = (question['correct_index'] + (1 if i % 3 == 0 else 0)) % 4
        state = nlm.event(state, sid, 'answer', answer, f'sample-newton-{i}', 0, now=at)
    state['preferences']['last_material'] = did
    state['preferences']['use_ai'] = False
    study.validate_state(state)
    (sample / 'workspace.json').write_text(study.export_state(state), encoding='utf-8')
    print('Built validated fictional User 1 workspace. No provider or private checkpoint accessed.')


if __name__ == '__main__':
    build()
