"""Live provider smoke with synthetic notes only; never reads learner checkpoints."""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'src' / 'phoenix'))
from ai_provider import settings,connection_check,ProviderError
from ledger import clock
from study import new_state,add_document

NOTES=('Photosynthesis converts light energy into chemical energy stored in glucose. '
       'Chlorophyll is a pigment that absorbs light for photosynthesis. '
       'Cellular respiration releases usable energy from glucose. '
       'Mitochondria are sites of cellular respiration in eukaryotic cells. '
       'Ribosomes assemble proteins from amino acids using genetic instructions. '
       'Osmosis is the movement of water across a selectively permeable membrane.')


def main():
    config=settings();result=dict(at=clock().isoformat(),model=config.model,source='synthetic biology fixture',configured_model=False,status='blocked')
    try:
        result['configured_model']=connection_check()
        state,mid,message=add_document(new_state(),'Synthetic smoke','synthetic.txt',NOTES.encode(),3,use_ai=True)
        version=state['pack_versions'][0]
        result.update(status='passed' if version['mode']=='gemini' else 'blocked',mode=version['mode'],questions=len(version['question_ids']),cards=len(version['card_ids']),selected_sources=version['selected_source_ids'],quality=version['quality'])
    except ProviderError as exc:result['reason']=str(exc)
    except Exception:result['reason']='Generation or validation failed; no learner workspace was changed.'
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='passed' else 2

if __name__=='__main__':raise SystemExit(main())
