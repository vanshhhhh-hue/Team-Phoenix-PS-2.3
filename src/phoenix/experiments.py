"""Bounded concept-specific teaching scenarios. SI units, g=10 m/s²."""
from html import escape
import math
from engine import require

# Controls are specific to each concept; every input changes an identified output.
CONTROLS={
 'inertia':[('speed','Initial rightward speed (m/s)',0.,20.,4.),('force','Resistance (N)',0.,30.,0.)],
 'second':[('mass','Mass (kg)',.1,10.,2.),('force','Net force (N)',-30.,30.,6.)],
 'third':[('force','Interaction magnitude (N)',0.,30.,6.)],
 'normal':[('mass','Mass (kg)',.1,10.,2.),('acceleration','Lift upward acceleration (m/s²)',-12.,12.,0.)],
 'tension':[('mass','Hanging mass (kg)',.1,10.,2.),('acceleration','Upward acceleration (m/s²)',-5.,5.,0.)],
 'equilibrium':[('force','Force east (N)',-30.,30.,3.),('vertical','Force north (N)',-30.,30.,4.)],
 'static':[('mass','Mass (kg)',.1,10.,2.),('force','Applied force (N)',0.,30.,6.),('mu','Static friction coefficient',0.,1.,.4)],
 'kinetic':[('mass','Mass (kg)',.1,10.,2.),('force','Applied force (N)',0.,30.,6.),('mu','Sliding friction coefficient',0.,1.,.2)],
 'momentum':[('mass','Mass A (kg)',.1,10.,2.),('mass_b','Mass B (kg)',.1,10.,3.),('speed','Velocity A (m/s)',-20.,20.,4.),('speed_b','Velocity B (m/s)',-20.,20.,-2.)],
 'impulse':[('force','Constant signed force (N)',-30.,30.,6.),('duration','Duration (s)',.1,10.,3.)],
 'circular':[('speed','Circular speed (m/s)',0.,20.,4.),('radius','Circle radius (m)',.5,20.,2.)],
 'roads':[('radius','Road radius (m)',.5,100.,20.),('angle','Bank angle (degrees)',0.,75.,30.),('mu','Level-road friction coefficient',0.,1.,.4)]}


def scenario(concept,**values):
    require(concept in CONTROLS,'Unsupported concept scenario.')
    controls=CONTROLS[concept]; require(set(values)<=set(c[0] for c in controls),'Unrelated experiment control.')
    p={key:values.get(key,default) for key,label,lo,hi,default in controls}
    for key,label,lo,hi,default in controls:
        require(type(p[key]) in (float,int) and math.isfinite(p[key]) and lo<=p[key]<=hi,'Experiment parameter outside supported bounds.')
    if concept=='inertia':
        acceleration=-p['force']/2.; final=max(0,p['speed']+acceleration*3)
        result=f"After 3 s: speed {final:.2f} m/s. While sliding, acceleration {acceleration:.2f} m/s². With zero resultant the initial velocity persists."
        assumption='Fixed 2 kg body in a horizontal inertial frame; normal and weight balance. Constant resistance opposes motion until rest; no reverse sliding.'
        labels=['Initial velocity right: '+str(p['speed'])+' m/s','Resistance left: '+str(p['force'])+' N']
        outputs=dict(acceleration=acceleration,speed_after_3s=final)
    elif concept=='second':
        outputs=dict(acceleration=p['force']/p['mass']);result=f"a = F_net/m = {outputs['acceleration']:.2f} m/s². Velocity is a separate state."
        assumption='Constant positive mass, horizontal inertial frame; F is the signed resultant.';labels=['Net horizontal F = '+str(p['force'])+' N']
    elif concept=='third':
        outputs=dict(force_on_a=-p['force'],force_on_b=p['force']);result=f"B on A: {-p['force']:.2f} N; A on B: {p['force']:.2f} N. These act on different bodies."
        assumption='Only the interaction pair is drawn. Their sum is zero for the combined A+B system; each separate body may accelerate.';labels=['Body A: B on A left','Body B: A on B right']
    elif concept in ('normal','tension'):
        raw=p['mass']*(10+p['acceleration']);support=max(0,raw);outputs=dict(support=support,contact=raw>=0)
        name='Normal force' if concept=='normal' else 'Rope tension'
        result=f"{name} = m(g+a) = {support:.2f} N." if raw>=0 else f'Required contact force {raw:.2f} N is impossible. Contact is lost: N=0; the body falls freely at -10 m/s² independently of the lift.'
        assumption='g=10 m/s², positive acceleration upwards. '+('Floor contact is unilateral; negative N is impossible.' if concept=='normal' else 'Single hanging mass; light taut vertical rope; no pulley mechanical advantage.')
        labels=[name+' upward: '+f'{support:.2f} N','Weight downward: '+f"{10*p['mass']:.2f} N"]
    elif concept=='equilibrium':
        outputs=dict(balance_x=-p['force'],balance_y=-p['vertical'],magnitude=math.hypot(p['force'],p['vertical']))
        result=f"Balancing force = ({-p['force']:.2f}, {-p['vertical']:.2f}) N; magnitude {outputs['magnitude']:.2f} N. Resultant after balancing = 0."
        assumption='Concurrent coplanar forces on a particle; east/north positive; torque of extended bodies is outside this scenario.';labels=['Known vector: '+str((p['force'],p['vertical']))+' N','Balancing vector: '+str((-p['force'],-p['vertical']))+' N']
    elif concept in ('static','kinetic'):
        normal=10*p['mass'];limit=p['mu']*normal
        if concept=='static':
            outputs=dict(required=p['force'],limit=limit,can_stick=p['force']<=limit)
            result=f"Required static friction {p['force']:.2f} N; limit μsN = {limit:.2f} N. "+('Friction matches the push; acceleration = 0.' if outputs['can_stick'] else 'The static condition fails. This case does not calculate subsequent sliding friction.')
            assumption='Initially at rest on a level fixed surface; static friction adjusts up to its limit.'
        else:
            outputs=dict(friction=limit,acceleration=(p['force']-limit)/p['mass'])
            result=f"Already sliding right: friction μkN = {limit:.2f} N left; a = {outputs['acceleration']:.2f} m/s² while sliding right."
            assumption='Already sliding, not a static threshold test. Ideal rolling without slip is different; rolling resistance needs a separate model.'
        labels=['Push right: '+str(p['force'])+' N','Static limit' if concept=='static' else 'Sliding friction left: '+f'{limit:.2f} N']
    elif concept=='momentum':
        total=p['mass']*p['speed']+p['mass_b']*p['speed_b'];final=total/(p['mass']+p['mass_b'])
        outputs=dict(momentum=total,common_velocity=final)
        result=f"Before: p_total = {total:.2f} kg m/s. If A and B stick: v = {final:.2f} m/s; after: p_total = {total:.2f} kg m/s."
        assumption='One-dimensional perfectly inelastic collision; chosen system A+B has zero external impulse; kinetic energy need not be conserved.';labels=['A: '+str(p['mass'])+' kg at '+str(p['speed'])+' m/s','B: '+str(p['mass_b'])+' kg at '+str(p['speed_b'])+' m/s']
    elif concept=='impulse':
        outputs=dict(impulse=p['force']*p['duration']);result=f"Signed force-time area J = FΔt = {outputs['impulse']:.2f} N s = Δp."
        assumption='Constant signed resultant over the chosen duration; impulse changes momentum, not necessarily speed alone.';labels=['Force '+str(p['force'])+' N','Duration '+str(p['duration'])+' s']
    elif concept=='circular':
        outputs=dict(acceleration=p['speed']**2/p['radius']);result=f"Inward a = v²/r = {outputs['acceleration']:.2f} m/s²; instantaneous velocity is tangent."
        assumption='Uniform circular motion in an inertial frame; centripetal acceleration is not an additional force.';labels=['Tangent speed '+str(p['speed'])+' m/s','Inward acceleration '+f"{outputs['acceleration']:.2f} m/s²"]
    else:
        outputs=dict(level_limit=math.sqrt(p['mu']*10*p['radius']),bank_design=math.sqrt(10*p['radius']*math.tan(math.radians(p['angle']))))
        result=f"Level road (friction-limited): v_max = {outputs['level_limit']:.2f} m/s. Frictionless bank design speed: {outputs['bank_design']:.2f} m/s."
        assumption='Two different ideal models: level road uses static friction; frictionless bank balances vertical forces at its design speed. g=10 m/s².';labels=['Level: inward static friction','Bank: normal has inward component']
    predictions={
        'inertia':['Zero resistance preserves velocity; resistance changes it','Inertia supplies a forward force'],
        'second':['Acceleration follows the signed net force divided by mass','Velocity and acceleration must have the same sign'],
        'third':['Interaction forces are equal and opposite on different bodies','The interaction pair cancels on each separate body'],
        'normal':['The contact force changes with lift acceleration','The normal force is always exactly mg'],
        'tension':['Tension must account for the hanging mass acceleration','Tension always equals mg even during acceleration'],
        'equilibrium':['The balancing vector opposes the resultant','The balancing vector points along the resultant'],
        'static':['Static friction adjusts up to its limit','Static friction always equals its limiting value'],
        'kinetic':['Sliding friction opposes current relative motion','Sliding friction must equal the applied force'],
        'momentum':['Total momentum of A+B is conserved under zero external impulse','Each body must keep its own initial momentum'],
        'impulse':['Signed force-time area gives the momentum change','Impulse equals force alone regardless of duration'],
        'circular':['Velocity is tangent and acceleration is inward','Acceleration must point along the tangent velocity'],
        'roads':['Level-road limit and frictionless-bank design use different assumptions','One arbitrary bank speed works with no friction']}
    elements=['<rect width="600" height="360" fill="#f8fafc"/>']
    def line(x,y,u,v,color='#526071'):
        elements.append(f'<line x1="{x}" y1="{y}" x2="{u}" y2="{v}" stroke="{color}" stroke-width="3"/>')
    def arrow(x,y,dx,dy,color='#126b60'):
        if abs(dx)+abs(dy)<.001:return
        u=x+dx;v=y+dy;line(x,y,u,v,color); theta=math.atan2(dy,dx)
        for off in (-.5,.5):line(u,v,u-10*math.cos(theta+off),v-10*math.sin(theta+off),color)
    def body(x,y,name):
        elements.append(f'<rect x="{x-22}" y="{y-20}" width="44" height="40" rx="4" fill="#e2e8f0" stroke="#334155"/><text x="{x-7}" y="{y+5}" font-size="16">{name}</text>')
    if concept=='third':
        body(180,150,'A');body(420,150,'B');arrow(158,150,-90 if p['force'] else 0,0);arrow(442,150,90 if p['force'] else 0,0)
    elif concept in ('normal','tension'):
        body(300,160,'A');arrow(300,140,0,-min(100,outputs['support']*3));arrow(300,180,0,min(80,10*p['mass']*3),'#a12b32')
        if concept=='normal':line(200,230 if not outputs['contact'] else 182,400,230 if not outputs['contact'] else 182)
        else:line(300,140,300,45)
    elif concept=='circular':
        elements.append('<circle cx="260" cy="150" r="85" fill="none" stroke="#526071" stroke-width="2"/>')
        body(345,150,'A');arrow(345,130,0,-70 if p['speed'] else 0,'#2563eb');arrow(323,150,-75 if p['speed'] else 0,0,'#a12b32')
    elif concept=='impulse':
        line(100,145,500,145);line(100,230,100,40)
        height=abs(p['force'])*3;top=145-height if p['force']>=0 else 145
        elements.append(f'<rect x="100" y="{top}" width="{p["duration"]*35}" height="{height}" fill="#eaf4f1" stroke="#126b60"/>')
    elif concept=='momentum':
        body(170,150,'A');body(420,150,'B');arrow(170,100,p['speed']*5,0,'#2563eb');arrow(420,100,p['speed_b']*5,0,'#2563eb')
    elif concept=='equilibrium':
        body(300,150,'A');arrow(300,150,p['force']*3,-p['vertical']*3);arrow(300,150,-p['force']*3,p['vertical']*3,'#a12b32')
    elif concept=='roads':
        line(55,180,230,180);body(145,160,'A');arrow(123,160,-55,0)
        theta=math.radians(p['angle']);line(430-70*math.cos(theta),175+70*math.sin(theta),430+70*math.cos(theta),175-70*math.sin(theta))
        body(430,175,'B');arrow(430,155,-65*math.sin(theta),-65*math.cos(theta));arrow(430,195,0,55,'#a12b32')
    else:
        line(100,185,500,185);body(300,165,'A');arrow(278 if concept=='inertia' or p.get('force',0)<0 else 322,165,(-1 if concept=='inertia' else 1)*max(-100,min(100,p.get('force',0)*4)),0)
        if concept=='inertia':arrow(300,95,p['speed']*5,0,'#2563eb')
        if concept in ('static','kinetic'):
            actual=min(p['force'],outputs['limit']) if concept=='static' else outputs['friction']
            arrow(278,165,-min(100,actual*4),0,'#a12b32')
    for i,label in enumerate(labels):
        elements.append(f'<text x="30" y="{285+i*30}" font-size="16" fill="#17253d">{escape(label)}</text>')
    svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 360" role="img"><title>'+escape('; '.join(labels))+'</title>'+''.join(elements)+'</svg>'
    return dict(parameters=p,outputs=outputs,result=result,assumptions=assumption,svg=svg,alt='; '.join(labels),prediction_options=predictions[concept])


def debugger_comparison(topic,**p):
    require(topic in ('motion','mass') and set(p)==({'speed','mass','force'} if topic=='motion' else {'mass','force'}),'Invalid comparison parameters.')
    require(all(type(v) in (int,float) and math.isfinite(v) for v in p.values()) and 1<=p['mass']<=5 and 1<=p['force']<=(6 if topic=='motion' else 20),'Comparison outside supported bounds.')
    if topic=='motion':
        require(2<=p['speed']<=10,'Invalid initial speed.')
        values=[max(0,p['speed']-p['force']/p['mass']*t) for t in range(5)]
        result='Smooth-track speed stays '+str(p['speed'])+' m/s. Rough-track speeds at seconds 0–4: '+', '.join(f'{v:g}' for v in values)+' m/s.'
    else:
        values=[p['force']/p['mass'],p['force']/(2*p['mass'])]
        result=f'A acceleration {values[0]:g} m/s²; twice-mass B acceleration {values[1]:g} m/s².'
    return dict(result=result,values=values)
