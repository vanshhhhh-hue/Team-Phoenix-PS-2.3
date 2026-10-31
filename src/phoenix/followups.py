"""Bounded generated changed-situation candidates; no learner history is sent."""
from engine import require,DomainError


def build_followup(state,document_id,origin_item_id,count=3,now=None,generator=None,reviewer=None):
    """Generated candidate checks pass operational novelty/review gates, never human review."""
    from ai_provider import generate,review_generated,ProviderError
    from content_quality import assess_pack
    from study import get_document,get_question,regenerate_document,validate_pack,normalize
    from copy import deepcopy
    import re
    doc=get_document(state,document_id);origin=get_question(state,origin_item_id)
    require(origin_item_id in {q['id'] for q in doc['questions']},'Origin belongs to another source.')
    require(any(a['question_id']==origin_item_id and not a['correct'] for a in state['attempts']),'Follow-up needs a saved originating mistake.')
    origin_data={k:origin[k] for k in ('prompt','topic','options','correct_index','explanation','evidence_quote')}
    source_ids={origin['source_chunk_id']}
    chunks=[c for c in doc['chunks'] if c['id'] in source_ids]
    try:
        pack=validate_pack((generator or generate)(chunks,count,'medium',followup_origin=origin_data),chunks)
        require((reviewer or review_generated)(pack,chunks,origin=origin_data) is True,'Changed-example review did not pass.')
        def words(text):return set(re.findall(r'[a-z0-9]+',text.casefold()))
        existing=[words(q['prompt']) for q in doc['questions']]
        for q in pack['questions']:
            tokens=words(q['prompt'])
            require(all(len(tokens&old)/max(1,len(tokens|old))<.65 for old in existing),'Candidate is too similar to an existing question.')
            require(q['topic']==origin['topic'],'Candidate assesses another source-local topic.')
            existing.append(tokens)
        pack['_automated_review']='passed'
    except (ProviderError,DomainError,ValueError,TypeError,KeyError,TimeoutError):
        # Deliberately fail closed; no invalid or fallback independent pack becomes active.
        raise DomainError('followup_unavailable','A sufficiently novel, source-supported generated check was unavailable. Your existing work is preserved. Use ordinary practice or add richer notes.') from None
    result,message=regenerate_document(state,document_id,count,'medium',True,now,
        generator=lambda *args:deepcopy(pack),source_ids=list(source_ids))
    version=result['pack_versions'][-1];version['kind']='independent';version['origin_item_id']=origin_item_id
    from study import validate_state
    validate_state(result)
    return result,'Generated changed-situation checks saved. Source and automated review passed; this is fallible generated content, not authored equivalence.'
