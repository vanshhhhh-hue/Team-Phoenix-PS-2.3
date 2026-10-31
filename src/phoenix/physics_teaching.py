"""Authored explanations, recall cues and teaching interventions for eight Physics topics."""
TEACHING = {
 'kinematics':dict(
  idea='Acceleration changes velocity over time; velocity and displacement describe different things.',
  mnemonic='VAT: Velocity Adds acceleration × Time.',
  approach=['Identify the initial velocity. “Starts from rest” means u = 0.',
    'Choose v = u + at because the question asks for speed after a time, not distance travelled.',
    'Multiply acceleration by elapsed time, then add the initial velocity. Keep units in m/s.'],
  trap='Using ½at² gives displacement, not final speed.',
  check='Acceleration in m/s² multiplied by time in s must produce m/s.',
  question='What changes when an object accelerates?',
  recall='Its velocity changes. Constant acceleration means equal velocity changes in equal time intervals.',
  example='A car starting from rest at 2 m/s² gains 2 m/s of speed every second.',
  counter='Separate the question “how fast?” from “how far?” before selecting an equation.',
  plan=['Ask students to label velocity, acceleration and displacement on a short motion story.',
        'Draw a velocity–time graph: its slope gives acceleration; its area gives displacement.',
        'Contrast a final-speed problem with a displacement problem using the same givens.']),
 'forces':dict(
  idea='Acceleration is caused by the net external force, and mass resists changes in motion.',
  mnemonic='FMA: Force = Mass × Acceleration.',
  approach=['Treat the stated acceleration as the effect of the net external force.',
    'Use F_net = ma. We are finding force, so multiply mass by acceleration rather than dividing them.',
    'Write mass in kilograms and acceleration in m/s² before substituting. The result will be in newtons.'],
  trap='Individual forces can cancel. Apply F = ma to their vector sum.',
  check='kg × m/s² is a newton. At fixed acceleration, doubling mass doubles the required net force.',
  question='Which force belongs in F = ma?',
  recall='The vector sum of all external forces on the chosen body or system.',
  example='Two opposite horizontal forces of 8 N and 3 N produce a net force of 5 N toward the larger force.',
  counter='Distinguish net force from the largest force; then check whether the student multiplies or divides.',
  plan=['Have the student draw and label a free-body diagram before calculating.',
        'Combine opposing forces with an explicit positive direction.',
        'Compare two masses under the same force, then the same acceleration.']),
 'energy':dict(
  idea='Translational kinetic energy grows linearly with mass and quadratically with speed.',
  mnemonic='Half the mass, square the speed: K = ½mv².',
  approach=['The question asks for energy of motion, so use K = ½mv², not momentum mv.',
    'Square the speed first. Then multiply by mass and by one half.',
    'Keep mass in kilograms and speed in m/s; report energy in joules.'],
  trap='Doubling speed gives four times the kinetic energy, not twice. Kinetic energy cannot be negative.',
  check='kg·m²/s² is a joule. The answer must be nonnegative.',
  question='How does doubling speed change kinetic energy?',
  recall='It multiplies kinetic energy by four because speed is squared.',
  example='At fixed mass, increasing speed from 3 m/s to 6 m/s makes kinetic energy four times larger.',
  counter='Make the square and the one-half factor explicit; distinguish energy from momentum.',
  plan=['Compare the units and meanings of mv and ½mv².',
        'Use a speed-ratio table for v, 2v and 3v before any numerical substitution.',
        'Ask the learner to predict the energy change before calculating.']),
 'gravitation':dict(
  idea='Outside a spherical planet, gravity depends on distance from its centre through an inverse-square law.',
  mnemonic='Centre first, square second.',
  approach=['Identify the distance r from the centre, not just the height above the surface.',
    'Write g/g_surface = (R/r)². For r equal to a multiple of R, the radii cancel.',
    'Square the distance ratio in the denominator and divide surface gravity by that factor.'],
  trap='At height h above the surface, r = R + h. Using h as the centre distance gives the wrong result.',
  check='Farther from the centre must mean weaker gravity. Doubling centre distance gives one-quarter gravity.',
  question='What happens to gravity when centre distance doubles?',
  recall='It falls to one quarter: g is proportional to 1/r² outside a spherical planet.',
  example='At a height equal to the planet’s radius, the centre distance is 2R and gravity is g_surface/4.',
  counter='Correct the reference distance and the inverse-square dependence before using numbers.',
  plan=['Sketch the planet, its radius, the height and the full centre distance.',
        'Build a ratio table at R, 2R and 3R.',
        'Contrast “height R” with “centre distance R” in a quick oral check.']),
 'electrostatics':dict(
  idea='Coulomb force depends on the product of the charges and inversely on separation squared.',
  mnemonic='Charges multiply; distance squares; micro means 10⁻⁶.',
  approach=['Convert both charges from microcoulombs to coulombs: each carries a factor of 10⁻⁶.',
    'Use F = k|q₁q₂|/r². Square the separation before dividing.',
    'Combine powers of ten separately from the numerical coefficients, then express force in newtons.'],
  trap='Converting only one charge or using r instead of r² introduces a large scale error.',
  check='Doubling either charge doubles force; doubling separation reduces it to a quarter.',
  question='Which changes halve or quarter Coulomb force?',
  recall='Halving one charge halves the force. Doubling separation quarters it.',
  example='A charge of 3 μC is 3 × 10⁻⁶ C; the conversion applies independently to each charge.',
  counter='Check both charge conversions and the square of separation independently.',
  plan=['Give a two-charge unit-conversion check before introducing Coulomb’s constant.',
        'Have students box the r² term and compute it on a separate line.',
        'Use a charge/separation ratio question to distinguish scaling from arithmetic.']),
 'current':dict(
  idea='At constant temperature, an ohmic resistor carries current proportional to voltage and inversely proportional to resistance.',
  mnemonic='V over R gives I.',
  approach=['Identify the voltage across this resistor and its resistance.',
    'Rearrange V = IR to I = V/R. The question asks for current, so voltage goes in the numerator.',
    'Divide volts by ohms. The resulting unit is amperes.'],
  trap='VR and R/V are not the current. Increasing resistance at fixed voltage must reduce current.',
  check='V/Ω = A. Compare the predicted direction of change before calculating.',
  question='At fixed voltage, what happens if resistance doubles?',
  recall='Current halves because I = V/R.',
  example='At 12 V, a 3 Ω resistor carries 4 A; a 6 Ω resistor carries 2 A.',
  counter='Check the ratio’s direction and the physical effect of increasing resistance.',
  plan=['Ask for a qualitative prediction at fixed voltage before doing arithmetic.',
        'Rearrange V = IR together, naming what is being solved for.',
        'Compare two resistors under the same voltage and explain which has more current.']),
 'optics':dict(
  idea='For a real object and real image in the positive-magnitude convention, reciprocal distances add to reciprocal focal length.',
  mnemonic='Reciprocals first; invert last.',
  approach=['The question specifies positive real-object and real-image distance magnitudes.',
    'Use 1/f = 1/u + 1/v, which rearranges to f = uv/(u+v).',
    'Multiply the two distances, divide by their sum, and keep the same distance unit throughout.'],
  trap='Adding u and v directly does not give f. Do not mix the positive-magnitude convention with Cartesian signs.',
  check='For equal real-object and real-image distances, both lie at 2f, so focal length is half either distance.',
  question='If real object and image distances are equal, where are they?',
  recall='Both are at 2f from a thin converging lens.',
  example='If u = v = 30 cm in positive magnitudes, f = 15 cm.',
  counter='Establish the sign convention and the reciprocal relationship before rearranging.',
  plan=['Draw the real-object/real-image geometry and label the chosen distance convention.',
        'Derive f = uv/(u+v) from the reciprocal equation.',
        'Use the symmetric 2f case as a reasonableness check.']),
 'thermal':dict(
  idea='Heat added increases internal energy unless some energy leaves as work done by the gas.',
  mnemonic='Heat in, work out: ΔU = Q − W.',
  approach=['Use the stated convention: heat absorbed is positive and work done by the gas is positive.',
    'Write ΔU = Q − W. Work done by the gas transfers energy out of it.',
    'Subtract the work from the absorbed heat and interpret the sign of the change in internal energy.'],
  trap='Adding positive work done by the gas to absorbed heat uses the wrong sign convention.',
  check='With no heat transfer, positive work done by the gas must lower internal energy.',
  question='Why is work subtracted in ΔU = Q − W?',
  recall='Here W is work done by the gas, so it represents energy leaving the system.',
  example='Absorbing 300 J and doing 100 J of work increases internal energy by 200 J.',
  counter='Fix the system boundary and sign convention before applying the first law.',
  plan=['Draw heat entering and work leaving a gas boundary.',
        'Classify the signs of Q and W in three short process descriptions.',
        'Check the adiabatic case Q = 0 before a numerical first-law question.']),
}


def guided_approach(question):
    """Reasoning scaffold only: deliberately does not interpolate the computed answer."""
    content=TEACHING[question['concept']]
    return content['idea'], content['approach'], content['check']


def worked_explanation(question, selected_index=None):
    content=TEACHING[question['concept']]
    error=question['error_labels'].get(str(selected_index),'')
    return dict(principle=content['idea'],steps=content['approach'],calculation=question['solution'],
                answer=question['options'][question['correct_index']],check=content['check'],
                correction=error or content['trap'])


def recall_cards(chapters):
    cards=[]
    for chapter in chapters:
        cid=chapter['id'];content=TEACHING[cid]
        for kind,prompt,answer in [
            ('concept',content['question'],content['recall']),
            ('relation','Recall the key relation and explain when it applies.',chapter['formula']+' '+content['idea']),
            ('pitfall','What is the most important trap to avoid in this topic?',content['trap'])]:
            cards.append(dict(id=cid+'-'+kind,concept=cid,title=chapter['title'],kind=kind,
                prompt=prompt,answer=answer,mnemonic=content['mnemonic'],example=content['example']))
    return cards
