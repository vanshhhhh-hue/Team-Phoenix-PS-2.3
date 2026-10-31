"""Generate disclosed fictional JEE profiles and genuine computed practice items offline."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json
import random

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'samples/users/user-1/physics'

TOPICS = [
    ('kinematics', 'Kinematics', 'Motion in a straight line', 'Mechanics', 'v = u + at',
     'Acceleration describes the rate of change of velocity. For constant acceleration, use v = u + at. Starting from rest means u = 0; displacement and velocity are different quantities.'),
    ('forces', 'Laws of Motion', 'Net force and acceleration', 'Mechanics', 'F = ma',
     'Net external force equals mass times acceleration. Resolve forces before applying F = ma. Mass measures inertia; acceleration depends on the net force, not the largest individual force.'),
    ('energy', 'Work, Energy & Power', 'Kinetic energy', 'Mechanics', 'K = ½mv²',
     'Translational kinetic energy is one half of mass times speed squared. Doubling speed quadruples kinetic energy. The work done by the net force equals the change in kinetic energy.'),
    ('gravitation', 'Gravitation', 'Gravity above Earth', 'Mechanics', 'g(h) = g₀R²/(R+h)²',
     'Outside a spherical Earth, gravitational acceleration varies inversely with the square of distance from the centre. At height h, that distance is R+h, not h. At h = R, gravity is one quarter of its surface value.'),
    ('electrostatics', 'Electrostatics', 'Coulomb force', 'Electricity', 'F = k|q₁q₂|/r²',
     'The magnitude of the electrostatic force is k times the product of charge magnitudes divided by separation squared. Convert microcoulombs to coulombs. Increasing separation weakens the force according to an inverse-square law.'),
    ('current', 'Current Electricity', 'Ohm’s law', 'Electricity', 'I = V/R',
     'For an ohmic conductor at constant temperature, current equals potential difference divided by resistance. Current is measured in amperes, voltage in volts and resistance in ohms. Increasing resistance at fixed voltage lowers current.'),
    ('optics', 'Ray Optics', 'Converging lens', 'Optics', '1/f = 1/u + 1/v (positive magnitudes for real object/image)',
     'A thin converging lens forming a real image obeys 1/f = 1/u + 1/v when u and v are positive distance magnitudes. Therefore f = uv/(u+v). With Cartesian signs, the equivalent formula is 1/f = 1/v - 1/u.'),
    ('thermal', 'Thermodynamics', 'First law of thermodynamics', 'Thermal physics', 'ΔU = Q − W',
     'With heat added to the gas positive and work done by the gas positive, the first law is delta U = Q - W. Heat supplied may partly increase internal energy and partly be transferred as work. State the sign convention first.'),
]


def make_question(topic, index):
    cid, title, concept, unit, formula, note = topic
    n = index + 1
    if cid == 'kinematics':
        a, t = n + 1, n + 2; value = a*t; unit_answer = 'm/s'
        prompt = f'A particle starts from rest with constant acceleration {a} m/s². What is its speed after {t} s?'
        working = f'v = u + at = 0 + {a} × {t} = {value} m/s.'
        hint = 'Starts from rest gives the initial velocity. Use the velocity–time equation, rather than the displacement equation.'
        confusion = 'Confuses displacement with velocity'
    elif cid == 'forces':
        m, a = n+1, n+2; value=m*a; unit_answer='N'
        prompt=f'A {m} kg body accelerates at {a} m/s². What is the magnitude of the net external force?'
        working=f'F_net = ma = {m} × {a} = {value} N.'
        hint='Identify mass and acceleration, then apply Newton’s second law to the net force.'
        confusion='Divides by mass when finding net force'
    elif cid == 'energy':
        m, v=2*n, n+2; value=m*v*v/2; unit_answer='J'
        prompt=f'A body of mass {m} kg moves at {v} m/s. Find its translational kinetic energy.'
        working=f'K = ½mv² = ½ × {m} × {v}² = {value:g} J.'
        hint='Kinetic energy depends on the square of speed. Keep the factor of one half.'
        confusion='Uses speed instead of speed squared'
    elif cid == 'gravitation':
        ratio=n+1; value=16/(ratio*ratio); unit_answer='m/s²'
        prompt=f'A spherical planet has surface gravity 16 m/s² and radius R. Find gravity at a distance {ratio}R from its centre.'
        working=f'g = g₀(R/r)² = 16/{ratio}² = {value:.3g} m/s².'
        hint='Use distance from the centre and apply the inverse-square dependence.'
        confusion='Applies inverse-distance instead of inverse-square dependence'
    elif cid == 'electrostatics':
        charge=n+1; value=0.9*charge; unit_answer='N'
        prompt=f'Point charges {charge} μC and 1 μC are 0.1 m apart in vacuum. Find the force magnitude. Use k = 9 × 10⁹ N·m²/C².'
        hint='Convert both charges from microcoulombs and square the separation.'
        confusion='Misses the square of separation or microcoulomb conversion'
        working=f'F = (9 × 10⁹)({charge} × 10⁻⁶)(10⁻⁶)/0.01 = {value:g} N.'
    elif cid == 'current':
        voltage, resistance=6*n, 3; value=voltage/resistance; unit_answer='A'
        prompt=f'A {voltage} V potential difference is applied across a {resistance} Ω ohmic resistor. What current flows?'
        working=f'I = V/R = {voltage}/{resistance} = {value:g} A.'
        hint='Use potential difference divided by resistance. Check the units are amperes.'
        confusion='Multiplies voltage and resistance'
    elif cid == 'optics':
        u,v=20*n,20*n; value=u*v/(u+v); unit_answer='cm'
        prompt=f'A converging lens forms a real image {v} cm from the lens of a real object {u} cm away. What is the focal length? Use positive distance magnitudes.'
        working=f'f = uv/(u+v) = ({u} × {v})/({u}+{v}) = {value:g} cm.'
        hint='Add reciprocal distances; do not add the distances directly to obtain focal length.'
        confusion='Adds object and image distances rather than their reciprocals'
    else:
        heat,work=100*n+100,40*n; value=heat-work; unit_answer='J'
        prompt=f'A gas absorbs {heat} J of heat and does {work} J of work. What is its change in internal energy?'
        working=f'ΔU = Q − W = {heat} − {work} = {value} J.'
        hint='Work done by the gas removes energy from it. Apply ΔU = Q − W with this sign convention.'
        confusion='Adds work done by the gas to heat absorbed'
    if cid=='kinematics':
        wrong=[.5*a*t*t,a+t,a/t]
        labels=['Uses displacement in place of speed','Adds acceleration and time','Divides acceleration by time']
    elif cid=='forces':
        wrong=[m/a,m+a,value*2]
        labels=['Divides mass by acceleration','Adds mass and acceleration','Introduces an extra factor of two']
    elif cid=='energy':
        wrong=[m*v,m*v*v,-value]
        labels=['Uses mv instead of kinetic energy','Omits the one-half factor','Assigns a negative value to kinetic energy']
    elif cid=='gravitation':
        wrong=[16/ratio,16*ratio*ratio,16]
        labels=['Uses inverse distance rather than inverse square','Increases gravity with distance squared','Treats gravity as independent of altitude']
    elif cid=='electrostatics':
        wrong=[value*.1,value*1e6,value*2]
        labels=['Uses separation rather than separation squared','Converts only one charge from microcoulombs','Introduces an extra factor of two in Coulomb force']
    elif cid=='current':
        wrong=[voltage*resistance,resistance/voltage,voltage]
        labels=['Multiplies voltage by resistance','Inverts the Ohm law ratio','Omits resistance when calculating current']
    elif cid=='optics':
        wrong=[u+v,u,1/(u+v)]
        labels=['Adds object and image distances','Equates focal length with object distance','Inverts the sum of distances instead of the reciprocal sum']
    else:
        wrong=[heat+work,heat,work-heat]
        labels=['Adds work done by the gas to heat supplied','Ignores work done by the gas','Reverses the first-law sign convention']
    values=[value,*wrong]
    random.Random(cid+str(n)).shuffle(values)
    options=[f'{x:.3g} {unit_answer}' for x in values]
    correct=values.index(value)
    return dict(id=f'{cid}-{n}',concept=cid,prompt=prompt,options=options,correct_index=correct,
                hint=hint,solution=working,formula=formula,misconception=confusion,
                error_labels={str(i): (labels[wrong.index(x)] if i != correct else '') for i,x in enumerate(values)})


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    bank=[make_question(topic,i) for topic in TOPICS for i in range(11)]
    chapters=[]
    for cid,title,concept,unit,formula,note in TOPICS:
        filename=cid+'.md'
        (DEST/filename).write_text(f'# {title}\n\n## {concept}\n\n{note}\n\nKey relation: {formula}\n\n## Worked practice\n\n'+ '\n\n'.join(q['prompt']+'\n\n'+q['solution'] for q in bank if q['concept']==cid),encoding='utf-8')
        chapters.append(dict(id=cid,title=title,concept=concept,unit=unit,formula=formula,notes=note,filename=filename))
    people=[('user-1','User 1','U1'),('aarav','Aarav Sharma','AS'),('ananya','Ananya Patel','AP'),('kabir','Kabir Mehta','KM'),('riya','Riya Verma','RV'),('ishaan','Ishaan Gupta','IG')]
    students=[]
    for index,(sid,name,initials) in enumerate(people):
        history=[]
        for day in range(21):
            for j,topic in enumerate(TOPICS):
                cid=topic[0];q=next(q for q in bank if q['concept']==cid and q['id']==f'{cid}-{day%7+1}')
                # The cohort is intentionally fictional; generate correlated, reproducible learning histories.
                threshold=[.78,.48,.83,.58,.43,.87,.62,.72][j] + (index-2)*.035
                correct=random.Random(f'{sid}:{day}:{cid}').random()<threshold
                answer=q['correct_index'] if correct else (q['correct_index']+1)%4
                at=datetime(2026,10,10,15,tzinfo=timezone.utc)+timedelta(days=day,minutes=j*8)
                history.append(dict(id=f'{sid}-{day}-{cid}',question_id=q['id'],concept=cid,correct=correct,
                    selected_index=answer,phase='first',hint_used=not correct and (day%2==0 or day%3==0 or day%5==0),
                    approach_used=not correct and (day%3==0 or day%5==0),
                    solution_used=not correct and day%5==0,
                    at=at.isoformat(),minutes=4+(day+j)%5))
        students.append(dict(id=sid,name=name,initials=initials,grade='Class 12',goal='JEE Main',
            batch='JEE Physics · Batch A',target='January 2027',streak=5+index,history=history))
    payload=dict(version=2,provenance='Synthetic cohort and activity generated for product demonstration; not actual student outcomes.',chapters=chapters,bank=bank,students=students)
    (DEST/'showcase.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Created {len(chapters)} readable chapters, {len(bank)} computed items and {len(students)} fictional profiles.')


if __name__=='__main__':main()
