"""Bounded explainable selection. No fitted probabilities or generated decisions."""
from debugger_content import QUESTIONS, TOPICS, POLICY, VERSION
from learner_model import build_learner_summary
from learning_events import exposed_questions


def choose_next_action(state, episode, view, now):
    summary=build_learner_summary(state,episode['learner'],now,episode['id'])
    used=exposed_questions(state,episode['learner'])
    phase=view['phase']; topic=episode['topic']
    candidates=[q for q in QUESTIONS.values() if q['topic']==topic and q['role']==phase
                and (q['id'] not in used or phase in ('primary','teach'))]
    reason='fresh_'+phase
    if phase=='primary': candidates=[QUESTIONS[TOPICS[topic]['primary']]]
    if phase=='probe':
        hs=summary['hypotheses']
        if topic=='mass':
            # Prior demonstrated correct law selection makes a calculation probe more informative.
            order=['mass-division-probe','mass-law-probe','mass-ratio-probe'] if hs['mass_rule']['contradict'] else ['mass-law-probe','mass-division-probe','mass-ratio-probe']
        else:
            order=['motion-change-probe','motion-direction-probe','motion-force-probe'] if hs['motion_force']['contradict'] else ['motion-force-probe','motion-change-probe','motion-direction-probe']
        candidates.sort(key=lambda q:order.index(q['id']))
        reason='discriminate_causes_with_history' if summary['history_enabled'] else 'discriminate_current_attempt'
    refs=[]
    for hid in TOPICS[topic]['hypotheses']:
        refs.extend(summary['hypotheses'][hid]['support']+summary['hypotheses'][hid]['contradict'])
    return dict(question_id=candidates[0]['id'] if candidates else None,reason_code=reason,
                evidence_ids=sorted(set(refs)),policy_version=POLICY,content_version=VERSION)


def choose_repair(state,episode,now):
    summary=build_learner_summary(state,episode['learner'],now,episode['id'])
    hs=summary['hypotheses']; topic=episode['topic']
    supported=[h for h in TOPICS[topic]['hypotheses'] if hs[h]['status']=='supported_candidate']
    if supported:
        chosen=max(supported,key=lambda h:len(hs[h]['support']))
        reason='supported_candidate'
    elif topic=='mass' and hs['mass_rule']['contradict'] and hs['execution']['support']:
        chosen='execution'; reason='correct_relation_execution_needs_check'
    elif topic=='motion' and hs['motion_force']['contradict'] and hs['velocity_acceleration']['support']:
        chosen='velocity_acceleration'; reason='forces_identified_quantity_needs_check'
    else: chosen='unclear'; reason='insufficient_or_conflicting_evidence'
    refs=[]
    for h in TOPICS[topic]['hypotheses']: refs+=hs[h]['support']+hs[h]['contradict']
    return dict(hypothesis=chosen,reason_code=reason,evidence_ids=sorted(set(refs)),
                policy_version=POLICY,content_version=VERSION)
