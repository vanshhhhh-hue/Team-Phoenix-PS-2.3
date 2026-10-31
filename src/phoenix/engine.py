"""Bounded algebra functions and validated authored content. No expression parsing."""
import json
from pathlib import Path

FAMILIES = ('distribution', 'square', 'negative')
SEARCH_VALUES = (0, 1, -1, 2, -2, 3, -3)
RULES = {
    'distribution': ('multiply_first_only', 'multiply_every_term'),
    'square': ('square_terms_only', 'include_cross_term'),
    'negative': ('negate_first_only', 'negate_every_term'),
}


class DomainError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def require(condition, message, code='invalid_input'):
    if not condition:
        raise DomainError(code, message)


def bounded(value):
    return type(value) is int and -5 <= value <= 5


def evaluate(family_id, rule_kind, parameters, x):
    require(family_id in FAMILIES, 'Unknown algebra family.')
    require(rule_kind in ('original', 'faulty', 'correct'), 'Unknown rule kind.')
    require(isinstance(parameters, dict) and bounded(x), 'Use whole numbers from -5 to 5.')
    expected = {'a', 'b'} if family_id == 'distribution' else {'b'}
    require(set(parameters) == expected and all(bounded(v) for v in parameters.values()),
            'Invalid template parameters.')
    b = parameters['b']
    if family_id == 'distribution':
        a = parameters['a']
        return {'original': a * (x + b), 'faulty': a * x + b,
                'correct': a * x + a * b}[rule_kind]
    if family_id == 'square':
        return {'original': (x + b) ** 2, 'faulty': x ** 2 + b ** 2,
                'correct': x ** 2 + 2 * b * x + b ** 2}[rule_kind]
    return {'original': -(x + b), 'faulty': -x + b, 'correct': -x - b}[rule_kind]


def find_counterexample(family_id, parameters):
    for x in SEARCH_VALUES:
        original = evaluate(family_id, 'original', parameters, x)
        faulty = evaluate(family_id, 'faulty', parameters, x)
        if original != faulty:
            return dict(x=x, original_value=original, rewritten_value=faulty)
    return None


def validate_content(content):
    try:
        require(type(content) is dict and type(content['schema_version']) is int
                and content['schema_version'] == 1, 'Unsupported content version.')
        packs, questions, hints = content['packs'], content['questions'], content['hints']
        require(all(type(v) is list for v in (packs, questions, hints)), 'Content must use collections.')
        ids = [item['id'] for items in (packs, questions, hints) for item in items]
        require(all(isinstance(i, str) and i for i in ids) and len(set(ids)) == len(ids),
                'Content IDs must be unique.')
        qmap = {q['id']: q for q in questions}
        hmap = {h['id']: h for h in hints}
        for hint in hints:
            require(isinstance(hint['text'], str) and hint['text'], 'Empty hint.')
        for q in questions:
            require(q['role'] in ('diagnostic', 'probe', 'repair', 'transfer', 'delayed'), 'Invalid role.')
            require(isinstance(q['prompt'], str) and q['prompt'], 'Empty prompt.')
            opts = q['options']
            require(type(opts) is list and len(opts) >= 2, 'At least two options are required.')
            oids = [o['id'] for o in opts]
            require(len(set(oids)) == len(oids) and oids.count(q['correct_option_id']) == 1,
                    'Each question needs one unique correct option.')
            require(all(isinstance(o['text'], str) and o['text'] for o in opts), 'Empty option.')
        require(tuple(p['id'] for p in packs) == FAMILIES, 'Expected the three supported families in order.')
        used = set()
        for p in packs:
            fid = p['id']
            require((p['faulty_rule_id'], p['correct_rule_id']) == RULES[fid], 'Unsupported rule ID.')
            require(p['original_template_id'] == fid + '_original', 'Unsupported original template.')
            evaluate(fid, 'original', p['parameters'], 0)
            require(p['parameters']['b'] != 0, 'A nonzero second term is required.')
            if fid == 'distribution':
                require(p['parameters']['a'] not in (0, 1), 'Avoid concealed distribution errors.')
            reasons = p['reason_options']
            require(len(reasons) == 3 and {r['id'] for r in reasons} == {*RULES[fid], 'unsure'},
                    'Reason options must include both rules and unsure.')
            require(all(isinstance(r['text'], str) and r['text'] for r in reasons), 'Empty reason.')
            require(len(p['hint_ids']) == 2 and len(set(p['hint_ids'])) == 2
                    and all(h in hmap for h in p['hint_ids']), 'Two authored hints required.')
            require(isinstance(p['canonical_explanation'], str) and p['canonical_explanation'],
                    'Canonical explanation missing.')
            refs = [(p['diagnostic_question_id'], 'diagnostic'), (p['probe_question_id'], 'probe'),
                    (p['repair_question_id'], 'repair')]
            require(len(p['transfer_question_ids']) == 2 and len(p['delayed_question_ids']) >= 2,
                    'Two transfer and at least two delayed items required.')
            refs += [(q, 'transfer') for q in p['transfer_question_ids']]
            refs += [(q, 'delayed') for q in p['delayed_question_ids']]
            for qid, role in refs:
                require(qid in qmap and qmap[qid]['role'] == role and qid not in used,
                        'Question references must be valid and disjoint.')
                used.add(qid)
            for key in ('original_latex', 'faulty_latex', 'correct_latex', 'faulty_rule_latex',
                        'correct_rule_latex', 'repair_reason'):
                require(isinstance(p[key], str) and p[key], 'Missing display content.')
            require(find_counterexample(fid, p['parameters']) is not None, 'Faulty rule needs a counterexample.')
        require(used == set(qmap), 'Unreferenced questions are not allowed.')
    except (KeyError, TypeError, AttributeError) as exc:
        raise DomainError('invalid_content', 'Malformed authored content.') from exc
    except DomainError as exc:
        raise DomainError('invalid_content', str(exc)) from exc
    return content


def load_packs(path=None):
    path = Path(path) if path else Path(__file__).resolve().parents[2] / 'data' / 'packs.json'
    try:
        return validate_content(json.loads(path.read_text(encoding='utf-8')))
    except (OSError, json.JSONDecodeError) as exc:
        raise DomainError('invalid_content', 'Unable to load the authored content file.') from exc


def pack_by_id(content, family_id):
    for pack in content['packs']:
        if pack['id'] == family_id:
            return pack
    raise DomainError('invalid_input', 'Unknown algebra family.')


def question_by_id(content, question_id):
    for question in content['questions']:
        if question['id'] == question_id:
            return question
    raise DomainError('invalid_input', 'Unknown question.')
