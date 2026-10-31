"""Rebuildable evidence summaries, not diagnosis probabilities or personality labels."""
from datetime import datetime, timedelta
from debugger_content import HYPOTHESES
from learning_events import normalize_evidence


def build_learner_summary(state, learner, now, episode_id=None):
    events=normalize_evidence(state,learner,before=now)
    history=state['debugger']['history'].get(learner,True)
    selected=events if history else [r for r in events if r['episode']==episode_id]
    recent=[r for r in selected if datetime.fromisoformat(r['at'])>=now-timedelta(days=30)]
    result={}
    for hid,label in HYPOTHESES.items():
        eligible=[r for r in recent if hid in r['effects'] and not r['helped'] and not r['repeat']
                  and r['role'] in ('primary','probe')][-10:]
        support=[r for r in eligible if r['effects'][hid]=='supports']
        against=[r for r in eligible if r['effects'][hid]=='contradicts']
        status='insufficient'
        if support and against: status='mixed_evidence'
        elif len({r['family'] for r in support})>=2 and any(r['role']=='probe' for r in support): status='supported_candidate'
        elif support: status='candidate'
        elif against: status='not_currently_supported'
        elif any(hid in r['effects'] for r in selected): status='needs_recheck'
        result[hid]=dict(label=label,status=status,support=[r['id'] for r in support],
                         contradict=[r['id'] for r in against],families=len({r['family'] for r in support}))
    outcomes={}
    for r in selected:
        if r['intervention'] and r['role'] in ('follow_up','transfer','delayed') and not r['repeat'] and not r['helped']:
            key=r['skill']+' / '+r['intervention']
            row=outcomes.setdefault(key,dict(attempted=0,passed=0,delayed=0,delayed_passed=0))
            row['attempted']+=1; row['passed']+=int(r['correct'])
            if r['role']=='delayed': row['delayed']+=1; row['delayed_passed']+=int(r['correct'])
    return dict(history_enabled=history,hypotheses=result,events=selected,support_outcomes=outcomes)
