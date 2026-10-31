"""Deterministic quality checks are bounded checks, never a truth guarantee."""
import re
from engine import require


def assess_pack(pack,chunks,mode):
    from study import normalize
    prompts=set()
    for q in pack['questions']:
        prompt=normalize(q['prompt']).casefold()
        require(prompt not in prompts,'Repeated questions were rejected.','invalid_content'); prompts.add(prompt)
        key=q['options'][q['correct_index']].strip()
        if len(key)>=5:
            require(not any(re.search(r'(?<!\w)'+re.escape(key)+r'(?!\w)',h,re.I) for h in q['hints']),'A hint exposes the keyed answer.','invalid_content')
        if q['prompt'].startswith('Complete this statement from your notes:\n\n'):
            masked=q['prompt'].split('\n\n',1)[1]
            require(masked.count('____')==1,'Local recall item has an ambiguous blank.','invalid_content')
            reconstructed=masked.replace('____',q['options'][q['correct_index']],1)
            require(normalize(reconstructed).casefold()==normalize(q['evidence_quote']).casefold(),
                'Local answer key does not reconstruct its source statement.','invalid_content')
    return dict(source_references='validated',local_keys='validated' if mode=='local' else 'not independently verified',
                semantic_review=pack.get('_automated_review','not performed'),authored_review=False,question_count=len(pack['questions']),card_count=len(pack['cards']))


def source_preview(filename,payload):
    from study import extract_upload
    text,chunks=extract_upload(filename,payload)
    letters=[c for c in text if c.isalpha()]
    latin=sum(c.isascii() for c in letters)/max(len(letters),1)
    formula=sum(text.count(c) for c in '=∫∑√^')
    warnings=[]
    if latin<.8: warnings.append('Local recall supports English words. This source may require multilingual AI generation; inspect every result.')
    if formula>max(8,len(text)//200): warnings.append('Formula-heavy notes may lose notation during extraction. Check the extracted text; local missing-word recall does not assess derivations.')
    warnings.append('Scanned images, diagrams and unreadable PDF regions are not extracted. Review the text below before building.')
    selected=selected_sources(chunks)
    return dict(text=text,chunks=chunks,warnings=warnings,selected_ids=[c['id'] for c in selected],
                omitted_ids=[c['id'] for c in chunks if c['id'] not in {x['id'] for x in selected}])


def selected_sources(chunks):
    n=min(18,len(chunks))
    indexes=sorted({round(i*(len(chunks)-1)/max(1,n-1)) for i in range(n)})
    return [chunks[i] for i in indexes]


def flag_item(state,item_id,reason,feedback='',now=None):
    from copy import deepcopy
    from ledger import clock,stamp
    require(reason in ('answer seems wrong','ambiguous choices','missing source support','explanation unclear','other'),'Choose a flag reason.')
    require(type(feedback) is str and len(feedback)<=1000,'Keep feedback within 1,000 characters.')
    items={q['id'] for d in state['documents'] for q in d['questions']}|{c['id'] for c in state['cards']}
    require(item_id in items,'Only uploaded study items can be flagged here.')
    result=deepcopy(state)
    result['item_status'][item_id]=dict(status='disputed',reason=reason,feedback=feedback,at=stamp(now or clock()))
    return result


def validate_extracted(text,chunks):
    from study import MAX_TEXT,normalize
    require(type(text) is str and 80<=len(text)<=MAX_TEXT and type(chunks) is list and 1<=len(chunks)<=200,'Invalid extracted draft.')
    seen=set()
    for c in chunks:
        require(type(c) is dict and set(c)=={'id','text','page','section'} and type(c['id']) is str and 0<len(c['id'])<=100 and c['id'] not in seen,'Invalid draft source reference.')
        seen.add(c['id'])
        require(type(c['text']) is str and 0<len(c['text'])<=1400 and normalize(c['text']) in normalize(text) and type(c['section']) is str and 0<len(c['section'])<=100 and (c['page'] is None or type(c['page']) is int and 1<=c['page']<=60),'Invalid extracted draft source.')


def validate_source_draft(draft):
    require(type(draft) is dict and set(draft)=={'title','filename','count','difficulty','text','chunks'},'Invalid source preview fields.')
    require(type(draft['title']) is str and 0<len(draft['title'])<=100 and type(draft['filename']) is str and 0<len(draft['filename'])<=150,'Invalid source preview title.')
    require(type(draft['count']) is int and 3<=draft['count']<=10 and draft['difficulty'] in ('mixed','easy','medium','hard'),'Invalid source preview settings.')
    validate_extracted(draft['text'],draft['chunks'])
