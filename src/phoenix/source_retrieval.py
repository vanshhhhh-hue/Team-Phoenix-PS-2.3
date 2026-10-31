"""Small local retrieval boundary: evidence relevance is not source correctness."""
import re
from engine import require


def retrieve_repair_sources(state,document_id,query,limit=3):
    require(type(limit) is int and 1<=limit<=3,'Invalid source limit.')
    d=next((d for d in state['documents'] if d['id']==document_id),None)
    require(d is not None,'Unknown study material.')
    terms=set(re.findall(r'[a-z]{3,}',query.lower()))-{'the','and','for','with','what','which','your','this','that'}
    ranked=[]
    for c in d['chunks']:
        score=len(terms & set(re.findall(r'[a-z]{3,}',c['text'].lower())))
        if score:
            ranked.append((score,c))
    ranked.sort(key=lambda v:(-v[0],v[1]['id']))
    return [dict(document_id=d['id'],chunk_id=c['id'],page=c['page'],section=c['section'],
                 quote=c['text'],relevance='keyword overlap; not semantic verification') for _,c in ranked[:limit]]
