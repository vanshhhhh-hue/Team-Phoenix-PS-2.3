"""Bounded deterministic SVG templates. No generated HTML, scripts or executable specs."""
from html import escape
import math
from engine import require
from nlm import FAMILIES


def quantities(family, mass=2., force=6., angle=30., speed=4., radius=2., mu_s=.4, mu_k=.2):
    require(family in FAMILIES,'Unknown visual family.')
    params=dict(mass=mass,force=force,angle=angle,speed=speed,radius=radius,mu_s=mu_s,mu_k=mu_k)
    bounds=dict(mass=(.1,100),force=(0,100),angle=(0,75),speed=(0,20),radius=(.5,100),mu_s=(0,1),mu_k=(0,1))
    require(all(type(v) in (float,int) and math.isfinite(v) and bounds[k][0]<=v<=bounds[k][1] for k,v in params.items())
            and mu_k<=mu_s,'Visual parameters outside supported physics regime.')
    t=math.radians(angle); normal=mass*10
    threshold=mu_s*normal; slipping=force>threshold
    friction=mu_k*normal if slipping else force
    return dict(**params,normal=normal,weight=normal,acceleration=force/mass,
                threshold=threshold,friction=friction,slipping=slipping,
                friction_acceleration=(force-friction)/mass,
                incline_normal=normal*math.cos(t),down_slope=normal*math.sin(t),
                circle_acceleration=speed**2/radius,bank_speed=math.sqrt(radius*10*math.tan(t)),
                level_speed=math.sqrt(mu_s*10*radius))


def render(family, **params):
    p=quantities(family,**params); items=[]
    def line(x,y,u,v,color='#64748b',dash=False):
        items.append(f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{u:.2f}" y2="{v:.2f}" stroke="{color}" stroke-width="3"'+(' stroke-dasharray="6 4"' if dash else '')+'/>')
    def text(x,y,label,color='#17253d'):
        items.append(f'<text x="{x:.2f}" y="{y:.2f}" fill="{color}" font-size="15">{escape(label)}</text>')
    def arrow(x,y,dx,dy,label,color='#087f74',labelx=None,labely=None):
        if abs(dx)+abs(dy)<.001: return
        u=x+dx; v=y+dy; line(x,y,u,v,color)
        theta=math.atan2(dy,dx)
        for off in (-.5,.5): line(u,v,u-10*math.cos(theta+off),v-10*math.sin(theta+off),color)
        text(u+7 if labelx is None else labelx,v-6 if labely is None else labely,label,color)
    def body(x,y,label):
        items.append(f'<rect x="{x-25}" y="{y-20}" width="50" height="40" rx="5" fill="#e2e8f0" stroke="#334155"/>'); text(x-12,y+5,label)
    fmt=lambda n:f'{n:.2f}'
    if family=='block':
        line(60,230,520,230); body(270,210,'A')
        arrow(270,190,0,-85,'N = '+fmt(p['normal'])+' N')
        arrow(270,230,0,85,'mg = '+fmt(p['weight'])+' N')
        arrow(295,210,min(p['force']*9,150),0,'F = '+fmt(p['force'])+' N')
        text(55,45,'Smooth horizontal surface; body A; no vertical acceleration.')
        text(55,365,'Individual forces shown; resultant is F horizontally (not an extra force).')
        alt='Free-body diagram for block A: weight down, equal normal up, '+('applied force right' if p['force'] else 'no horizontal interaction')+', no friction.'
    elif family=='experiment':
        body(180,180,'A'); arrow(205,180,min(p['force']*9,200),0,'F = '+fmt(p['force'])+' N')
        arrow(180,265,100,0,'v right (chosen initial condition)','#2563eb')
        arrow(180,320,min(p['acceleration']*12,220),0,'a = '+fmt(p['acceleration'])+' m/s²','#dc2626')
        text(60,55,'Smooth floor; net horizontal F; m = '+fmt(p['mass'])+' kg')
        alt='Separate arrows show the chosen rightward velocity and force-driven acceleration; a equals F divided by positive mass.'
    elif family=='pair':
        body(170,200,'A'); body(400,200,'B')
        arrow(145,200,-80,0,'B on A','#dc2626',45,160)
        arrow(425,200,80,0,'A on B','#087f74',420,160)
        text(65,70,'Separate body diagrams: equal/opposite contact forces')
        text(65,310,'Only the interaction pair is shown, not complete vertical forces.')
        alt='On A the contact force from B points left; on B the contact force from A points right; equal arrow lengths.'
    elif family=='incline':
        t=math.radians(p['angle']); x,y=280,200
        line(x-110*math.cos(t),y+110*math.sin(t),x+110*math.cos(t),y-110*math.sin(t))
        items.append(f'<circle cx="{x}" cy="{y}" r="8" fill="#334155"/>')
        arrow(x,y,0,105,'mg','#dc2626')
        arrow(x,y,-90*math.sin(t),-90*math.cos(t),'N perpendicular')
        # Components are a separate decomposition inset, never added as extra forces.
        text(45,45,'Smooth incline; angle = '+fmt(p['angle'])+'°; friction = 0')
        text(45,335,'Separate components: along slope mg sinθ = '+fmt(p['down_slope'])+' N')
        text(45,365,'Into plane mg cosθ = N = '+fmt(p['incline_normal'])+' N')
        alt='Smooth plane rises to the right; weight is vertically down and normal perpendicular up-left. Gravity components are stated separately.'
    elif family=='friction':
        line(55,230,530,230); body(280,210,'A')
        arrow(305,210,min(p['force']*6,180),0,'F = '+fmt(p['force'])+' N')
        arrow(255,210,-min(p['friction']*6,180),0,'f = '+fmt(p['friction'])+' N','#dc2626',50,175)
        text(45,45,'Initially at rest on fixed level floor; push increases rightward.')
        text(45,80,'N = mg = '+fmt(p['normal'])+' N; static limit = '+fmt(p['threshold'])+' N')
        text(45,310,('Sliding right: kinetic friction' if p['slipping'] else 'Sticking: friction matches push'))
        text(45,345,'a = '+fmt(p['friction_acceleration'])+' m/s²; μs = '+fmt(p['mu_s'])+', μk = '+fmt(p['mu_k']))
        alt='Applied force points right and friction left. Below the static threshold the box remains at rest; above it, kinetic friction applies.'
    elif family=='circle':
        items.append('<circle cx="200" cy="205" r="85" fill="none" stroke="#94a3b8" stroke-width="2"/>')
        body(285,205,'A'); arrow(285,185,0,-90,'v tangent','#2563eb')
        arrow(260,205,-90,0,'a inward','#dc2626',140,245)
        t=math.radians(p['angle'])
        text(370,100,'Bank: design speed')
        line(460-70*math.cos(t),220+70*math.sin(t),460+70*math.cos(t),220-70*math.sin(t))
        items.append('<circle cx="460" cy="220" r="6" fill="#334155"/>')
        arrow(460,220,-80*math.sin(t),-80*math.cos(t),'N')
        arrow(460,220,0,60,'mg','#dc2626')
        text(30,55,'Plan view: anticlockwise circle, r = '+fmt(p['radius'])+' m')
        text(30,310,'a = v²/r = '+fmt(p['circle_acceleration'])+' m/s²')
        text(30,342,'Level road: static friction supplies inward resultant.')
        text(30,374,'Ideal frictionless bank: v = √(rg tanθ) = '+fmt(p['bank_speed'])+' m/s')
        alt='At the rightmost point velocity points up and acceleration left. Separate bank cross-section shows only actual forces: normal up-left, weight down. The bank is at its design speed; acceleration is not an extra force.'
    elif family=='impulse':
        line(90,290,500,290); line(90,290,90,65)
        h=min(p['force']*12,180)
        items.append(f'<rect x="90" y="{290-h}" width="280" height="{h}" fill="#ccfbf1" stroke="#087f74"/>')
        text(400,320,'t (s)'); text(25,65,'F (N)'); text(355,315,'3')
        text(110,90,'Constant F = '+fmt(p['force'])+' N for 3 s')
        text(80,365,'Signed area = impulse = '+fmt(p['force']*3)+' N s')
        alt='Force-time rectangle with width 3 s and height equal to the selected force in newtons; its area is impulse.'
    else:
        body(275,220,'A'); arrow(275,220,90,0,'3 N east','#2563eb')
        arrow(275,220,0,-120,'4 N north','#087f74')
        arrow(275,220,-90,120,'5 N balance','#dc2626',95,360)
        text(65,50,'Concurrent forces: sum Fx = 0; sum Fy = 0')
        alt='Three concurrent forces: 3 N east, 4 N north, and 5 N southwest with components -3 N and -4 N.'
    svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 410" role="img"><title>'+escape(alt)+'</title><rect width="600" height="410" fill="#f8fafc"/>'+''.join(items)+'</svg>'
    return svg,alt,p


def render_question(scene):
    """Question-only givens. Never displays an answer, slope, area or requested vector."""
    from nlm import validate_scene
    validate_scene(scene)
    require(scene is not None,'Question has no visual scene.')
    head='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 350"><rect width="600" height="350" fill="#f8fafc"/>'
    def text(x,y,label): return f'<text x="{x}" y="{y}" font-size="16" fill="#17253d">{escape(label)}</text>'
    if scene['kind']=='graph':
        ymin,ymax=scene['y_min'],scene['y_max']; xmax=scene['x_max']
        xy=lambda x,y:(90+430*x/xmax,280-220*(y-ymin)/(ymax-ymin))
        points=' '.join(f'{x:.2f},{y:.2f}' for x,y in [xy(*p) for p in scene['points']])
        zero=xy(0,0)[1]
        content=f'<path d="M90 40V280 M90 {zero}H530" stroke="#64748b" fill="none" stroke-width="2"/>'
        content+=f'<polyline points="{points}" fill="none" stroke="#087f74" stroke-width="4"/>'
        for x,y in scene['points']:
            px,py=xy(x,y); content+=text(min(px+5,495),py-10,f'({x}, {y})')
        content+=text(460,320,'time (s)')+text(20,25,'velocity (m/s)' if scene['quantity']=='velocity' else 'force (N)')
        content+=text(70,310,'0')
        alt='Question graph: '+scene['quantity']+' against time; points '+str(scene['points'])+'. Join consecutive points by straight segments; no computed result is shown.'
    elif scene['kind']=='orbit':
        content='<circle cx="260" cy="170" r="100" fill="none" stroke="#94a3b8" stroke-width="2"/><circle cx="360" cy="170" r="8" fill="#087f74"/>'
        content+=text(250,175,'C')+text(375,175,'A')+text(100,320,'Anticlockwise motion. Predict v and a at A.')
        alt='Circle centred at C with the body A at the rightmost point, moving anticlockwise; velocity and acceleration arrows are intentionally absent.'
    else:
        angle=scene['angle']; t=math.radians(angle)
        content=f'<line x1="{300-130*math.cos(t)}" y1="{170+130*math.sin(t)}" x2="{300+130*math.cos(t)}" y2="{170-130*math.sin(t)}" stroke="#64748b" stroke-width="3"/><circle cx="300" cy="170" r="9" fill="#087f74"/>'
        content+=text(75,320,f'Smooth incline: {angle}° to horizontal. Find normal force.')
        alt=f'Particle on a smooth plane at {angle} degrees to horizontal; normal and gravity components are not supplied.'
    return head+'<title>'+escape(alt)+'</title>'+content+'</svg>',alt
