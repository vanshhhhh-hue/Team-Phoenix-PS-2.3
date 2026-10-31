"""Reviewed debugger content v1. Keys and evidence maps never come from an LLM."""
from engine import require

VERSION = 1
POLICY = 'debugger-v1'
SOURCE = 'https://openstax.org/books/university-physics-volume-1/pages/5-2-newtons-first-law'
SECOND_SOURCE = 'https://openstax.org/books/university-physics-volume-1/pages/5-3-newtons-second-law'
HYPOTHESES = {
    'motion_force': 'Motion requires a continuing resultant force',
    'velocity_acceleration': 'Velocity and acceleration are being confused',
    'mass_rule': 'Acceleration is multiplied by mass rather than divided',
    'execution': 'Division or substitution needs support',
}


def item(id, topic, role, prompt, options, correct, family, effects=None, explanation='', representation='text'):
    return dict(id=id, topic=topic, role=role, prompt=prompt, options=options, correct=correct,
                family=family, effects=effects or {}, explanation=explanation, representation=representation)


ITEMS = [
    item('motion-start','motion','primary','A glider moves right on an ideal horizontal air track. After the push ends, its horizontal velocity:',
         ['Remains constant','Gradually becomes zero','Keeps increasing'],0,'glider-release',
         {'1':{'motion_force':'supports'},'2':{'velocity_acceleration':'supports'}},
         'With no horizontal resultant, horizontal acceleration is zero; the initial velocity remains.'),
    item('mass-start','mass','primary','A 2 kg trolley has a 6 N rightward resultant. What is its acceleration?',
         ['12 m/s² right','3 m/s² right','0.33 m/s² right'],1,'force-six-mass-two',
         {'0':{'mass_rule':'supports','execution':'supports'},'2':{'execution':'supports'}},
         'a = F_net/m = 6/2 = 3 m/s² right.'),
    item('motion-force-probe','motion','probe','After release on an ideal horizontal air track, which horizontal interaction remains on the glider?',
         ['A forward force supplied by its velocity','No horizontal interaction','A backward force because it is moving'],1,'horizontal-interactions',
         {'0':{'motion_force':'supports'},'1':{'motion_force':'contradicts'},'2':{'motion_force':'supports'}},
         'Velocity is not an interaction. In this ideal case no horizontal force remains.'),
    item('motion-change-probe','motion','probe','The resultant force is zero. Which statement must hold in an inertial frame?',
         ['Velocity must be zero','Acceleration is zero; velocity may be nonzero','Acceleration points along velocity'],1,'zero-resultant-quantities',
         {'0':{'velocity_acceleration':'supports','motion_force':'supports'},
          '1':{'velocity_acceleration':'contradicts','motion_force':'contradicts'},
          '2':{'velocity_acceleration':'supports'}},
         'Zero resultant implies zero acceleration, not necessarily zero velocity.'),
    item('motion-direction-probe','motion','probe','An object moves right while a leftward resultant acts. Its acceleration points:',
         ['Right','Left','Nowhere, because it is moving'],1,'opposing-acceleration',
         {'0':{'velocity_acceleration':'supports'},'1':{'velocity_acceleration':'contradicts'},'2':{'velocity_acceleration':'supports'}},
         'Acceleration follows the resultant; it need not follow velocity.'),
    item('mass-law-probe','mass','probe','Before substituting numbers, choose the relation for acceleration under a resultant force F and positive mass m.',
         ['a = F × m','a = F / m','a = m / F'],1,'choose-second-law',
         {'0':{'mass_rule':'supports'},'1':{'mass_rule':'contradicts'},'2':{'mass_rule':'supports'}},
         'Newton’s second law is F_net = ma; rearranging gives a = F_net/m.'),
    item('mass-division-probe','mass','probe','For a = 10/5 m/s², evaluate the division.',
         ['50 m/s²','0.5 m/s²','2 m/s²'],2,'division-ten-five',
         {'0':{'execution':'supports'},'1':{'execution':'supports'},'2':{'execution':'contradicts'}},
         '10 divided by 5 is 2.'),
    item('mass-ratio-probe','mass','probe','Two trolleys experience the same nonzero resultant. Trolley B has twice the mass. Its acceleration is:',
         ['Twice A’s acceleration','Half A’s acceleration','The same as A’s'],1,'mass-proportionality',
         {'0':{'mass_rule':'supports'},'1':{'mass_rule':'contradicts'},'2':{'mass_rule':'supports'}},
         'At fixed resultant, acceleration is inversely proportional to positive mass.'),
    item('motion-teach','motion','teach','Complete the explanation: a resultant force changes velocity by producing ____. Existing velocity ____ a continuing resultant.',
         ['acceleration; does not require','velocity; always requires','mass; requires'],0,'motion-teachback',
         explanation='A resultant produces acceleration. Constant velocity is possible with zero resultant.'),
    item('mass-teach','mass','teach','Choose a valid calculation chain for a 3 kg body under a 12 N resultant.',
         ['a = 12 × 3 = 36 m/s²','a = 12/3 = 4 m/s²','a = 3/12 = 0.25 m/s²'],1,'mass-teachback',
         explanation='Divide the resultant in newtons by mass in kilograms.'),
    item('motion-fresh','motion','follow_up','A probe in deep space already moves at 8 m/s. Its resultant stays zero for 4 s. Its final speed is:',
         ['0 m/s','2 m/s','8 m/s'],2,'deep-space-eight',explanation='Zero resultant means zero acceleration, so the speed stays 8 m/s.'),
    item('motion-fresh-2','motion','follow_up','A laboratory cart travels at constant nonzero velocity. Its resultant is:',
         ['Zero','Forward','Backward'],0,'constant-cart',explanation='Constant velocity means acceleration is zero, so resultant force is zero.'),
    item('mass-fresh','mass','follow_up','A 4 kg body has a 20 N leftward resultant. Its acceleration is:',
         ['80 m/s² left','5 m/s² left','5 m/s² right'],1,'twenty-four',explanation='20/4 = 5 m/s², in the direction of the resultant.'),
    item('mass-fresh-2','mass','follow_up','A 6 kg body has an 18 N rightward resultant. Its acceleration is:',
         ['108 m/s² right','3 m/s² right','0.33 m/s² right'],1,'eighteen-six',explanation='18/6 = 3 m/s² right.'),
    item('motion-transfer','motion','transfer','A velocity–time graph is horizontal at −4 m/s for 3 s. The resultant force is:',
         ['Leftward','Zero','Rightward'],1,'negative-horizontal-graph',representation='graph',
         explanation='The slope is zero even though velocity is negative. Acceleration and resultant are zero.'),
    item('motion-transfer-2','motion','transfer','A toy car slides right and slows only after it enters a rough strip. What new horizontal interaction explains this?',
         ['Forward force supplied by motion','Leftward friction','Loss of mass'],1,'rough-strip',representation='scenario',
         explanation='The rough strip exerts friction opposite sliding, giving leftward acceleration.'),
    item('mass-transfer','mass','transfer','A resultant-force versus acceleration graph through the origin has slope 4 kg. At 28 N, acceleration is:',
         ['112 m/s²','7 m/s²','4 m/s²'],1,'force-graph-four',representation='graph',
         explanation='The slope F/a is mass. Thus a = 28/4 = 7 m/s².'),
    item('mass-transfer-2','mass','transfer','A 2 kg cart has forces 9 N right and 3 N left. Its acceleration is:',
         ['6 m/s² right','3 m/s² right','12 m/s² right'],1,'two-force-resultant',representation='diagram',
         explanation='Resultant = 9 − 3 = 6 N right; a = 6/2 = 3 m/s² right.'),
    item('motion-delayed','motion','delayed','An object moves downward at a steady 2 m/s. Its total resultant force is:',
         ['Downward','Zero','Upward'],1,'steady-downward',explanation='Steady velocity implies zero acceleration; total forces balance.'),
    item('motion-delayed-2','motion','delayed','A velocity–time graph is horizontal at +9 m/s. What is acceleration?',
         ['9 m/s²','Zero','It increases'],1,'horizontal-nine',representation='graph',explanation='Acceleration is the slope of velocity versus time: zero.'),
    item('motion-delayed-3','motion','delayed','A moving ice puck has zero horizontal resultant. Over the next second its horizontal velocity:',
         ['Stays unchanged','Must fall to zero','Doubles'],0,'ice-puck-later',explanation='Zero horizontal resultant gives zero horizontal acceleration.'),
    item('mass-delayed','mass','delayed','A 5 kg body experiences a 15 N downward resultant. Its acceleration is:',
         ['75 m/s² down','3 m/s² down','3 m/s² up'],1,'fifteen-five',explanation='15/5 = 3 m/s² in the resultant direction.'),
    item('mass-delayed-2','mass','delayed','A 3 kg object has acceleration 2 m/s² right. Its resultant is:',
         ['6 N right','1.5 N right','6 N left'],0,'inverse-second-law',explanation='F_net = ma = 3 × 2 = 6 N right.'),
    item('mass-delayed-3','mass','delayed','Under a 24 N resultant, an 8 kg object accelerates at:',
         ['192 m/s²','3 m/s²','0.33 m/s²'],1,'twentyfour-eight',explanation='24/8 = 3 m/s².'),
]
QUESTIONS = {q['id']: q for q in ITEMS}
TOPICS = {
    'motion': dict(title='Force, velocity and acceleration', primary='motion-start',
                   hypotheses=['motion_force','velocity_acceleration'], source=SOURCE),
    'mass': dict(title='Resultant, mass and calculation', primary='mass-start',
                 hypotheses=['mass_rule','execution'], source=SECOND_SOURCE),
}
REPAIRS = {
    'motion_force': ('Compare force and motion', 'On an ideal track, zero horizontal force preserves velocity. On a rough track, friction changes velocity. Motion is not a force.'),
    'velocity_acceleration': ('Separate velocity from its change', 'Velocity describes motion. Acceleration describes the rate of change of velocity. A leftward acceleration can act on a right-moving object.'),
    'mass_rule': ('Compare two masses', 'F_net = ma. With the same resultant, a larger mass has smaller acceleration. Rearrange to a = F_net/m before using numbers.'),
    'execution': ('Work through units and division', 'Write a = F_net/m. Substitute numbers with units. Since N = kg·m/s², dividing N by kg gives m/s². Check the division separately.'),
    'unclear': ('Work through a guided example', 'The cause is unclear. Choose the physical quantity, identify the resultant, select the law, and only then calculate. Ask for a different explanation if needed.'),
}


def validate_content():
    require(len(QUESTIONS)==len(ITEMS), 'Duplicate debugger question.')
    for q in ITEMS:
        require(q['topic'] in TOPICS and q['role'] in ('primary','probe','teach','follow_up','transfer','delayed')
                and type(q['correct']) is int and 0 <= q['correct'] < len(q['options'])
                and len(set(q['options']))==len(q['options']) and bool(q['explanation']), 'Invalid debugger content.')
        for index, effects in q['effects'].items():
            require(index in {str(i) for i in range(len(q['options']))}
                    and all(h in TOPICS[q['topic']]['hypotheses'] and e in ('supports','contradicts','neutral')
                            for h,e in effects.items()), 'Invalid diagnostic effects.')
    for topic,t in TOPICS.items():
        require(QUESTIONS[t['primary']]['topic']==topic, 'Invalid primary reference.')
    return True
