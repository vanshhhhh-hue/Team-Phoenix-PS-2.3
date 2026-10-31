"""Uploaded-material study domain: sources, generation, quizzes, cards and persistence."""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
import os
import hashlib
from io import BytesIO
import json
from pathlib import Path
import random
import re
import tempfile
from uuid import uuid4

from ai_provider import ProviderError, generate
from engine import DomainError, require
from ledger import clock, stamp

MAX_UPLOAD = 10 * 1024 * 1024
MAX_TEXT = 100000
MAX_STATE = 8 * 1024 * 1024
STATE_PATH = Path(os.getenv('PHOENIX_DATA_DIR', str(Path(__file__).resolve().parents[2] / '.local'))) / 'study.json'
STOP = set('about after again also another because before being between could every first from have into '
           'more most notes only other over same should some such than that their them then there these '
           'they this those through under using very were what when where which while will with would '
           'your does each example following must'.split())


def normalize(text):
    return re.sub(r'\s+', ' ', text).strip()


def new_state():
    from nlm import empty_progress
    from debugger import empty_progress as empty_debugger
    return {'schema_version': 6, 'workspace_id': str(uuid4()), 'revision': 0, 'last_saved_at': None,
            'material_meta': {}, 'pack_versions': [], 'activity_events': [], 'item_status': {},
            'drafts': [], 'preferences': {}, 'command_receipts': [], 'documents': [], 'quizzes': [], 'attempts': [], 'cards': [], 'reviews': [],
            'nlm': empty_progress(), 'debugger': empty_debugger(), 'practice_events': []}


def extract_upload(filename, payload):
    require(isinstance(payload, bytes) and 0 < len(payload) <= MAX_UPLOAD, 'Choose a nonempty file up to 10 MB.')
    suffix = Path(filename).suffix.lower()
    pages = []
    if suffix in ('.txt', '.md'):
        try:
            text = payload.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise DomainError('invalid_input', 'Save the text file as UTF-8 and try again.') from None
        pages = [(None, text)]
    elif suffix == '.pdf':
        require(payload.startswith(b'%PDF-'), 'This is not a valid PDF file.')
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(payload))
            require(not reader.is_encrypted, 'Use an unencrypted PDF.')
            require(len(reader.pages) <= 60, 'Use a PDF with at most 60 pages.')
            total = 0
            for n, page in enumerate(reader.pages):
                text = page.extract_text() or ''
                total += len(text)
                require(total <= MAX_TEXT, 'Extracted notes exceed 100,000 characters. Upload a smaller section.')
                pages.append((n + 1, text))
        except DomainError:
            raise
        except Exception:
            raise DomainError('invalid_input', 'This PDF could not be read. Try a text-based PDF or paste its text.') from None
    else:
        raise DomainError('invalid_input', 'Supported uploads: text-based PDF, TXT and Markdown.')
    text = '\n\n'.join(t for _, t in pages).strip()
    require(80 <= len(text) <= MAX_TEXT, 'Provide 80–100,000 characters of readable notes. Scanned PDFs need OCR first.')
    chunks = []
    section = 'General concepts'
    for page, page_text in pages:
        pending = ''
        for line in page_text.splitlines():
            line = line.strip()
            if not line:
                continue
            heading = line.lstrip('#').strip()
            if (line.startswith('#') or (len(heading) < 70 and not re.search(r'[.!?]$', heading)
                                         and (heading.isupper() or heading.endswith(':')))):
                if pending:
                    chunks.append({'id': 's' + str(len(chunks) + 1), 'text': normalize(pending), 'page': page, 'section': section})
                    pending = ''
                section = heading.rstrip(':').title()[:70]
                continue
            for piece in re.findall(r'.{1,1100}(?:\s|$)', line) or [line[:1100]]:
                if len(pending) + len(piece) > 1200 and pending:
                    chunks.append({'id': 's' + str(len(chunks) + 1), 'text': normalize(pending), 'page': page, 'section': section})
                    pending = ''
                pending += ' ' + piece
        if pending.strip():
            chunks.append({'id': 's' + str(len(chunks) + 1), 'text': normalize(pending), 'page': page, 'section': section})
    require(chunks and sum(len(c['text']) for c in chunks) >= 60,
            'There is not enough readable explanation here. Add source notes, not only a list of headings.')
    return text, chunks


def _sentences(chunks):
    result = []
    for c in chunks:
        for sentence in re.split(r'(?<=[.!?])\s+|\n+', c['text']):
            sentence = sentence.strip()
            if 35 <= len(sentence) <= 500:
                result.append((sentence, c))
    return result


def local_pack(chunks, count):
    """Honest extractive practice, not a claim of local language-model understanding."""
    letters=[c for chunk in chunks for c in chunk['text'] if c.isalpha()]
    require(sum(c.isascii() for c in letters)/max(1,len(letters))>=.8,'Local recall supports English prose. Use multilingual AI generation or provide English explanatory notes; the source preview is preserved.')
    sentences = _sentences(chunks)
    if not sentences:
        sentences = [(c['text'][:350], c) for c in chunks if len(c['text']) >= 35]
    words = Counter(w.lower() for c in chunks for w in re.findall(r'\b[A-Za-z][A-Za-z-]{4,}\b', c['text'])
                    if w.lower() not in STOP)
    entries, seen = [], set()
    for sentence, c in sentences:
        match = re.match(r'([A-Za-z][A-Za-z ()-]{2,44}?)\s+(?:is|are|means|refers to)\s+', sentence, re.I)
        term = match.group(1).strip() if match else None
        if term is None:
            candidates = [w for w in re.findall(r'\b[A-Za-z][A-Za-z-]{4,}\b', sentence) if w.lower() not in STOP]
            if not candidates:
                continue
            term = max(candidates, key=lambda w: (words[w.lower()], len(w)))
        if term.lower() in seen:
            continue
        seen.add(term.lower())
        entries.append((term, sentence, c))
    require(len(entries) >= 3, 'Local practice needs at least three explanatory statements. Add fuller notes or use Gemini.')
    groups = defaultdict(list)
    for entry in entries:
        groups[entry[2]['section']].append(entry)
    entries = [group[i] for i in range(max(len(g) for g in groups.values()))
               for group in groups.values() if i < len(group)]
    questions, cards = [], []
    for i, (term, sentence, c) in enumerate(entries[:count]):
        distractors = [e[0] for e in entries if e[0].lower() != term.lower()]
        distractors += [w for w, _ in words.most_common() if w.lower() != term.lower() and w.lower() not in {s.lower() for s in distractors}]
        distractors += ['A different concept', 'No matching term', 'Not stated here']
        choices = [term, *distractors[:3]]
        rng = random.Random(hashlib.sha256(sentence.encode()).hexdigest())
        rng.shuffle(choices)
        masked = re.sub(re.escape(term), '____', sentence, count=1, flags=re.I)
        topic = c['section'] if c['section'] != 'General concepts' else 'Key concepts'
        questions.append({'prompt': 'Complete this statement from your notes:\n\n' + masked,
                          'topic': topic, 'options': choices, 'correct_index': choices.index(term),
                          'difficulty': 'easy', 'hints': ['Recall cue: read the statement around the blank and recall its subject. This cue does not explain the concept.',
                          f'The missing term starts with “{term[0]}” and has {len(term.split())} word(s).'],
                          'explanation': 'The source states: ' + sentence,
                          'source_chunk_id': c['id'], 'evidence_quote': sentence})
        cards.append({'front': 'Recall the missing term: ' + masked, 'back': term + '\n\n' + sentence,
                      'topic': topic, 'source_chunk_id': c['id'], 'evidence_quote': sentence})
    return {'summary': 'Source excerpts: ' + ' '.join(s for s, _ in sentences[:3])[:900],
            'topics': list(dict.fromkeys(q['topic'] for q in questions)), 'questions': questions, 'cards': cards}


def validate_pack(pack, chunks):
    try:
        require(type(pack) is dict and set(pack) in ({'summary','topics','questions','cards'},{'summary','topics','questions','cards','_automated_review'}), 'Invalid generated pack fields.')
        require(isinstance(pack['summary'], str) and 0 < len(pack['summary']) <= 6000, 'Invalid summary.')
        topics = pack['topics']
        require(type(topics) is list and 1 <= len(topics) <= 20 and all(isinstance(t, str) and 0 < len(t) <= 100 for t in topics),
                'Invalid topics.')
        sources = {c['id']: normalize(c['text']) for c in chunks}
        for collection in ('questions', 'cards'):
            require(type(pack[collection]) is list and 3 <= len(pack[collection]) <= 20, 'At least three study items are needed.')
            for item in pack[collection]:
                require(type(item) is dict and item['topic'] in topics, 'Invalid item topic.')
                base_fields={'prompt','topic','options','correct_index','difficulty','hints','explanation','source_chunk_id','evidence_quote'} if collection=='questions' else {'front','back','topic','source_chunk_id','evidence_quote'}
                stored_fields=base_fields|({'id'} if collection=='questions' else {'id','document_id','due_at','step','review_count'})
                require(set(item) in (base_fields,stored_fields),'Unexpected study item fields.')
                source_id, quote = item['source_chunk_id'], item['evidence_quote']
                require(source_id in sources and isinstance(quote, str) and 12 <= len(quote) <= 1500
                        and normalize(quote) in sources[source_id], 'Generated evidence must quote the uploaded source.')
                if collection == 'questions':
                    require(isinstance(item['prompt'], str) and 10 <= len(item['prompt']) <= 2000, 'Invalid question.')
                    opts = item['options']
                    require(type(opts) is list and len(opts) == 4 and all(isinstance(o, str) and 0 < len(o) <= 800 for o in opts)
                            and len({normalize(o).lower() for o in opts}) == 4, 'Questions need four distinct options.')
                    require(type(item['correct_index']) is int and 0 <= item['correct_index'] < 4, 'Invalid answer key.')
                    require(item['difficulty'] in ('easy', 'medium', 'hard'), 'Invalid difficulty.')
                    require(type(item['hints']) is list and len(item['hints']) == 2
                            and all(isinstance(h, str) and 0 < len(h) <= 1000 for h in item['hints']), 'Two hints required.')
                    require(isinstance(item['explanation'], str) and 0 < len(item['explanation']) <= 3000, 'Invalid explanation.')
                else:
                    require(all(isinstance(item[k], str) and 0 < len(item[k]) <= 3000 for k in ('front', 'back')), 'Invalid flashcard.')
    except (KeyError, TypeError, AttributeError) as exc:
        raise DomainError('invalid_content', 'Malformed generated study content.') from exc
    from content_quality import assess_pack
    assess_pack(pack,chunks,'local' if all(q['prompt'].startswith('Complete this statement from your notes:') for q in pack['questions']) else 'gemini')
    return pack


def build_pack(chunks, count=6, difficulty='mixed', use_ai=True, generator=None):
    require(type(count) is int and 3 <= count <= 10, 'Choose 3–10 questions.')
    require(difficulty in ('mixed', 'easy', 'medium', 'hard'), 'Invalid difficulty preference.')
    failed=False
    if use_ai:
        try:
            pack=validate_pack((generator or generate)(chunks,count,difficulty),chunks)
            if generator is None:
                from ai_provider import review_generated
                review_generated(pack,chunks); pack['_automated_review']='passed'
            return pack,'gemini',f'Gemini created {len(pack["questions"])} of {count} requested questions. Source references checked; automated review is fallible and is not authored review.'
        except (ProviderError,DomainError,ValueError,TypeError,KeyError,TimeoutError): failed=True
    try: pack=validate_pack(local_pack(chunks,count),chunks)
    except DomainError:
        if failed:
            raise DomainError('generation_failed','AI generation failed and local recall could not make three valid questions. Your source preview is kept. Add fuller explanatory notes or retry generation.') from None
        raise
    return pack,'local',('AI generation failed. ' if failed else '')+f'Local recall created {len(pack["questions"])} of {count} requested questions. Recall difficulty; requested {difficulty} is not supported locally. Source-checked keys, no semantic review.'


def add_document(state, title, filename, payload, count=6, difficulty='mixed', use_ai=True, now=None, generator=None, source_ids=None, extracted=None):
    now = now or clock()
    require(isinstance(title, str) and 1 <= len(title.strip()) <= 100, 'Give this material a title of 1–100 characters.')
    if extracted is None:text,chunks=extract_upload(filename,payload)
    else:
        from content_quality import validate_extracted
        text,chunks=extracted;validate_extracted(text,chunks)
    digest = hashlib.sha256(normalize(text).encode('utf-8')).hexdigest()[:24]
    if any(d['id'] == digest for d in state['documents']):
        return deepcopy(state), digest, 'This material is already in your library; existing progress was preserved.'
    require(len(state['documents']) < 20, 'This workspace supports at most 20 documents. Export and start a new workspace.')
    require(len(export_state(state).encode('utf-8'))+len(text.encode('utf-8'))<=MAX_STATE,'There is not enough workspace capacity for this source. Export and start a new workspace before generation.')
    selected=select_chunks(chunks,source_ids)
    pack, mode, message = build_pack(selected, count, difficulty, use_ai, generator)
    updated = deepcopy(state)
    document = {'id': digest, 'title': title.strip(), 'filename': Path(filename).name[:150],
                'text': text, 'chunks': chunks, 'summary': pack['summary'], 'topics': pack['topics'],
                'questions': [], 'mode': mode, 'created_at': stamp(now)}
    for i, q in enumerate(pack['questions']):
        document['questions'].append({**q, 'id': digest + '_q' + str(i + 1)})
    updated['documents'].append(document)
    for i, card in enumerate(pack['cards']):
        updated['cards'].append({**card, 'id': digest + '_c' + str(i + 1), 'document_id': digest,
                                'due_at': stamp(now), 'step': 0, 'review_count': 0})
    from schema_v6 import register_pack
    register_pack(updated, document, count, difficulty,selected,__import__('content_quality').assess_pack(pack,selected,mode))
    return updated, digest, message


def get_document(state, document_id):
    document = next((d for d in state['documents'] if d['id'] == document_id), None)
    require(document is not None, 'Choose a document from your library.')
    return document


def get_question(state, question_id):
    for d in state['documents']:
        for q in d['questions']:
            if q['id'] == question_id:
                return q
    raise DomainError('invalid_input', 'Unknown study question.')


def topic_stats(state, document_id=None):
    questions = {q['id']: q for d in state['documents'] if document_id is None or d['id'] == document_id for q in d['questions']}
    stats = {q['topic']: {'topic': q['topic'], 'attempted': 0, 'correct': 0, 'assisted': 0} for q in questions.values()}
    seen=set()
    independent={qid for v in state['pack_versions'] if v['kind']=='independent' for qid in v['question_ids']}
    for a in state['attempts']:
        if a['question_id'] not in questions or a['question_id'] in state.get('item_status',{}) or a['question_id'] in independent:continue
        q=questions[a['question_id']]
        did=next(d['id'] for d in state['documents'] if any(x['id']==q['id'] for x in d['questions']))
        family=(did,normalize(q['prompt']).casefold())
        if family in seen:continue
        seen.add(family);row=stats[q['topic']]
        row['attempted']+=1;row['correct']+=int(a['correct']);row['assisted']+=int(a['hint_count']>0)
    for row in stats.values():
        row['accuracy'] = row['correct'] / row['attempted'] if row['attempted'] else None
    return list(stats.values())


def start_quiz(state, document_id, count=5, adaptive=True, now=None, topic=None):
    document = get_document(state, document_id)
    require(type(count) is int and 1 <= count <= 10, 'Invalid quiz length.')
    active = next((q for q in state['quizzes'] if q['document_id'] == document_id and not q['completed']), None)
    if active:
        return deepcopy(state), active['id']
    updated = deepcopy(state)
    stats = {s['topic']: s for s in topic_stats(state, document_id)}
    seen = Counter(a['question_id'] for a in state['attempts'])
    active=next((v for v in state['pack_versions'] if v['id']==state['material_meta'][document_id]['active_pack']),None)
    questions = [q for q in document['questions'] if (active is None or q['id'] in active['question_ids']) and q['id'] not in state['item_status']]
    if active and active['kind']=='independent':
        exposed={e['item_id'] for e in state['activity_events'] if e['kind']=='present'}
        questions=[q for q in questions if q['id'] not in exposed and not seen[q['id']]]
    require(questions,'No undisputed questions remain in the active pack. Regenerate from Library or review the source.')
    if topic is not None:
        require(topic in document['topics'],'Unknown source-local topic.')
        questions=[q for q in questions if q['topic']==topic]
        require(questions,'No available questions for this topic. Build a new pack version in Library.')
    if adaptive:
        questions.sort(key=lambda q: (stats[q['topic']]['accuracy'] if stats[q['topic']]['accuracy'] is not None else -0.1,
                                      seen[q['id']], q['id']))
        # Always use unattempted items before repeating any question.
        questions.sort(key=lambda q: seen[q['id']] > 0)
    else:
        random.Random(len(state['quizzes'])).shuffle(questions)
    quiz = {'id': str(uuid4()), 'document_id': document_id, 'question_ids': [q['id'] for q in questions[:count]],
            'completed': False, 'created_at': stamp(now or clock())}
    updated['quizzes'].append(quiz)
    from study_flow import record_presentations
    updated=record_presentations(updated,quiz['id'],now)
    return updated, quiz['id']


def answer_question(state, quiz_id, question_id, selected_index, hint_count, token, now=None):
    existing=next((a for a in state['attempts'] if a['id']==token),None)
    if existing:
        require((existing['quiz_id'],existing['question_id'],existing['selected_index'],existing['hint_count'])==(quiz_id,question_id,selected_index,hint_count),'Submission token was reused with different content.')
        return deepcopy(state)
    quiz = next((q for q in state['quizzes'] if q['id'] == quiz_id), None)
    require(quiz is not None and not quiz['completed'], 'This quiz has already finished.', 'invalid_transition')
    require(question_id in quiz['question_ids'], 'This question is not in the current quiz.')
    remaining = [qid for qid in quiz['question_ids'] if not any(a['quiz_id'] == quiz_id and a['question_id'] == qid for a in state['attempts'])]
    require(remaining and remaining[0] == question_id, 'Continue with the current unanswered question.', 'invalid_transition')
    require(type(selected_index) is int and 0 <= selected_index < 4, 'Select an answer first.')
    require(type(hint_count) is int and 0 <= hint_count <= 2, 'Invalid hint count.')
    version=next((v for v in state['pack_versions'] if question_id in v['question_ids']),None)
    if version and version['kind']=='independent':
        require(any(e['kind']=='present' and e['activity_id']==quiz_id and e['item_id']==question_id for e in state['activity_events']),'Save presentation before answering an independent item.')
    require(isinstance(token, str) and 0 < len(token) <= 100, 'Invalid submission token.')
    updated = deepcopy(state)
    q = get_question(state, question_id)
    updated['attempts'].append({'id': token, 'quiz_id': quiz_id, 'question_id': question_id,
                                'selected_index': selected_index, 'correct': selected_index == q['correct_index'],
                                'hint_count': hint_count, 'answered_at': stamp(now or clock())})
    if len(remaining) == 1:
        next(r for r in updated['quizzes'] if r['id'] == quiz_id)['completed'] = True
    return updated


def grade_card(state, card_id, rating, token, now=None):
    now = now or clock()
    existing=next((r for r in state['reviews'] if r['id']==token),None)
    if existing:
        require((existing['card_id'],existing['rating'])==(card_id,rating),'Rating token was reused with different content.')
        return deepcopy(state)
    card = next((c for c in state['cards'] if c['id'] == card_id), None)
    require(card is not None, 'Unknown revision card.')
    require(now >= datetime.fromisoformat(card['due_at']), 'This card is a preview; it is not due yet.', 'invalid_transition')
    require(rating in ('Again', 'Hard', 'Good', 'Easy'), 'Choose a recall rating.')
    updated = deepcopy(state)
    c = next(c for c in updated['cards'] if c['id'] == card_id)
    c['step'],c['due_at']=next_card_schedule(c['step'],rating,now)
    c['review_count'] += 1
    updated['reviews'].append({'id': token, 'card_id': card_id, 'rating': rating, 'reviewed_at': stamp(now)})
    return updated


def next_card_schedule(step,rating,now):
    require(rating in ('Again','Hard','Good','Easy'),'Choose a recall rating.')
    if rating=='Again':step=0;interval=timedelta(minutes=10)
    elif rating=='Hard':interval=timedelta(days=1)
    else:
        index=min(step+(1 if rating=='Easy' else 0),3)
        interval=timedelta(days=[1,3,7,14][index]);step=min(index+1,3)
    return step,stamp(now+interval)


def recommendations(state, now=None):
    now = now or clock()
    if not state['documents']:
        return [('Upload your first notes', 'Library', 'Start with a PDF, text file, or pasted notes.')]
    result = []
    due = sum(datetime.fromisoformat(c['due_at']) <= now for c in state['cards'])
    if due:
        result.append((f'Review {due} due cards', 'Flash Cards', 'Retrieve before you reread.'))
    weak = sorted((r for r in topic_stats(state) if r['attempted'] and r['accuracy'] < .7), key=lambda r: r['accuracy'])
    if weak:
        result.append(('Practise ' + weak[0]['topic'], 'Quiz', 'Based on your first responses, not a mastery estimate.'))
    if any(not q['completed'] for q in state['quizzes']):
        result.append(('Continue your unfinished quiz', 'Quiz', 'Your submitted answers are saved.'))
    result.append(('Build understanding with a new quiz', 'Quiz', 'Unseen questions first; weak topics get priority.'))
    return result[:3]


def export_state(state):
    return json.dumps(state, ensure_ascii=False, indent=2)


def validate_state(state):
    """Validate persistence references and recompute grading invariants; no credentials allowed."""
    try:
        require(type(state) is dict and set(state) == set(new_state())
                and type(state['schema_version']) is int and state['schema_version'] == 6, 'Invalid study backup version.')
        from schema_v6 import validate_extensions
        validate_extensions(state)
        from nlm import validate_progress
        validate_progress(state['nlm'])
        require(all(type(state[k]) is list for k in ('documents', 'quizzes', 'attempts', 'cards', 'reviews')), 'Invalid collections.')
        require(len(state['documents']) <= 20 and len(state['attempts']) <= 10000, 'Backup is too large.')
        ids = set()
        qmap, dmap = {}, {}
        def identity(item):
            require(isinstance(item['id'], str) and 0 < len(item['id']) <= 100 and item['id'] not in ids, 'Duplicate or invalid ID.')
            ids.add(item['id'])
        def date(value):
            require(isinstance(value, str) and len(value) <= 64, 'Invalid timestamp.')
            dt = datetime.fromisoformat(value)
            require(dt.tzinfo is not None and dt.utcoffset() is not None, 'Timestamp must have a timezone.')
        for d in state['documents']:
            require(set(d) == {'id', 'title', 'filename', 'text', 'chunks', 'summary', 'topics', 'questions', 'mode', 'created_at'}, 'Invalid document fields.')
            identity(d); date(d['created_at'])
            require(isinstance(d['title'], str) and 0 < len(d['title']) <= 100 and isinstance(d['filename'], str)
                    and isinstance(d['text'], str) and 80 <= len(d['text']) <= MAX_TEXT and d['mode'] in ('local', 'gemini'), 'Invalid document.')
            require(type(d['chunks']) is list and 0 < len(d['chunks']) <= 200, 'Invalid sources.')
            cids = set()
            for c in d['chunks']:
                require(set(c) == {'id', 'text', 'page', 'section'} and isinstance(c['id'], str) and c['id'] not in cids,
                        'Invalid source reference.')
                cids.add(c['id'])
                require(isinstance(c['text'], str) and c['text'] and normalize(c['text']) in normalize(d['text'])
                        and isinstance(c['section'], str) and 0 < len(c['section']) <= 100
                        and (c['page'] is None or type(c['page']) is int and 1 <= c['page'] <= 60), 'Invalid source chunk.')
            cards = [c for c in state['cards'] if c.get('document_id') == d['id']]
            versions=[v for v in state['pack_versions'] if v['document_id']==d['id']]
            require(versions,'Missing pack descriptor.')
            require(set(q['id'] for q in d['questions'])=={qid for v in versions for qid in v['question_ids']},'Unversioned question.')
            require(set(c['id'] for c in cards)=={cid for v in versions for cid in v['card_ids']},'Unversioned card.')
            for v in versions:
                validate_pack({'summary':v['summary'],'topics':v['topics'],
                    'questions':[q for q in d['questions'] if q['id'] in v['question_ids']],
                    'cards':[c for c in cards if c['id'] in v['card_ids']]},d['chunks'])
            for q in d['questions']:
                require(set(q) == {'id', 'prompt', 'topic', 'options', 'correct_index', 'difficulty', 'hints', 'explanation',
                                   'source_chunk_id', 'evidence_quote'}, 'Invalid question fields.')
                identity(q); qmap[q['id']] = (q, d['id'])
            dmap[d['id']] = d
        quizzes = {}
        for q in state['quizzes']:
            require(set(q) == {'id', 'document_id', 'question_ids', 'completed', 'created_at'}, 'Invalid quiz fields.')
            identity(q); date(q['created_at'])
            require(q['document_id'] in dmap and type(q['completed']) is bool and type(q['question_ids']) is list
                    and 1 <= len(q['question_ids']) <= 10 and len(set(q['question_ids'])) == len(q['question_ids'])
                    and all(i in qmap and qmap[i][1] == q['document_id'] for i in q['question_ids']), 'Invalid quiz reference.')
            quizzes[q['id']] = q
        pairs = set()
        for a in state['attempts']:
            require(set(a) == {'id', 'quiz_id', 'question_id', 'selected_index', 'correct', 'hint_count', 'answered_at'}, 'Invalid attempt fields.')
            identity(a); date(a['answered_at'])
            require(a['quiz_id'] in quizzes and a['question_id'] in quizzes[a['quiz_id']]['question_ids'], 'Unknown attempt reference.')
            pair = (a['quiz_id'], a['question_id'])
            require(pair not in pairs, 'Duplicate answer.'); pairs.add(pair)
            require(type(a['selected_index']) is int and 0 <= a['selected_index'] < 4
                    and type(a['hint_count']) is int and 0 <= a['hint_count'] <= 2 and type(a['correct']) is bool
                    and a['correct'] == (a['selected_index'] == qmap[a['question_id']][0]['correct_index']), 'Inconsistent grading.')
        for q in quizzes.values():
            answered = [qid for qid in q['question_ids'] if (q['id'], qid) in pairs]
            require(answered == q['question_ids'][:len(answered)] and q['completed'] == (len(answered) == len(q['question_ids'])),
                    'Inconsistent quiz completion.')
        cardmap = {}
        for c in state['cards']:
            require(set(c) == {'id', 'front', 'back', 'topic', 'source_chunk_id', 'evidence_quote', 'document_id',
                              'due_at', 'step', 'review_count'}, 'Invalid card fields.')
            identity(c); date(c['due_at'])
            require(c['document_id'] in dmap and type(c['step']) is int and 0 <= c['step'] <= 3
                    and type(c['review_count']) is int and c['review_count'] >= 0, 'Invalid card schedule.')
            cardmap[c['id']] = c
        counts = Counter()
        for r in state['reviews']:
            require(set(r) == {'id', 'card_id', 'rating', 'reviewed_at'}, 'Invalid review fields.')
            identity(r); date(r['reviewed_at'])
            require(r['card_id'] in cardmap and r['rating'] in ('Again', 'Hard', 'Good', 'Easy'), 'Invalid review.')
            counts[r['card_id']] += 1
        require(all(c['review_count'] == counts[c['id']] for c in state['cards']), 'Inconsistent review count.')
        schedules={cid:(0,v['created_at']) for v in state['pack_versions'] for cid in v['card_ids']}
        for review in state['reviews']:
            step,due=schedules[review['card_id']];at=datetime.fromisoformat(review['reviewed_at'])
            require(at>=datetime.fromisoformat(due),'A card was reviewed before it was due.')
            schedules[review['card_id']]=next_card_schedule(step,review['rating'],at)
        require(all((c['step'],c['due_at'])==schedules[c['id']] for c in state['cards']),'Inconsistent card schedule.')
        validate_practice_events(state)
        from debugger import validate_progress as validate_debugger
        validate_debugger(state)
    except DomainError as exc:
        raise DomainError('invalid_progress', str(exc)) from None
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError):
        raise DomainError('invalid_progress', 'Malformed study backup. Existing data is unchanged.') from None
    return state


def import_state(text):
    require(isinstance(text, str) and len(text.encode('utf-8')) <= MAX_STATE, 'Backup exceeds 8 MB.', 'invalid_progress')
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        raise DomainError('invalid_progress', 'Choose a valid study backup JSON file.') from None
    return validate_state(migrate_state(data))


def migrate_state(data):
    """Schema 2 -> 3 -> 4 preserves legacy records; new debugger history starts empty."""
    if type(data) is dict and type(data.get('schema_version')) is int and data['schema_version'] == 2:
        require(set(data) == {'schema_version','documents','quizzes','attempts','cards','reviews'},
                'Malformed schema-v2 backup.', 'invalid_progress')
        from nlm import empty_progress
        result = deepcopy(data)
        result.update(schema_version=3, nlm=empty_progress())
        data = result
    if type(data) is dict and type(data.get('schema_version')) is int and data['schema_version'] == 3:
        require(set(data)=={'schema_version','documents','quizzes','attempts','cards','reviews','nlm'},
                'Malformed schema-v3 backup.','invalid_progress')
        from debugger import empty_progress as empty_debugger
        data=deepcopy(data)
        data.update(schema_version=4,debugger=empty_debugger())
    if type(data) is dict and type(data.get('schema_version')) is int and data['schema_version']==4:
        require(set(data)=={'schema_version','documents','quizzes','attempts','cards','reviews','nlm','debugger'},
                'Malformed schema-v4 backup.','invalid_progress')
        data=deepcopy(data)
        data.update(schema_version=5,practice_events=[])
    if type(data) is dict and data.get('schema_version') == 5:
        from schema_v6 import upgrade_v5
        data = upgrade_v5(data)
    return data


def save_state(state, path=None):
    """Compatibility CAS adapter; callers must retain the returned canonical state."""
    from storage import commit_snapshot
    result = commit_snapshot(Path(path) if path else STATE_PATH, state, state)
    if result.status not in ('committed', 'already_applied'):
        raise DomainError('storage_' + result.status, result.message)
    return result.state


def load_state(path=None):
    from storage import read_workspace
    result = read_workspace(Path(path) if path else STATE_PATH)
    if result.status != 'ready':
        raise DomainError(result.code, 'Your saved workspace could not be opened. The file has been kept.')
    return result.state


def practice_view(state, quiz_id, question_id):
    first=next((a for a in state['attempts'] if a['quiz_id']==quiz_id and a['question_id']==question_id),None)
    require(first is not None, 'Answer the question first.')
    events=[e for e in state['practice_events'] if e['quiz_id']==quiz_id and e['question_id']==question_id]
    v=dict(revision=0, retries=[], hints=0 if first['correct'] else max(1,first['hint_count']), solution=first['correct'], done=first['correct'])
    for e in events:
        require(not v['done'], 'Support already completed.')
        if e['action']=='retry':
            require(not v['solution'] and type(e['value']) is int and 0<=e['value']<4, 'Choose a retry answer.')
            correct=e['value']==get_question(state,question_id)['correct_index']
            v['retries'].append(dict(correct=correct,selected_index=e['value'],at=e['at'],id=e['id'],hints=v['hints']))
            if correct: v['solution']=True
            elif len(v['retries'])>=2: v['solution']=True
            else: v['hints']=2
        elif e['action']=='solution':
            require(e['value'] is None and not v['solution'],'Solution already revealed.')
            v['solution']=True
        elif e['action']=='finish':
            require(e['value'] is None and v['solution'],'Review the explanation first.')
            v['done']=True
        else: raise DomainError('invalid_transition','Unknown support action.')
        v['revision']+=1
    return v


def practice_event(state,quiz_id,question_id,action,value,token,revision,now=None):
    existing=next((e for e in state['practice_events'] if e['id']==token),None)
    if existing:
        require((existing['quiz_id'],existing['question_id'],existing['action'],existing['value'],existing['revision'])==(quiz_id,question_id,action,value,revision),'Support token was reused with different content.')
        return deepcopy(state)
    v=practice_view(state,quiz_id,question_id)
    require(type(revision) is int and revision==v['revision'],'This support step changed. Refresh and retry.','invalid_transition')
    require(type(token) is str and 0<len(token)<=100,'Invalid support token.')
    result=deepcopy(state)
    result['practice_events'].append(dict(id=token,quiz_id=quiz_id,question_id=question_id,
                                        action=action,value=value,at=stamp(now or clock()),revision=revision))
    validate_practice_events(result)
    return result


def validate_practice_events(state):
    events=state['practice_events']
    require(type(events) is list and len(events)<=30000,'Invalid support events.')
    replay=dict(state); replay['practice_events']=[]
    grouped=defaultdict(list)
    ids={r['id'] for key in ('documents','quizzes','attempts','cards','reviews') for r in state[key]}
    ids.update(q['id'] for d in state['documents'] for q in d['questions'])
    for e in events:
        require(type(e) is dict and set(e)=={'id','quiz_id','question_id','action','value','at','revision'},'Invalid support fields.')
        require(type(e['id']) is str and 0<len(e['id'])<=100 and e['id'] not in ids,'Duplicate support token.')
        ids.add(e['id'])
        pair=(e['quiz_id'],e['question_id'])
        replay['practice_events']=grouped[pair]
        v=practice_view(replay,e['quiz_id'],e['question_id'])
        require(type(e['revision']) is int and e['revision']==v['revision'],'Invalid support revision.')
        at=datetime.fromisoformat(e['at']); first=next(a for a in state['attempts'] if a['quiz_id']==e['quiz_id'] and a['question_id']==e['question_id'])
        previous=[r for r in replay['practice_events'] if r['quiz_id']==e['quiz_id'] and r['question_id']==e['question_id']]
        require(at.tzinfo is not None and at>=datetime.fromisoformat(previous[-1]['at'] if previous else first['answered_at']),'Invalid support date.')
        replay['practice_events'].append(e)
        practice_view(replay,e['quiz_id'],e['question_id'])


def regenerate_document(state,document_id,count=6,difficulty='mixed',use_ai=True,now=None,generator=None,source_ids=None):
    """Append a pack version; historical questions, grades and schedules remain intact."""
    doc=get_document(state,document_id)
    require(len(state['pack_versions'])<200,'Saved pack capacity reached. Export and start another workspace.')
    selected=select_chunks(doc['chunks'],source_ids)
    pack,mode,message=build_pack(selected,count,difficulty,use_ai,generator)
    result=deepcopy(state); target=get_document(result,document_id)
    version=max(v['version'] for v in state['pack_versions'] if v['document_id']==document_id)+1
    pid=f'{document_id}:v{version}'; nonce=uuid4().hex[:12]
    questions=[dict(q,id=f'{document_id}_v{version}_{nonce}_q{i}') for i,q in enumerate(pack['questions'])]
    cards=[dict(c,id=f'{document_id}_v{version}_{nonce}_c{i}',document_id=document_id,due_at=stamp(now or clock()),step=0,review_count=0) for i,c in enumerate(pack['cards'])]
    target['questions'].extend(questions); target['topics']=list(dict.fromkeys(target['topics']+pack['topics']))
    result['cards'].extend(cards)
    result['pack_versions'].append(dict(id=pid,document_id=document_id,version=version,mode=mode,
        summary=pack['summary'],topics=pack['topics'],question_ids=[q['id'] for q in questions],card_ids=[c['id'] for c in cards],
        kind='ordinary',origin_item_id=None,source_ids=list(dict.fromkeys(q['source_chunk_id'] for q in questions)),selected_source_ids=[c['id'] for c in selected],quality=__import__('content_quality').assess_pack(pack,selected,mode),requested_count=count,requested_difficulty=difficulty,created_at=stamp(now or clock())))
    result['material_meta'][document_id]['active_pack']=pid
    validate_state(result)
    return result,message


def select_chunks(chunks,source_ids=None):
    if source_ids is None:return chunks
    require(type(source_ids) is list and source_ids and len(source_ids)==len(set(source_ids)) and set(source_ids)<={c['id'] for c in chunks},'Select one or more valid source sections.')
    return [c for c in chunks if c['id'] in source_ids]
