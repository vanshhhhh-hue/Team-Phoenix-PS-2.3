"""Reproducible authored content build; never touches learner state."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://openstax.org/books/university-physics-volume-1/pages/'
SOURCES = {
 'nta': {'url': 'https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2025/10/202510311323551056.pdf', 'section': 'JEE Main 2026 Physics Unit 3, PDF page 3', 'role': 'scope only'},
 'laws': {'url': BASE+'5-2-newtons-first-law', 'section': 'University Physics Volume 1 (2016), section 5.2', 'role': 'physics reference'},
 'second': {'url': BASE+'5-3-newtons-second-law', 'section': 'University Physics Volume 1 (2016), section 5.3', 'role': 'physics reference'},
 'third': {'url': BASE+'5-5-newtons-third-law', 'section': 'University Physics Volume 1 (2016), section 5.5', 'role': 'physics reference'},
 'contact': {'url': BASE+'5-6-common-forces', 'section': 'University Physics Volume 1 (2016), section 5.6', 'role': 'physics reference'},
 'friction': {'url': BASE+'6-2-friction', 'section': 'University Physics Volume 1 (2016), section 6.2', 'role': 'physics reference'},
 'circle': {'url': BASE+'6-3-centripetal-force', 'section': 'University Physics Volume 1 (2016), section 6.3', 'role': 'physics reference'},
 'impulse': {'url': BASE+'9-2-impulse-and-collisions', 'section': 'University Physics Volume 1 (2016), section 9.2', 'role': 'physics reference'},
 'momentum': {'url': BASE+'9-3-conservation-of-linear-momentum', 'section': 'University Physics Volume 1 (2016), section 9.3', 'role': 'physics reference'},
 'vectors': {'url': BASE+'2-2-coordinate-systems-and-components-of-a-vector', 'section': 'University Physics Volume 1 (2016), section 2.2', 'role': 'prerequisite reference'}}

# id, title, original explanation, assumptions/formula, original example, visual, reference
ROWS = [
 ('inertia','Inertia and the first law','A released object keeps its velocity unless interactions change it. Inertia is resistance to a change in velocity; it is not a forward force.','Inertial frame; net force zero implies constant velocity.','A puck released at 3 m/s on ideal ice stays at 3 m/s when horizontal resistance is absent.','block','laws'),
 ('second','Force, mass and acceleration','Net force controls the change of velocity. Its direction gives acceleration, which need not point along the current velocity.','Constant positive mass: sum F = ma, with SI units N, kg, m/s².','A 2 kg trolley under 6 N net force accelerates at 3 m/s².','experiment','laws'),
 ('third','Interaction pairs','An interaction has two forces of equal magnitude and opposite direction on two different bodies. Draw each body separately.','Simultaneous pair F_AB = -F_BA; masses need not match.','A hand pushes a wall with 20 N; the wall pushes the hand with 20 N.','pair','laws'),
 ('normal','Normal force and free-body diagrams','Select one body, then list external interactions on it. The normal acts perpendicular to contact and is determined by the perpendicular equation of motion.','Horizontal support, upward acceleration a: N - mg = ma. Contact must remain.','A 50 kg passenger accelerating upward at 2 m/s² has N = 600 N for g = 10 m/s².','block','contact'),
 ('tension','Tension and connected bodies','A taut rope pulls along its length. Equal tension follows from a massless rope over a frictionless massless pulley, not from the word rope alone.','Ideal taut inextensible rope and pulley; for upward moving mass: T - mg = ma.','A 2 kg mass accelerating upward at 1 m/s² needs 22 N tension, with g = 10.','pair','contact'),
 ('equilibrium','Concurrent-force equilibrium','For a particle in equilibrium, vector components sum to zero. Forces can be nonzero individually. Constant velocity also permits equilibrium.','Particle/concurrent forces; sum Fx = sum Fy = 0.','Forces 3 N east and 4 N north are balanced by 5 N southwest with components -3 and -4 N.','equilibrium','laws'),
 ('static','Static friction','At a sticking contact, friction supplies the required tangential force up to a limit. Determine the needed friction before comparing with the maximum.','Dry contact model: |fs| ≤ mu_s N; equality only at impending slip.','A 2 kg box pushed by 3 N stays still if mu_s = 0.4 and g = 10; friction is 3 N, not 8 N.','friction','friction'),
 ('kinetic','Kinetic and rolling friction','Sliding friction opposes relative sliding at contact. Rolling resistance involves deformation and dissipation; ideal pure rolling need not dissipate energy or require nonzero friction.','Dry sliding approximation fk = mu_k N. There is no universal rolling-resistance coefficient law here.','A 5 kg crate sliding right with mu_k = 0.2 has 10 N friction left when g = 10 and N = mg.','friction','friction'),
 ('momentum','Momentum and conservation','Momentum is a vector attached to the chosen system. Internal interaction pairs cancel in the system sum. External impulse determines whether total momentum changes.','Fixed system: delta P = external impulse. Conservation requires zero net external impulse over the interval.','Two skaters push apart on ideal ice; their total horizontal momentum remains its initial value.','pair','momentum'),
 ('impulse','Impulse and force-time graphs','Impulse measures force accumulated over time and equals change in momentum. Area under a signed force-time graph determines the signed impulse.','J = integral F dt = delta p; constant-force shortcut J = F delta t.','A constant 4 N force lasting 3 s gives 12 N s impulse.','impulse','impulse'),
 ('circular','Uniform circular dynamics','Speed can be constant while velocity changes direction. The inward resultant is supplied by actual interactions such as tension, gravity or friction.','Uniform circle: a = v²/r, r > 0. Do not add an extra centripetal interaction to the diagram.','At 4 m/s on a 2 m radius, acceleration is 8 m/s² inward.','circle','circle'),
 ('roads','Level and banked roads','On a level road lateral static friction supplies the turn. On a frictionless banked road the inward component of the normal provides it.','Level: v²/r ≤ mu_s g. Ideal bank: tan(theta) = v²/(rg); no vertical acceleration.','At r = 20 m, g = 10, tan(theta) = 0.5, the ideal bank speed is 10 m/s.','circle','circle')]
PREREQS = [
 ('vectors','Vectors and components','Choose axes and resolve a vector: Fx = F cos(theta), Fy = F sin(theta), with theta from +x. Components replace the vector in an equation; never add them again to the original.'),
 ('units','SI units','Convert mass to kg and time to s before using force in N. One newton equals one kg m/s²; impulse uses N s.'),
 ('velocity','Velocity versus acceleration','Velocity describes current motion; acceleration describes its rate of change. A rightward object may have leftward acceleration and slow down.'),
 ('algebra','Basic algebra','In F = ma, divide both sides by positive m to find a. In T - mg = ma, add mg to both sides before substituting values.')]
MIS = [
 ('inertia','Motion needs a continuous forward force','Would the same reasoning predict slowing when all horizontal contact forces vanish?'),
 ('inertia','Zero net force means zero velocity','Could a spacecraft coast at a nonzero constant velocity with engines off?'),
 ('second','Force determines velocity rather than acceleration','Does a leftward force tell you current velocity or its rate of change?'),
 ('second','A right-moving body must accelerate right','Can a right-moving car brake with acceleration to the left?'),
 ('third','Action and reaction cancel on one body','Name the body receiving each member of the pair.'),
 ('third','The heavier body exerts the larger interaction force','Are unequal accelerations evidence of unequal forces or unequal masses?'),
 ('normal','Normal force always equals mg','Would the scale reading change in an upward accelerating lift?'),
 ('normal','Weight and normal form a third-law pair','What body receives the reaction partner of the Earth’s pull on the block?'),
 ('static','Static friction always equals mu_s N','If a push is below the threshold, what force is needed for balance?'),
 ('kinetic','Friction always opposes object velocity','A belt moves right beneath a slower block: which way is relative slip?'),
 ('static','Stationary bodies cannot experience friction','What balances a small horizontal push on a stationary crate?'),
 ('tension','Tension always equals hanging weight','What is T - mg when a hanging mass accelerates upward?'),
 ('tension','Every rope and pulley has equal tension','Which assumption rules out a tension difference accelerating a rope segment?'),
 ('equilibrium','Equilibrium means no forces act','Can a book have both weight and support while staying at rest?'),
 ('momentum','Momentum is conserved despite external impulse','What is included in your system and what acts across its boundary?'),
 ('impulse','Impulse and force are interchangeable','If the same force acts twice as long, does momentum change twice as much?'),
 ('circular','Centripetal force is an extra interaction','Which real object supplies the inward force on a ball on a string?'),
 ('circular','Constant circular speed means zero acceleration','Does the velocity arrow keep the same direction around the circle?')]

# Six independently written situations per concept: three primary and three related checks.
# Every row has four choices, first correct before deterministic rotation, and original reasoning.
BANK = {
'inertia': [
 ('A puck moves right on a frictionless horizontal floor after release. What happens horizontally?',['Constant rightward velocity','It slows without a force','It accelerates right','It stops immediately'],'No horizontal interaction remains, so horizontal acceleration is zero.'),
 ('A train moves straight at constant velocity. Its net force is:',['Zero','Forward','Backward','Equal to its momentum'],'Constant velocity has zero derivative, so net force vanishes.'),
 ('A bus brakes suddenly. Why does an unrestrained bag move forward relative to the bus?',['It tends to retain its ground-frame velocity','A new forward force appears','Gravity turns forward','Its mass increases'],'The bus slows while the bag initially retains its velocity.'),
 ('A spacecraft coasts with engines off far from other bodies. Its velocity:',['Remains constant','Gradually becomes zero','Must point toward Earth','Doubles each second'],'In the ideal isolated inertial frame there is no resultant to change velocity.'),
 ('A stone at rest has zero net force for 5 s. At the end it is:',['Still at rest','Moving forward','Moving downward','Moving faster each second'],'Zero initial velocity remains zero when acceleration vanishes.'),
 ('A right-moving glider experiences a leftward net force. Its instantaneous acceleration is:',['Leftward','Rightward','Zero','Undetermined by the force'],'Force sets acceleration direction even before velocity changes sign.')],
'second': [
 ('A 2 kg trolley experiences 6 N net force. Its acceleration is:',['3 m/s²','12 m/s²','0.33 m/s²','6 m/s²'],'Divide 6 N by 2 kg: a = 3 m/s². Multiplication is an algebra error, not evidence about force direction.'),
 ('A v-time graph is a straight line falling from +6 m/s to +2 m/s in 2 s. For 3 kg, net force is:',['6 N left','6 N right','12 N left','Zero'],'Slope is (2-6)/2 = -2 m/s²; multiply by 3 kg to get -6 N.'),
 ('At fixed nonzero net force, doubling positive mass makes acceleration:',['Half as large','Twice as large','Unchanged','Zero'],'The ratio F/m halves when only the denominator doubles.'),
 ('A 4 kg cart starts from rest under 8 N net force. Velocity after 3 s is:',['6 m/s along the force','2 m/s along the force','24 m/s along the force','6 m/s opposite the force'],'First find a = 2 m/s², then delta v = a t = 6 m/s.'),
 ('A ball moving upward has only gravity acting. Its acceleration points:',['Downward','Upward','Nowhere at the top','Along velocity at all times'],'Gravity points downward throughout free flight, independent of instantaneous velocity.'),
 ('A 500 g slider has 2 N rightward resultant. Acceleration is:',['4 m/s² right','0.004 m/s² right','1 m/s² right','4 m/s² left'],'Convert 500 g to 0.5 kg; 2/0.5 = 4 m/s².')],
'third': [
 ('A truck pushes a light car. Compare their mutual contact force magnitudes.',['Equal','Truck on car is larger','Car on truck is larger','Both must be zero'],'The contact pair has equal magnitudes; different masses allow different accelerations.'),
 ('Which pair belongs on one selected block’s free-body diagram?',['Earth on block and floor on block','Block on floor and floor on block','Block on Earth and Earth on block','Hand on wall and wall on hand'],'A free-body diagram lists forces received by the selected body only.'),
 ('Two skaters push apart. The lighter skater has greater acceleration because:',['Equal interaction forces act on unequal masses','It receives the larger force','Its reaction has a delay','Action forces cancel its weight'],'Use the equal force magnitude divided by each mass.'),
 ('A swimmer pushes water backward. Water pushes the swimmer:',['Forward with equal force magnitude','Backward with equal force magnitude','Forward with always greater force','Only after the swimmer stops'],'These are simultaneous interaction forces on different bodies.'),
 ('Earth pulls a falling ball down. The third-law partner is:',['Ball pulling Earth upward','Air pushing ball upward','Ball’s acceleration','Ground pushing ball upward'],'Exchange source and recipient: ball on Earth.'),
 ('A 60 kg person and 30 kg child push each other on ideal ice. Acceleration magnitudes adult:child are:',['1:2','2:1','1:1','4:1'],'The same interaction force divided by twice the mass gives half the acceleration.')],
'normal': [
 ('A 50 kg passenger accelerates upward at 2 m/s². With g=10, scale normal is:',['600 N','500 N','400 N','100 N'],'Upward axis: N - 500 = 50×2, so N = 600 N.'),
 ('A block slides on a fixed smooth 60° incline while maintaining contact. Normal is:',['mg/2','mg','2mg','Zero'],'There is no acceleration perpendicular to the fixed plane. Resolve along that axis: N = mg cos60°.'),
 ('The reaction partner of Earth’s force on a book is:',['Book’s gravitational force on Earth','Table’s force on book','Book’s force on table','Net force on book'],'A reaction pair reverses the interacting bodies; the table is a different interaction.'),
 ('In a freely falling ideal lift, a passenger’s scale reading is:',['Zero','mg','2mg','mg/2'],'Passenger and scale accelerate down at g; N - mg = -mg.'),
 ('A 2 kg box remains on a horizontal floor while pulled vertically upward with 5 N. g=10. Normal is:',['15 N','20 N','25 N','5 N'],'Vertical balance gives N + 5 - 20 = 0.'),
 ('A lift moves upward but slows at 2 m/s². For 50 kg and g=10, normal is:',['400 N','600 N','500 N','Zero'],'Acceleration is downward: N - 500 = -100 N.')],
'tension': [
 ('A 2 kg mass accelerates upward at 1 m/s², g=10. Tension is:',['22 N','20 N','18 N','2 N'],'For the mass: T - 20 = 2×1.'),
 ('Equal tension throughout a connected rope is justified when it is:',['Massless with ideal frictionless massless pulley','Heavy with rough pulley','Stretching with massive pulley','Any rope at all'],'A massless rope segment needs zero resultant; a real pulley can require a tension difference.'),
 ('Two blocks of 2 kg and 3 kg on a smooth floor are joined by an ideal rope. A 10 N pull acts on the 3 kg block. Tension is:',['4 N','10 N','6 N','20 N'],'Whole system a = 10/5 = 2; the 2 kg block receives T = 2×2 = 4 N.'),
 ('A 3 kg mass hangs at rest on an ideal rope, g=10. Tension is:',['30 N','3 N','Zero','60 N'],'At rest, a = 0; upward tension balances weight.'),
 ('A 2 kg suspended mass accelerates downward at 3 m/s², g=10. Tension is:',['14 N','26 N','20 N','6 N'],'Upward axis: T - 20 = -6.'),
 ('Ideal Atwood machine has masses 3 kg and 2 kg, g=10. Acceleration magnitude is:',['2 m/s²','10 m/s²','5 m/s²','1 m/s²'],'Net driving force 10 N accelerates total 5 kg: a = 2 m/s².')],
'equilibrium': [
 ('A particle has forces 3 N east and 4 N north. A balancing third force has magnitude:',['5 N','7 N','1 N','12 N'],'The third force has components -3 N and -4 N; magnitude sqrt(9+16).'),
 ('Which condition describes particle equilibrium in an inertial frame?',['Vector sum of forces is zero','Every individual force is zero','Velocity must be zero','Mass must be zero'],'Balance is a vector condition, compatible with rest or constant velocity.'),
 ('A sign hangs from two symmetric strings each 30° from vertical. Weight is 100 N. Each tension is:',['100/√3 N','50 N','100 N','200 N'],'Horizontal components cancel; 2T cos30° = 100 N.'),
 ('A lamp at rest has weight 20 N and one vertical support string. Support force is:',['20 N upward','Zero','20 N downward','40 N upward'],'For the lamp, vertical force balance requires T - 20 = 0.'),
 ('Two forces 6 N east and 8 N south act on a particle. Balancing force direction is:',['Northwest','Northeast','Southeast','Southwest'],'Reverse the resultant components: west and north.'),
 ('A body moves straight at constant 5 m/s with two forces of 12 N east and unknown force. Unknown force is:',['12 N west','Zero','5 N west','12 N east'],'Constant velocity requires cancellation of the given force.')],
'static': [
 ('A stationary 2 kg box is pushed right with 3 N. mu_s=0.4, g=10. Friction magnitude is:',['3 N','8 N','Zero','11 N'],'Maximum is 8 N, but balance requires only 3 N.'),
 ('A crate is at rest under a horizontal push below its slip threshold. Static friction points:',['Opposite the impending relative slip','Always along velocity','Always vertically up','Nowhere because it is stationary'],'A stationary contact can exert tangential force to prevent slip.'),
 ('A 5 kg crate has mu_s=0.3 on a level floor, g=10. Maximum static friction is:',['15 N','50 N','1.5 N','150 N'],'At the threshold, mu_s N = 0.3×50 N.'),
 ('A book stays still on an inclined rough board. Friction points:',['Up the slope','Down the slope','Vertically up','Zero'],'Gravity tends to slide it downhill; contact friction prevents that tendency.'),
 ('A horizontal force-friction graph for a resting crate below threshold has friction magnitude:',['Equal to applied force','Constant at mu_s N','Zero throughout','Larger than applied force'],'With zero acceleration, horizontal friction matches the applied push.'),
 ('A rough floor supports a box with N=40 N and mu_s=0.5. A 25 N horizontal push from rest means:',['Static balance is impossible','Static friction becomes 25 N','Static friction remains zero','Normal becomes 50 N'],'The 20 N static limit is below the required 25 N.')],
'kinetic': [
 ('A 5 kg crate slides right, mu_k=0.2, g=10, N=mg. Friction is:',['10 N left','10 N right','50 N left','Zero'],'Relative sliding is rightward, so mu_k N = 10 N points left.'),
 ('A moving belt slides right beneath a slower block. Friction on the block points:',['Right','Left','Vertically down','Zero in every case'],'The block slips left relative to the belt, so friction on the block points right.'),
 ('Which is a sound statement about rolling resistance?',['It depends on deformation and dissipation','It always equals mu_k N','It is always zero on real wheels','It must oppose the centre’s velocity even for static contact friction'],'Real rolling resistance is not the universal dry sliding law; ideal rolling may have no dissipation.'),
 ('A 2 kg box slides left on a fixed floor with mu_k=0.3 and g=10. Friction is:',['6 N right','6 N left','20 N right','Zero'],'Relative slip is leftward, so sliding friction is rightward with magnitude 6 N.'),
 ('A crate starts to slide right when the applied force exceeds its static limit. In the dry model with mu_k < mu_s, friction just after slip:',['Drops to mu_k N','Stays equal to any applied force','Points right','Becomes zero necessarily'],'Once sliding, use kinetic friction and its relative-slip direction.'),
 ('An ideal rigid wheel rolls at constant speed on an ideal horizontal rigid surface without losses or other horizontal forces. Required friction is:',['Zero','Always mu_s N','Always mu_k N','Always mg'],'No horizontal acceleration or torque is required; pure rolling does not demand nonzero friction.')],
'momentum': [
 ('Two skaters push apart on ideal horizontal ice. Total horizontal momentum is conserved because:',['Net external horizontal impulse is zero','Each skater’s momentum is constant','Internal forces vanish individually','Their velocities must match'],'Internal forces change individual momenta but cancel for the pair.'),
 ('A single ball receives a nonzero external impulse. Its momentum:',['Changes by that impulse','Must remain constant','Always becomes zero','Changes only if its mass changes'],'System boundary matters: for the ball, delta p equals the external impulse.'),
 ('An isolated cart and its 1 kg load are initially at rest. Cart mass excluding the load is 2 kg. After ejection, the load moves at 4 m/s right in the ground frame. Cart velocity is:',['2 m/s left','2 m/s right','4 m/s left','Zero'],'Initial total momentum zero; 2v + 1×4 = 0.'),
 ('Two carts exchange spring forces on a smooth track. For the two-cart system, the spring forces are:',['Internal and cancel in the total momentum equation','External and both rightward','Absent','A source of nonzero net impulse necessarily'],'The interactions transfer momentum inside the boundary.'),
 ('A 3 kg cart moves right at 2 m/s. Its momentum is:',['6 kg m/s right','1.5 kg m/s right','6 N right','Zero'],'Momentum is mass times vector velocity and has units kg m/s.'),
 ('Choose a momentum-conserving horizontal system while a person pushes a cart on ideal ice.',['Person plus cart, with no external horizontal force','Cart alone under the person’s push','Person alone under cart reaction','Any subsystem regardless of external forces'],'Including both interacting bodies makes their mutual forces internal.')],
'impulse': [
 ('A force-time graph is a rectangle: +4 N from 0 to 3 s. Impulse is:',['12 N s','4 N s','1.33 N s','7 N s'],'Area is height times width: 4×3 = 12 N s.'),
 ('For the same stopping momentum change, doubling stopping time makes average force magnitude:',['Half','Double','Unchanged','Four times'],'Average force magnitude is the fixed impulse magnitude divided by duration.'),
 ('A force-time triangle rises from zero to 6 N then back to zero over 4 s. Impulse is:',['12 N s','24 N s','6 N s','48 N s'],'Triangle area is 1/2×4×6.'),
 ('A 2 kg ball changes velocity from +3 m/s to -1 m/s. Impulse is:',['-8 N s','+8 N s','-4 N s','+4 N s'],'Delta p = 2×(-1-3) = -8 kg m/s.'),
 ('A +5 N force lasts 2 s, then -5 N lasts 2 s. Total impulse is:',['Zero','20 N s','10 N s','-10 N s'],'Signed areas cancel even though the force was nonzero during both intervals.'),
 ('An airbag increases stopping time for the same initial and final momentum. It reduces:',['Average force magnitude','Required impulse magnitude','Initial momentum necessarily','Mass necessarily'],'Spreading the same momentum change over longer time reduces average force.')],
'circular': [
 ('An object moves uniformly in a circle at 4 m/s, radius 2 m. Acceleration magnitude is:',['8 m/s²','2 m/s²','Zero','16 m/s²'],'v²/r = 16/2; direction is toward the centre.'),
 ('At the rightmost point of an anticlockwise circle, velocity and acceleration point:',['Up and left','Left and up','Up and right','Right and down'],'Velocity is tangent up; inward acceleration is left.'),
 ('A ball circles on a horizontal frictionless table attached to a string. Its horizontal free-body diagram has:',['Tension inward only','Tension plus extra centripetal force inward','Tension outward','No horizontal force'],'Tension is the actual interaction supplying the inward resultant.'),
 ('At constant radius, doubling speed multiplies inward acceleration by:',['4','2','1','1/2'],'The square of speed appears in v²/r.'),
 ('A string holding a circling puck breaks on an ideal horizontal table. The puck initially travels:',['Along the tangent','Radially outward','Radially inward','In the same circle'],'Without tension the horizontal resultant vanishes; velocity initially keeps its tangent direction.'),
 ('Uniform circular motion has constant speed but changing:',['Velocity direction','Mass','Speed magnitude','Radius necessarily'],'Changing direction is enough to produce nonzero acceleration.')],
'roads': [
 ('A level road has mu_s=0.5, r=20 m, g=10. Maximum non-skidding speed is:',['10 m/s','5 m/s','20 m/s','100 m/s'],'At the limit mv²/r = mu_s mg, so v = sqrt(100).'),
 ('A frictionless bank has tan(theta)=0.5, r=20 m and g=10. Ideal speed is:',['10 m/s','20 m/s','5 m/s','Zero'],'Divide inward and vertical normal components: v² = rg tan(theta) = 100.'),
 ('On a frictionless bank at design speed, inward force comes from:',['Horizontal component of the normal','Extra centripetal interaction','Weight’s horizontal component in ground axes','Kinetic friction'],'Normal is tilted; its horizontal projection supplies the inward resultant.'),
 ('For the same level-road radius and mu_s, doubling vehicle mass changes limiting speed by a factor of:',['1','2','1/2','√2'],'Mass cancels in mv²/r ≤ mu_s mg.'),
 ('At fixed bank angle and g, quadrupling road radius changes frictionless design speed by a factor of:',['2','4','1/2','1'],'The speed is proportional to sqrt(r).'),
 ('A frictionless banked-road vehicle has no vertical acceleration. The vertical normal component equals:',['mg','mv²/r','Zero','mg + mv²/r'],'Use vertical balance separately from the inward acceleration equation.')]
}

# Further representation changes for the two flagship demo branches; reserved for transfer.
BANK['inertia'] += [
 ('A velocity-time graph is horizontal at +7 m/s. What is the horizontal resultant?',['Zero','7 N right','7 N left','It increases with time'],'A horizontal v-time graph has zero slope, so acceleration and resultant vanish.'),
 ('A curling stone slides right but slows on rough ice. Compared with ideal frictionless ice, what changed?',['A leftward friction interaction is present','Inertia disappeared','Mass became zero','Velocity itself supplies a forward force'],'Friction changes velocity on rough ice; no forward force is required to sustain motion on ideal ice.')]
BANK['second'] += [
 ('A 1 kg glider has forces 7 N right and 3 N left. Its acceleration is:',['4 m/s² right','10 m/s² right','4 m/s² left','7 m/s² right'],'Add signed force components first: 7-3 = 4 N, then divide by 1 kg.'),
 ('A force-acceleration graph through the origin has slope 5 kg. For a net force of 15 N, acceleration is:',['3 m/s²','75 m/s²','5 m/s²','0.33 m/s²'],'In F versus a, slope is mass. The force is 15 N and a = 15/5 = 3 m/s².')]

# Candidate evidence attaches to observable reasoning, never arbitrary wrong-option positions.
DISTRACTORS = {
 'inertia-1': {'It slows without a force':'m01','It stops immediately':'m02','It accelerates right':'m03'},
 'inertia-2': {'Forward':'m01','Equal to its momentum':'m03'},
 'inertia-4': {'Gradually becomes zero':'m01'},
 'inertia-6': {'Rightward':'m04','Zero':'m03'},
 'second-2': {'6 N right':'m04'},
 'second-5': {'Upward':'m04','Nowhere at the top':'m03'},
 'third-1': {'Truck on car is larger':'m06','Car on truck is larger':'m06'},
 'third-2': {'Block on floor and floor on block':'m05','Block on Earth and Earth on block':'m05'},
 'third-3': {'It receives the larger force':'m06','Action forces cancel its weight':'m05'},
 'normal-1': {'500 N':'m07'}, 'normal-2': {'mg':'m07'},
 'normal-3': {'Table’s force on book':'m08'}, 'normal-4': {'mg':'m07'},
 'static-1': {'8 N':'m09','Zero':'m11'},
 'static-2': {'Always along velocity':'m10','Nowhere because it is stationary':'m11'},
 'static-5': {'Constant at mu_s N':'m09','Zero throughout':'m11'},
 'static-6': {'Static friction becomes 25 N':'m09'},
 'kinetic-2': {'Left':'m10'},
 'tension-1': {'20 N':'m12'},
 'tension-2': {'Any rope at all':'m13'},
 'tension-5': {'20 N':'m12'},
 'equilibrium-2': {'Every individual force is zero':'m14','Velocity must be zero':'m02'},
 'momentum-1': {'Each skater’s momentum is constant':'m15'},
 'momentum-2': {'Must remain constant':'m15'},
 'momentum-6': {'Any subsystem regardless of external forces':'m15'},
 'impulse-1': {'4 N s':'m16'}, 'impulse-2': {'Unchanged':'m16'},
 'circular-1': {'Zero':'m18'},
 'circular-3': {'Tension plus extra centripetal force inward':'m17'},
 'roads-3': {'Extra centripetal interaction':'m17'}}

SCAFFOLDS = {
 'inertia': ('the released or coasting object','Weight down and support up on a horizontal surface; check for horizontal contact forces.','Use a horizontal axis; distinguish current velocity from its change.','sum Fx = m ax; zero horizontal resultant gives ax = 0.'),
 'second': ('the accelerating object named in the prompt','Combine all external forces as signed components before dividing by mass.','Choose the positive direction stated in the prompt; on a v-time graph use its signed slope.','a = Fnet/m, with mass in kg; for constant acceleration delta v = a delta t.'),
 'third': ('each interacting body separately','Draw A on B on B’s diagram and B on A on A’s diagram. These forces never cancel on one object.','Use a common axis to compare signed forces; compare magnitudes separately.','F_AB = -F_BA; a_A/a_B in magnitude = m_B/m_A for that interaction alone.'),
 'normal': ('the passenger, book or supported block','Weight points vertically down. Normal is perpendicular to its contact. Include any other applied pull.','For a lift use up as positive; for an incline use a perpendicular axis.','sum F_perpendicular = m a_perpendicular; N = mg only in the appropriate special case.'),
 'tension': ('one mass, then the connected system if useful','Draw tension along the taut rope away from the selected mass, weight down, and support if on a floor.','Choose along the rope or each body’s motion, respecting the ideal rope constraint.','Use T - mg = ma for an upward axis on a hanging mass; system equations eliminate internal tension.'),
 'equilibrium': ('the particle, lamp or sign','Draw every force meeting at the selected particle; balance their vector sum, not their individual magnitudes.','Resolve into perpendicular x and y components.','sum Fx = 0 and sum Fy = 0; reverse the resultant to find a balancing force.'),
 'static': ('the box or book at the sticking contact','Weight and normal act perpendicular to a level floor; friction opposes the tangential slip tendency.','Choose one axis tangent to contact.','First calculate friction needed for no slip; compare its magnitude with mu_s N.'),
 'kinetic': ('the sliding body or rolling wheel','Identify relative contact slip, not just centre-of-mass motion; draw friction opposite that slip.','Use a tangential axis along the surface.','For the dry sliding model |fk| = mu_k N. Do not apply that law universally to rolling resistance.'),
 'momentum': ('the explicitly chosen cart, person, or multi-body system','Internal forces cancel only for the combined system; identify external interactions across its boundary.','Choose right as positive for the horizontal examples.','P = sum m v; delta P = J_external. Set delta P = 0 only with zero net external impulse.'),
 'impulse': ('the object receiving the force','Use the net force on this object over the stated interval.','Use signed force and momentum along the chosen axis.','J = area under F(t) = m(v_final - v_initial); F_average = J/delta t.'),
 'circular': ('the circling object at its stated position','Draw the actual tension, contact or gravity interactions. Inward resultant is not an extra interaction.','Use inward radial and tangential axes; for uniform speed tangential acceleration is zero.','a_radial = v²/r and Fnet_radial = m v²/r.'),
 'roads': ('the vehicle, approximated as a particle','Level road: weight down, normal up, lateral friction inward. Frictionless bank: weight down and tilted normal only.','Use vertical and inward horizontal axes.','Level: f ≤ mu_s mg and f = mv²/r. Ideal bank: N cosθ = mg, N sinθ = mv²/r.')}

def build():
    concepts=[]; questions=[]; cards=[]
    for ci,(cid,title,note,assumptions,example,visual,source) in enumerate(ROWS):
        source={'second':'second','third':'third'}.get(cid,source)
        deps = ['vectors','units','velocity','algebra'] if cid=='second' else ['second'] if cid not in ('inertia','third') else ['velocity']
        concepts.append(dict(id=cid,title=title,prerequisite_ids=deps,goals=['Explain '+title.lower(),'Choose the system and justify a prediction'],explanation=note,formula_assumptions=assumptions,worked_example=example,visual_id=visual,evidence_refs=[source]))
        candidates=[f'm{i+1:02}' for i,(c,_,_) in enumerate(MIS) if c==cid]
        for j,(prompt,options,reason) in enumerate(BANK[cid]):
            qid=f'{cid}-{j+1}'; shift=(ci+j)%4
            options=options[shift:]+options[:shift]; key=(-shift)%4
            mapping={str(k): DISTRACTORS.get(qid,{}).get(options[k],'uncertain') for k in range(4) if k!=key}
            if cid=='second' and j in (0,3,5):
                mapping={str(k):'calculation' for k in range(4) if k!=key}
            questions.append(dict(id=qid,concept_id=cid,prerequisite_ids=deps,role='primary' if j<3 else 'follow_up' if j<6 else 'transfer',difficulty=['easy','medium','hard'][j%3],representation='graph' if 'graph' in prompt else 'diagram' if ('diagram' in prompt or 'point' in prompt) else 'numerical' if any(s in prompt for s in (' kg',' N','m/s','tan(')) else 'conceptual',assumptions=assumptions+' Use g = 10 m/s² where specified; classical inertial frame.',prompt=prompt,options=options,correct_index=key,visual_id=visual,distractor_candidates=mapping,hints=['Select the body or system. '+('Convert to kg and isolate the unknown before substitution.' if cid=='second' else 'Which external interactions can change its motion?'),assumptions+' Choose axes and write a component equation before calculating.'],explanation=reason,solution_steps=['Body/system: select the object or group named in the prompt.','Forces: list only external interactions; paired reactions on other bodies are excluded.','Axes: choose along the motion or the stated components.','Law and calculation: '+reason,'Interpretation: '+note],evidence_refs=[source],follow_up_ids=[f'{cid}-{j+4}'] if j<3 else [],transfer_family=cid,provenance='original authored NLM pack v1'))
            body,forces,axes,law=SCAFFOLDS[cid]
            questions[-1].update(assumptions='Use the conditions in the prompt, in a classical inertial frame. Neglect air resistance. Use g = 10 m/s² only where specified.'+(' Ropes and pulleys are ideal only where stated.' if cid=='tension' else ''),
                                hints=['Select '+body+'. '+('Convert mass to kg before rearranging Fnet = ma.' if cid=='second' else forces), axes+' '+law],
                                solution_steps=['1. Body/system: select '+body+'.','2. Free-body diagram in words: '+forces,'3. Axes: '+axes,'4. Apply the law: '+law,'5. Calculate/reason: '+reason,'6. Interpret and check: '+note])
        for k in range(2):
            cards.append(dict(id=f'card-{cid}-{k}',concept_id=cid,kind='open_recall',front=('Predict and explain: '+BANK[cid][3][0]) if k else 'Explain '+title.lower()+' and state one assumption.',back=(BANK[cid][3][2] if k else note+' '+assumptions),visual_id=visual,practice_id=f'{cid}-1',evidence_refs=[source]))
            category='prediction' if k else ['concept_recall','diagram_interpretation','common_confusion'][ci%3]
            cards[-1]['category']=category
            if category=='diagram_interpretation':
                cards[-1]['front']='Interpret the diagram: identify the shown quantities, their units or directions, and explain which law connects them.'
                cards[-1]['back']=note+' '+assumptions+' '+example
            elif category=='common_confusion':
                confusion=next((claim for c,claim,_ in MIS if c==cid),None)
                if confusion: cards[-1]['front']='Challenge this claim and explain why it can fail: '+confusion+'.'
    misconceptions=[dict(id=f'm{i+1:02}',concept_id=c,claim=claim,probe=probe,hint='Name the receiving body and check: '+probe,remediation_ref=c,observable_distractors=[q['id']+':'+k for q in questions for k,v in q['distractor_candidates'].items() if v==f'm{i+1:02}']) for i,(c,claim,probe) in enumerate(MIS)]
    scenes={
     'second-2':dict(kind='graph',quantity='velocity',points=[[0,6],[2,2]],x_max=2,y_min=0,y_max=8),
     'inertia-7':dict(kind='graph',quantity='velocity',points=[[0,7],[3,7]],x_max=3,y_min=0,y_max=10),
     'impulse-1':dict(kind='graph',quantity='force',points=[[0,4],[3,4]],x_max=3,y_min=0,y_max=6),
     'impulse-3':dict(kind='graph',quantity='force',points=[[0,0],[2,6],[4,0]],x_max=4,y_min=0,y_max=8),
     'impulse-5':dict(kind='graph',quantity='force',points=[[0,5],[2,5],[2,-5],[4,-5]],x_max=4,y_min=-6,y_max=6),
     'circular-2':dict(kind='orbit',position='rightmost',rotation='anticlockwise'),
     'normal-2':dict(kind='incline',angle=60)}
    for q in questions:
        q['scene']=scenes.get(q['id'])
    pack=dict(id='nlm-jee-2026',version=1,syllabus_year=2026,provenance='Original authored offline pack; not live AI or NTA teaching notes',sources=SOURCES,source_note='NTA checked 2026-10-30. NCERT endpoint returned HTTP 502; OpenStax used as accessible educational reference. No syllabus-year substitution.',prerequisites=[dict(id=i,title=t,explanation=e,evidence_refs=['vectors' if i=='vectors' else 'second']) for i,t,e in PREREQS],concepts=concepts,misconceptions=misconceptions,questions=questions,flashcards=cards,visuals=[dict(id=i,family=i,version=1) for i in ['block','experiment','pair','equilibrium','friction','impulse','circle','incline']])
    (ROOT/'samples/users/user-1/nlm-v1.json').write_text(json.dumps(pack,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return pack

if __name__=='__main__':
    p=build(); print('Authored:',len(p['concepts']),'concepts,',len(p['questions']),'questions,',len(p['flashcards']),'cards')
