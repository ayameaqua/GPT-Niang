"""Coordinated body performances: contact, skeletal flexion and secondary lag."""
import math

from .kinematics import VIEW_ANGLES


def smooth(x):
    x=max(0.,min(1.,x));return x*x*(3-2*x)


def envelope(elapsed,duration,enter=.18,leave=.22):
    return smooth(elapsed/enter)*smooth((duration-elapsed)/leave)


def run_flight(elapsed,duration):
    """Position, derivative and remaining time on the authored short run arc."""
    hz=2.1;phase=(elapsed*hz)%.5
    if phase<=.4:return 0.,0.,0.
    u=(phase-.4)/.1;env=envelope(elapsed,duration,.24,.28)
    def derivative(x):return 6*x*(1-x) if 0<x<1 else 0.
    env_velocity=derivative(elapsed/.24)/.24*smooth((duration-elapsed)/.28)-smooth(elapsed/.24)*derivative((duration-elapsed)/.28)/.28
    y=-12*math.sin(math.pi*u)*env
    velocity=-12*math.pi*math.cos(math.pi*u)*hz/.1*env-12*math.sin(math.pi*u)*env_velocity
    return y,velocity,(.5-phase)/hz


def perform(pose,elapsed,duration,carry,seat,listening=False):
    a=pose.motion;p=pose.phase;tr=pose.transforms
    env=envelope(elapsed,duration) if a else 0.
    angle=VIEW_ANGLES[pose.view];direction=-math.sin(math.radians(angle))
    side=-1 if pose.view in ('left','front-left','back-left') else 1
    sitting=smooth(seat/.72)
    extension=smooth((seat-.22)/.78)
    pose.pelvis=(-20*sitting,180*sitting)
    pose.root_y=0.;pose.root_x=0.
    pose.head_pitch=8*seat if pose.eye_closed else 0.
    pose.head_yaw=0.
    pose.tail_energy=.15+.8*carry
    pose.airborne=False;pose.vertical_velocity=0.
    pose.contacts=(not bool(carry),not bool(carry))
    pose.legs={name:{'x':0.,'y':0.,'foot':0.} for name in ('legFar','legNear')}
    # Leave the head at its authored neck; sagittal and yaw motion is projected.
    if a in ('nod','shake','look'):
        tr['head'].pop('x',None);tr['head'].pop('y',None);tr['head'].pop('sy',None)
        tr['head']['a']=0.
        if a=='nod':pose.head_pitch=12*math.sin(p*math.pi)**2*env
        elif a=='shake':pose.head_yaw=math.sin(p*2*math.pi)*11*env
        else:
            pose.head_yaw=math.sin(p*2*math.pi)*10*env
            pose.head_pitch=-4*math.sin(p*math.pi)*env
    if a in ('jump','hop','toss','flap'):
        height={'jump':125,'hop':48,'toss':165,'flap':42}[a]
        if p<.18:
            crouch=(44 if a!='hop' else 22)*smooth(p/.18)
        elif p<.28:
            crouch=(44 if a!='hop' else 22)*(1-smooth((p-.18)/.10))
        elif p>.80:
            crouch=(48 if a!='hop' else 23)*math.sin(math.pi*(p-.8)/.2)**2
        else:crouch=0.
        u=max(0.,min(1.,(p-.25)/.55));flight=4*u*(1-u)
        pose.root_y=-height*flight
        pose.airborne=.25<p<.80
        pose.vertical_velocity=-height*4*(1-2*u)/(.55*duration) if pose.airborne else 0.
        pose.pelvis=(0.,crouch)
        pose.head_pitch=8*crouch/48-5*flight
        pose.contacts=(not pose.airborne,not pose.airborne)
        pose.root_angle=0.
        if a=='toss':
            pose.root_x=math.sin(p*math.pi)*24
            pose.root_angle=math.sin(math.pi*u)*13 if pose.airborne else 0.
        lift=(66 if a!='hop' else 24)*math.sin(math.pi*u) if pose.airborne else 0.
        for node in pose.legs:
            pose.legs[node]={'x':direction*lift*.3,'y':-lift,'foot':-side*12*flight}
        for node,sign in (('armFar',1),('armNear',-1)):
            tr[node]['a']=sign*(50*flight-14*crouch/48)
        pose.tail_energy=1.4*flight+.6*crouch/48
        pose.hair+=math.sin(p*math.pi*2-1.0)*13*env
        pose.cloth+=math.sin(p*math.pi*2-.8)*11*env
    elif a in ('walk','run','dance'):
        env=envelope(elapsed,duration,.24,.28)
        hz=2.1 if a=='run' else 1.35 if a=='walk' else 1.7
        phase=(elapsed*hz)%1
        stance=.40 if a=='run' else .62
        pose.root_x=math.sin(phase*2*math.pi)*(8 if a!='dance' else 15)*env
        pose.root_y=0.
        pose.root_angle=0.
        pose.pelvis=(pose.root_x*.2,(8+math.cos(phase*4*math.pi)*5)*env)
        contacts=[]
        for node,offset in (('legFar',0.),('legNear',.5)):
            cycle=(phase+offset)%1
            contact=cycle<stance
            u=max(0.,min(1.,(cycle-stance)/(1-stance)))
            swing=math.sin(math.pi*u)
            height=(88 if a=='run' else 42 if a=='walk' else 58)*swing*env
            stride=(45 if a=='run' else 29)*math.sin(2*math.pi*u)*env
            pose.legs[node]={'x':direction*stride-pose.root_x,'y':-height,'foot':side*(18 if a=='run' else 9)*swing*env}
            contacts.append(contact)
        pose.contacts=tuple(contacts)
        if a=='run' and not any(contacts):
            pose.root_y,pose.vertical_velocity,_=run_flight(elapsed,duration)
            pose.airborne=True
        pose.tail_energy=(1.3 if a=='run' else .7)*env
        stride=math.sin(phase*2*math.pi)*env
        tr['armFar']['a'],tr['armNear']['a']=-stride*(35 if a=='run' else 22),stride*(35 if a=='run' else 22)
        tr['upper']['a']=(direction*8 if a=='run' else stride*2)*env
        if a=='dance':
            tr['upper']['a']=stride*6
            pose.head_yaw=-stride*5
        pose.cloth+=math.sin(phase*2*math.pi-.7)*(14 if a=='run' else 9)*env
    elif a=='land':
        pose.root_y=0.
        pose.pelvis=(0.,48*math.sin(math.pi*p)**2)
        pose.head_pitch=8*math.sin(math.pi*p)*env
        pose.tail_energy=.9*math.sin(math.pi*p)
        for node in pose.legs:pose.legs[node]['foot']=0.
    elif a in ('sit','stand','sleep') or seat>0:
        # Feet collect under the knees when standing, then the pelvis rises.
        for node,x in (('legFar',-104),('legNear',-122)):
            pose.legs[node]['x']=x*extension
            pose.legs[node]['y']=-16*math.sin(math.pi*extension)
            pose.legs[node]['foot']=side*8*extension
        pose.contacts=(not (0<extension<1),)*2
        tr['upper']['a']=side*7*math.sin(math.pi*seat)
        pose.tail_energy=.25
        if pose.eye_closed:pose.head_pitch=9+math.sin(pose.time*1.3)*1.2
    if a=='bow':
        bend=math.sin(math.pi*p)**2
        tr['upper']['a']=side*23*bend
        pose.head_pitch=9*bend
        pose.pelvis=(direction*-8*bend,14*bend)
        pose.tail_energy=.4*bend
        pose.blink=max(pose.blink,smooth(elapsed/.12)*smooth((duration-elapsed)/.12))
        pose.eye_closed=pose.blink>.999
    elif a=='shiver':
        shake=math.sin(pose.time*42)*env
        pose.root_x=0.
        pose.pelvis=(shake*1.3,6*env)
        tr['upper']['x']=shake*2;tr['upper']['a']=shake*1.2
        tr['head']['a']=-shake*1.2
        pose.tail_energy=.8*env
    elif a=='dizzy':
        wobble=math.sin(pose.time*5)*env
        pose.root_angle=0.;pose.root_x=0.
        pose.pelvis=(wobble*8,7*env)
        tr['upper']['a']=wobble*6
        pose.head_yaw=-wobble*7;pose.head_pitch=5*env
    elif a=='pet':
        tr['head']['a']=math.sin(p*math.pi*2)*5*env
        pose.head_pitch=7*env
        pose.hair+=math.sin(p*math.pi*3)*7*env
    elif a=='poke':
        recoil=math.sin(p*math.pi)*env
        pose.root_x=0.
        pose.pelvis=(-5*recoil,9*recoil)
        tr['upper']['x']=-7*recoil;tr['upper']['a']=-side*6*recoil
        pose.head_pitch=-6*recoil
    if a in ('turn','spin'):
        # A short pivot step accompanies direction keyframes; feet do not spin
        # flat on the floor while the entire character texture dissolves.
        step=math.sin(p*math.pi*(4 if a=='turn' else 8))
        for node,phase in (('legFar',step),('legNear',-step)):
            pose.legs[node]['y']=-25*max(0,phase)*env
            pose.legs[node]['x']=math.sin(p*math.pi)*direction*8*env
        pose.pelvis=(0.,4*abs(step)*env)
        pose.tail_energy=.5*env
    if carry:
        pose.airborne=True;pose.contacts=(False,False)
        pose.pelvis=(0.,0.)
        pose.root_y=-35*carry
        pose.root_angle=math.sin(pose.time*4)*4*carry
        pose.root_anchor=(425.,190.)
        for node,sign in (('legFar',-1),('legNear',1)):
            pose.legs[node]={'x':sign*10*carry,'y':-18*carry,'foot':sign*9*carry}
    # All rooted appendages share the same pelvis offset; they do not follow
    # just a subset of upper-body translation during landing or sitting.
    tr['upper']['y']=pose.pelvis[1]
    tr['upper']['x']=tr['upper'].get('x',0)+pose.pelvis[0]
    tr['head']['y']=0.;tr['head']['sy']=1.
    tr['tail']={'a':0.,'x':pose.pelvis[0],'y':pose.pelvis[1]}
    if listening:pose.head_yaw+=4
    if pose.eye_closed and (a=='sleep' or seat>.99):pose.head_pitch=max(pose.head_pitch,7.)
    tr['hairBack']['warp']=pose.hair
    tr['hairFront']['warp']=pose.hair*.35
    hand_motion=a in ('wave','raise-left','raise-right','raise-both','point','dance')
    pose.arm_base={node:0. if hand_motion else tr[node].get('a',0)*(1-max(pose.hands[index],pose.hands[2] if index==0 else 0.)) for index,node in enumerate(('armNear','armFar'))}
    return pose
