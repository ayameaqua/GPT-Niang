"""Deterministic pose evaluation, independent of Qt, wall time and quota polling."""
from dataclasses import dataclass, field, replace
import math
from .dynamics import perform,run_flight

EXPRESSIONS = dict(zip(
    "neutral happy wink love shy surprised angry sad sleepy thinking smug pout worried determined flustered scared excited cry confused".split(),
    "平静 开心 眨眼 喜欢 害羞 惊讶 生气 难过 犯困 思考 得意 嘟嘴 担心 认真 慌张 害怕 期待 大哭 疑惑".split()))
MOTIONS = {
    "stand": ("站起", 1.2), "jump": ("跳", 1.2), "hop": ("小跳", .9), "look": ("张望", 2.7),
    "turn": ("转身", .6), "nod": ("点头", 1.2), "shake": ("摇头", 1.2), "spin": ("转圈", 1.6),
    "sit": ("坐下", .8), "sleep": ("睡觉", .8), "dizzy": ("晕", 3.2), "walk": ("走走", 12),
    "run": ("跑", 12), "wave": ("招手", 1.7), "bow": ("鞠躬", 1.7), "shiver": ("发抖", 1.9),
    "flap": ("扑腾", 1.5), "dance": ("跳舞", 3.4),
    "tilt-left": ("向左歪头", 1.8), "tilt-right": ("向右歪头", 1.8),
    "raise-left": ("抬左手", 2), "raise-right": ("抬右手", 2), "raise-both": ("举双手", 2),
    "point": ("指向气泡", 2), "carried": ("拎起", 1.5), "land": ("放下", .65),
    "toss": ("画布内抛落", 1.4), "pet": ("摸头", 1.6), "poke": ("戳一戳", .65),
    "look-back": ("回眸", 2.8),
}
VIEWS = dict(zip("front front-left left back-left back back-right right front-right".split(),
                 "正面 左前侧 左侧面 左后侧 背面 右后侧 右侧面 右前侧".split()))
FACE_VIEWS = {"front","front-left","front-right","left","right"}
HAND_GESTURES = {"wave","raise-left","raise-right","raise-both","point","dance"}
# Node and screen rotation for anatomical left/right, independent of camera.
HAND_BINDINGS = {
    "front": (("armNear",-1),("armFar",1)),
    "front-left": (("armNear",-1),("armFar",1)),
    "front-right": (("armNear",-1),("armFar",1)),
    "left": (("armNear",1),("armFar",1)),
    "right": (("armFar",-1),("armNear",-1)),
    "back-left": (("armFar",1),("armNear",-1)),
    "back": (("armFar",1),("armNear",-1)),
    "back-right": (("armFar",1),("armNear",-1)),
}


def clamp(value, low=0., high=1.):
    return max(low, min(high, value))


def smooth(value):
    x = clamp(value)
    return x*x*(3-2*x)


def turn_progress(phase):
    return smooth((phase-.15)/.70)


@dataclass
class Pose:
    expression: str = "neutral"
    view: str = "front-left"
    transforms: dict = field(default_factory=dict)
    root_x: float = 0
    root_y: float = 0
    root_angle: float = 0
    seat: float = 0
    blink: float = 0
    gaze: tuple = (0, 0)
    speech: float = 0
    hair: float = 0
    cloth: float = 0
    tear: float = 0
    phase: float = 0
    time: float = 0
    motion: str = ""
    eye_closed: bool = False
    blend_view: str = ""
    view_mix: float = 0
    gesture: float = 0
    look_back: float = 0
    # Anatomical left/right lift, pointing-hand mix, wrist sway in degrees.
    hands: tuple = (0., 0., 0., 0.)
    head_pitch: float = 0.
    head_yaw: float = 0.
    pelvis: tuple = (0.,0.)
    legs: dict = field(default_factory=dict)
    contacts: tuple = (True,True)
    airborne: bool = False
    vertical_velocity: float = 0.
    root_anchor: tuple = (425.,969.)
    tail_energy: float = 0.
    tail_angle: object = None
    point_target: object = None
    arm_base: dict = field(default_factory=dict)
    expression_from: str = ''
    expression_mix: float = 1.
    face_weights: dict = field(default_factory=dict)
    camera_angle: object = None
    turn_tail: float = 0.
    face_visibility: float = 1.


class Animator:
    def __init__(self):
        self.expression = "neutral"
        self.view = "front-left"
        self.action = ""
        self.elapsed = 0.
        self.clock = 0.
        self.speed = 1.
        self.paused = False
        self.seat = 0.
        self.start_seat = 0.
        self.sleeping = False
        self.speech = False
        self.listening = False
        self.gaze = (0., 0.)
        self.pending = ""
        self.turn_from = self.view
        self.turn_to = self.view
        self.carry = 0.
        self.emotion = 0.
        self.face_requested = False
        self.face_reasons = set()
        self.settling = None
        self.head_start=0.
        self.head_return=None
        self.hand_return=None
        self.body_return=None
        self.fall=None
        self.after_land=''
        self.point_target=None
        self.lid=0.
        self.speech_amount=0.
        self.face_transition=None
        self.hair_follow=0.;self.hair_velocity=0.

    def set_expression(self, value):
        if value not in EXPRESSIONS:
            return False
        previous=self.pose()
        weights=previous.face_weights or {previous.expression:1.}
        self.face_transition=[weights,0.] if weights!={value:1.} and not self.paused else None
        self.expression = value
        self.request_face_view()
        return True

    def request_face_view(self,reason="expression",enabled=True):
        """Consume requests after a running turn, without losing queued actions."""
        if enabled:self.face_reasons.add(reason)
        else:self.face_reasons.discard(reason)
        self.face_requested=bool(self.face_reasons)
        self._consume_face_request()

    def _consume_face_request(self):
        if not self.face_requested or self.action in ("turn","spin","look-back") or self.settling:
            return
        if self.view in FACE_VIEWS:
            self.face_requested=False
            self.face_reasons.clear()
            return
        # A facial request cannot take ownership of a ballistic performance.
        # Keep it queued until touchdown; carried pets retain their grab anchor.
        if self.action in ('jump','hop','toss','flap','land') or (self.action!='carried' and self.pose().airborne) or self.fall:
            return
        resume=self.action
        self.play("turn",keep_air=True)
        self.turn_to="front-right" if self.view=="back-right" else "front-left"
        self.pending=resume

    def set_view(self, value):
        if value not in VIEWS:
            return False
        self.view = value
        self.settling=None
        self.head_return=None
        self.hand_return=None
        self.body_return=None
        return True

    def play(self, action,keep_air=False):
        if action not in MOTIONS:
            return False
        previous=self.pose()
        previous_fall=self.fall;previous_elapsed=self.elapsed
        self.face_transition=[previous.face_weights or {previous.expression:1.},0.]
        if previous.airborne and self.action=='land' and self.fall and action!='carried':
            self.after_land=action if action!='land' else ''
            self.pending=''
            return True
        self.after_land=''
        self.fall=None
        if previous.airborne and not keep_air and action!='carried':
            release=previous.motion=='carried' and action=='toss'
            if action!='land' and not release:self.after_land=action
            action='land'
            height=min(-1e-6,previous.root_y);velocity=previous.vertical_velocity;gravity=1200.
            if previous.motion in ('jump','hop','toss','flap'):
                peak={'jump':125,'hop':48,'toss':165,'flap':42}[previous.motion]
                gravity=8*peak/(.55*MOTIONS[previous.motion][1])**2
            elif previous_fall:gravity=previous_fall['gravity']
            if release:velocity=-430.;gravity=1200.
            seconds=(-velocity+math.sqrt(velocity*velocity-2*gravity*height))/gravity
            self.fall={'start':previous,'height':height,'velocity':velocity,'gravity':gravity,'duration':seconds}
            if release:self.fall['release']=True
            if previous.motion=='run':
                _,_,remaining=run_flight(self.elapsed,MOTIONS['run'][1])
                self.fall.update(run_elapsed=self.elapsed,duration=max(1e-6,remaining))
            elif previous_fall and 'run_elapsed' in previous_fall:
                self.fall.update(run_elapsed=previous_fall['run_elapsed']+previous_elapsed,
                                 duration=max(1e-6,previous_fall['duration']-previous_elapsed))
        self.body_return=None if self.fall else [previous,0.,.14]
        self.hand_return=[previous.hands,0.]
        head=previous.look_back
        self.head_start=head if action=='look-back' else 0.
        self.head_return=[head,0.] if head>0 and action!='look-back' else None
        # Settle the visible blend before starting another orientation/action.
        # Selecting an action midway through a turn must not snap back a view.
        if self.action in ("turn","spin") or self.settling:
            current=self.pose()
            if current.blend_view and current.view_mix>0:
                target=1 if current.view_mix>=.5 else 0
                self.view=current.blend_view if target else current.view
                self.settling=[current.view,current.blend_view,current.view_mix,target,0.]
        self.pending = ""
        self.start_seat = self.seat
        seated_next=action if self.seat>.001 and action not in ('sit','sleep','stand','land','carried') else ''
        if seated_next:action='stand'
        self.elapsed = 0.
        self.action = action
        self.sleeping = action == "sleep"
        if action not in ("sit", "sleep"):
            self.sleeping = False
        if action in ("turn", "spin"):
            self.turn_from = self.view
            order = list(VIEWS)
            self.turn_to = order[(order.index(self.view) + 4) % 8]
        target=None
        if action in HAND_GESTURES:
            target="front"
        elif action == "bow":
            target="right" if self.view in ("right","front-right","back-right") else "left"
        elif action in ("sit","sleep"):
            target="front-left"
        elif action=="look-back":
            target="back-right" if self.view in ("right","front-right","back-right") else "back-left"
        # Face-dependent gestures return to a readable view first.
        allowed = {"turn", "spin", "walk", "run", "stand", "raise-left", "raise-right", "raise-both", "carried", "land", "toss", "tilt-left", "tilt-right"}
        if self.view in ("left", "right"):
            allowed |= {"wave", "look", "nod", "shake"}
        if target is None and action not in allowed and self.view not in FACE_VIEWS:
            target="front-left"
        if target is not None and self.view != target:
                self.pending = action
                self.turn_from, self.turn_to = self.view, target
                self.action = "turn"
        elif seated_next:
            self.pending=seated_next
        return True

    def cancel(self):
        current=self.pose()
        self.face_transition=[current.face_weights or {current.expression:1.},0.]
        if current.airborne:
            self.play('land')
        elif self.seat>.001:
            self.play('stand')
        else:
            self.action = self.pending = ""
            self.elapsed = 0.
            self.fall=None
            self.body_return=[current,0.,.22]
        self.after_land=''
        self.sleeping = self.speech = self.listening = False
        self.expression = "neutral"
        self.face_requested=False
        self.face_reasons.clear()
        self.settling=None
        self.head_start=0.
        self.head_return=[current.look_back,0.] if current.look_back>0 else None
        self.hand_return=[current.hands,0.]
        if current.blend_view and current.view_mix>0:
            target=1 if current.view_mix>=.5 else 0
            self.view=current.blend_view if target else current.view
            self.settling=[current.view,current.blend_view,current.view_mix,target,0.]

    def advance(self, dt):
        if self.paused:
            return self.pose()
        dt = clamp(dt, 0, .1) * self.speed
        self.clock += dt
        if self.face_transition:
            self.face_transition[1]+=dt
            if self.face_transition[1]>=.16:self.face_transition=None
        self.speech_amount=clamp(self.speech_amount+(dt/.12 if self.speech else -dt/.12))
        self.lid=clamp(self.lid+(dt/.22 if self.sleeping else -dt/.22))
        if self.body_return:
            self.body_return[1]+=dt
            if self.body_return[1]>=self.body_return[2]:self.body_return=None
        if self.hand_return:
            self.hand_return[1]+=dt
            if self.hand_return[1]>=.18:self.hand_return=None
        if self.head_return:
            self.head_return[1]+=dt
            if self.head_return[1]>=.18:self.head_return=None
        emotion_target=self.expression in ("angry","scared")
        self.emotion=clamp(self.emotion+(dt/.18 if emotion_target else -dt/.18))
        carrying=self.action=="carried" or self.pending=="carried"
        self.carry=clamp(self.carry+(dt/.22 if carrying else -dt/.22))
        action_dt=dt
        if self.settling:
            remaining=max(0,.12-self.settling[4])
            self.settling[4]+=dt
            action_dt=max(0,dt-remaining)
            if self.settling[4]>=.12:self.settling=None
        self._consume_face_request()
        if self.action:
            self.elapsed += action_dt
            duration = MOTIONS[self.action][1]+(self.fall['duration'] if self.fall else 0.)
            p = clamp(self.elapsed / duration)
            target = 1. if self.action in ("sit", "sleep") else 0.
            self.seat = self.start_seat + (target-self.start_seat)*smooth(p)
            if self.action == "turn":
                order = list(VIEWS)
                start, end = order.index(self.turn_from), order.index(self.turn_to)
                delta = (end-start) % 8
                if delta > 4:
                    delta -= 8
                step = min(abs(delta), int(turn_progress(p)*abs(delta)))
                self.view = order[(start + (step if delta >= 0 else -step)) % 8]
            if self.action == "spin":
                order = list(VIEWS)
                self.view = order[(order.index(self.turn_from) + int(turn_progress(p)*8)) % 8]
            if p >= 1 and self.action != "carried":
                old = self.action
                ended=self.pose()
                if ended.expression!=self.expression:self.face_transition=[ended.face_weights or {ended.expression:1.},0.]
                self.action = ""
                self.fall=None
                if old == "spin":
                    self.view = self.turn_from
                if self.pending:
                    pending, self.pending = self.pending, ""
                    self.play(pending)
                if self.face_requested:
                    self._consume_face_request()
                if old=='land' and self.after_land:
                    following,self.after_land=self.after_land,''
                    self.play(following)
        physical=self.pose()
        target=physical.head_yaw*.5+physical.head_pitch*.35+physical.transforms['head'].get('a',0)*.7+physical.root_angle
        acceleration=50*(target-self.hair_follow)-12*self.hair_velocity
        self.hair_velocity+=acceleration*dt;self.hair_follow+=self.hair_velocity*dt
        return self.pose()

    def pose(self):
        t = self.clock
        a = self.action
        motion_elapsed=max(0,self.elapsed-(self.fall['duration'] if self.fall else 0.))
        p = clamp(motion_elapsed / MOTIONS[a][1]) if a else 0
        env = smooth(p/.18) * (1-smooth((p-.78)/.22)) if a else 0
        beat = math.sin(t*2)
        pose = Pose(expression=self.expression, view=self.view, seat=self.seat, gaze=self.gaze,
                    speech=self.speech_amount*(math.sin(math.pi*((t*3.8)%1)/.76)**2 if (t*3.8)%1<.76 else 0.),
                    phase=p,time=t,motion=a,hair=math.sin(t*1.7)*3,cloth=math.sin(t*1.3))
        if a in ("turn","spin"):
            order=list(VIEWS);start=order.index(self.turn_from)
            delta=8 if a=="spin" else (order.index(self.turn_to)-start)%8
            if a=="turn" and delta>4:delta-=8
            position=turn_progress(p)*abs(delta);step=int(position);direction=1 if delta>=0 else -1
            pose.turn_tail=smooth(p/.15)*(1-smooth((p-.85)/.15))
            if step<abs(delta):
                pose.blend_view=order[(start+direction*(step+1))%8]
                pose.view_mix=smooth(position-step)
        if self.settling:
            first,second,start,target,elapsed=self.settling
            pose.view=first;pose.blend_view=second
            pose.view_mix=start+(target-start)*smooth(elapsed/.12)
        # Natural blink, 180 ms every 4.6 s, no wall-clock random jitter in previews.
        blink_phase = t % 4.6
        pose.blink = max(0., 1-abs(blink_phase-3.9)/.09)
        pose.blink=max(pose.blink,self.lid)
        pose.eye_closed = self.lid>=.999
        if self.sleeping:
            pose.expression = "sleepy"
        pose.root_y = math.sin(t*1.9)*1.7
        tr = pose.transforms
        low = self.seat*54
        tr["upper"] = {"y": low, "sy": 1+math.sin(t*1.9)*.003}
        tr["head"] = {"a": 2.5 if self.expression == "confused" else 0}
        tr["tail"] = {"a": math.sin(t*2.8)*(10 if self.expression in ("happy", "excited", "love") else 5), "y": low*.25}
        tr["wingFar"] = {"a": math.sin(t*2.3)*4}
        tr["wingNear"] = {"a": -math.sin(t*2.3)*4}
        tr["hairBack"] = {"warp": pose.hair}
        tr["hairFront"] = {"warp": pose.hair*.35}
        tr["ahoge"] = {"a": math.sin(t*2.1)*5}
        for name in ("legFar", "legNear", "armFar", "armNear", "skirtFar", "skirtNear", "apron", "seat"):
            tr[name] = {"a": 0, "y": low*(1 if name in ("apron", "seat") else .55 if name.startswith("skirt") else 0)}
        tr["armFar"]["a"], tr["armNear"]["a"] = beat*1.4, -beat*1.4
        if a in ("jump", "hop", "flap", "toss"):
            height = {"jump": 145, "hop": 60, "flap": 35, "toss": 180}[a]
            flight = math.sin(math.pi*clamp((p-.12)/.72))
            pose.root_y -= height*flight
            squat = 13*math.sin(math.pi*clamp(p/.12)) if p < .12 else 12*math.sin(math.pi*clamp((p-.84)/.16))
            tr["upper"]["y"] += squat
            tr["armNear"]["a"] -= 45*flight
            tr["armFar"]["a"] += 35*flight
            if a == "toss":
                pose.root_angle = math.sin(math.pi*p)*14
                pose.root_x = math.sin(math.pi*p)*35
        if a in ("walk", "run", "dance"):
            frequency = 10 if a == "run" else 7 if a == "dance" else 5
            stride = math.sin(t*frequency)*env
            amplitude = 25 if a == "run" else 16
            tr["legFar"]["a"], tr["legNear"]["a"] = stride*amplitude, -stride*amplitude
            tr["armFar"]["a"], tr["armNear"]["a"] = -stride*22, stride*22
            tr["skirtFar"]["a"], tr["skirtNear"]["a"] = stride*3, -stride*3
            pose.cloth+=math.sin(t*frequency-.65)*(14 if a=='run' else 9)*env
            if self.view in ('front','back') and a!='dance':
                # Depth-facing steps shorten/lift alternately. A sagittal kick
                # rendered as a large screen rotation reads as sideways splits.
                for node,phase in (('legFar',stride),('legNear',-stride)):
                    tr[node]['a']=phase*1.5
                    tr[node]['sy']=1-(.09 if a=='run' else .055)*max(0,phase)
                tr['armFar']['a'],tr['armNear']['a']=-stride*8,stride*8
            pose.root_y -= abs(math.sin(t*frequency))*7*env
            if a == "run":
                direction=1 if self.view in ("right","front-right","back-right") else -1
                if self.view in ("front","back"):
                    tr["upper"]["sy"]*=1-.025*env
                    tr["head"]["y"]=4*env
                else:
                    tr["upper"]["a"] = direction*10*env
                if self.view not in ('front','back'):
                    tr["armNear"]["a"],tr["armFar"]["a"]=direction*38*env,direction*32*env
            if a == "dance":
                pose.gesture=env
                pose.root_angle = stride*6
                tr["head"]["a"] -= stride*7
                tr["armFar"]["a"] += 35*env
                tr["armNear"]["a"] -= 65*env
        if a == "look":
            pose.gaze = (math.sin(p*math.pi*2)*.9, -.2)
            tr["head"]["a"] = math.sin(p*math.pi*2)*6
        if a=="look-back":
            pose.look_back=(self.head_start+(1-self.head_start)*smooth(p/.18))*(1-smooth((p-.78)/.22))
            tr["head"]["a"]+=(-3 if self.view=="back-left" else 3)*env
        elif self.head_return:
            pose.look_back=self.head_return[0]*(1-smooth(self.head_return[1]/.18))
        if a == "nod":
            pulse=math.sin(p*math.pi*4)*env
            tr["head"]["a"] = pulse*(4 if self.view in ("right","front-right") else -4 if self.view in ("left","front-left") else 0)
            tr["head"]["y"] = pulse*7
            tr["head"]["sy"] = 1-.018*pulse
        if a == "shake":
            tr["head"]["x"] = math.sin(p*math.pi*6)*10*env
            tr["head"]["a"] = math.sin(p*math.pi*6)*3*env
        if a.startswith("tilt-"):
            tr["head"]["a"] = (-12 if a == "tilt-left" else 12)*env
        if a in ("wave", "raise-left", "raise-right", "raise-both", "point"):
            (left,ls),(right,rs)=HAND_BINDINGS[self.view]
            pose.gesture=env
            if a in ("wave", "raise-left", "raise-both"):
                tr[left]["a"] = ls*(110+(math.sin(p*math.pi*12)*12 if a == "wave" else 0))*env
            if a in ("raise-right", "raise-both"):
                tr[right]["a"] = rs*110*env
            if a == "point":
                tr[left]["a"] = ls*145*env
                tr["head"]["a"] = -5*env
                pose.gaze = (0, -.7)
        if a in HAND_GESTURES:
            left=env if a in ('wave','raise-left','raise-both','point','dance') else 0.
            right=env if a in ('raise-right','raise-both','dance') else 0.
            sway=math.sin(p*math.pi*4)*12*env if a in ('wave','dance') else 0.
            pose.hands=(left,right,env if a=='point' else 0.,sway)
        if self.hand_return:
            start,elapsed=self.hand_return;amount=smooth(elapsed/.18)
            pose.hands=tuple(x+(y-x)*amount for x,y in zip(start,pose.hands))
        if a == "bow":
            direction=1 if self.view=="right" else -1
            tr["upper"]["a"] = direction*22*math.sin(math.pi*p)**2
            tr["head"]["a"] = direction*8*env
            pose.eye_closed = True
        emotion=self.emotion*(1-env if a else 1)
        tr["armFar"]["a"]-=10*emotion
        tr["armNear"]["a"]+=12*emotion
        pose.root_x+=math.sin(t*45)*(2*self.emotion*(1-env if a=="shiver" else 1)+ (4*env if a=="shiver" else 0))
        if a=="shiver":
            tr["armFar"]["a"]-=10*env
            tr["armNear"]["a"]+=12*env
        if a == "flap":
            flap = math.sin(p*math.pi*12)*env
            tr["wingFar"]["a"], tr["wingNear"]["a"] = flap*30, -flap*30
        if a == "dizzy":
            pose.expression = "dizzy"
            pose.root_angle = math.sin(t*7)*7*env
        carry=smooth(self.carry)
        if carry:
            pose.root_angle+=math.sin(t*9)*8*carry
            pose.root_y-=30*carry
            for node,angle in (("armFar",60),("armNear",-80),("legFar",-12),("legNear",18)):
                tr[node]["a"]=tr[node]["a"]*(1-carry)+angle*carry
        if a == "land":
            tr["upper"]["y"] += math.sin(math.pi*p)*22
            pose.hair += math.sin(p*math.pi*3)*8*(1-p)
            pose.cloth+=math.sin(p*math.pi*3)*5*(1-p)
        if a == "pet":
            pose.expression = "happy"
            tr["head"]["a"] = math.sin(p*math.pi*3)*4*env
        if a == "poke":
            pose.expression = "surprised"
            pose.root_x += math.sin(p*math.pi)*12
        if self.listening:
            tr["head"]["a"] += 5
        tr["hairBack"]["warp"]=pose.hair
        tr["hairFront"]["warp"]=pose.hair*.35
        pose=perform(pose,motion_elapsed,MOTIONS[a][1] if a else 1.,smooth(self.carry),self.seat,self.listening)
        pose.point_target=self.point_target
        target=pose.head_yaw*.5+pose.head_pitch*.35+pose.transforms['head'].get('a',0)*.7+pose.root_angle
        pose.hair+=(target-self.hair_follow)*.6
        if self.fall and self.elapsed<max(.14,self.fall['duration']):
            start=self.fall['start'];t=self.elapsed
            ready=smooth(t/max(.14,self.fall['duration']))
            source=start
            if 'run_elapsed' in self.fall:
                elapsed=self.fall['run_elapsed']+t
                continuation=Pose(view=start.view,motion='run',phase=clamp(elapsed/MOTIONS['run'][1]),time=self.clock,
                                  transforms={node:{} for node in start.transforms})
                continuation=perform(continuation,elapsed,MOTIONS['run'][1],0.,0.)
                transforms={**start.transforms}
                for node in ('upper','armFar','armNear'):
                    transforms[node]={**start.transforms[node],**continuation.transforms[node]}
                source=replace(start,transforms=transforms,root_x=continuation.root_x,pelvis=continuation.pelvis,
                               legs=continuation.legs,contacts=continuation.contacts,arm_base=continuation.arm_base,
                               tail_energy=continuation.tail_energy)
            gravity=self.fall['gravity']
            y=self.fall['height']+self.fall['velocity']*t+gravity*t*t/2
            velocity=self.fall['velocity']+gravity*t
            if 'run_elapsed' in self.fall:y,velocity,_=run_flight(self.fall['run_elapsed']+t,MOTIONS['run'][1])
            flying=t<self.fall['duration']
            pose=replace(blend_pose(source,pose,ready),time=self.clock,motion='toss' if self.fall.get('release') else 'land',airborne=flying,
                root_y=min(0.,y) if flying else 0.,
                root_angle=start.root_angle*(1-ready),root_anchor=(425.,start.root_anchor[1]+(969-start.root_anchor[1])*ready),
                vertical_velocity=velocity if flying else 0.,head_pitch=start.head_pitch*(1-ready),head_yaw=start.head_yaw*(1-ready))
            pose.contacts=(False,False) if flying else tuple(abs(pose.legs[node]['y'])<1 for node in ('legFar','legNear'))
        elif self.body_return:
            start,elapsed,duration=self.body_return
            pose=blend_pose(start,pose,smooth(elapsed/duration))
        pose.transforms['hairBack']['warp']=pose.hair;pose.transforms['hairFront']['warp']=pose.hair*.35
        if self.face_transition:
            old,elapsed=self.face_transition;amount=smooth(elapsed/.16)
            pose.face_weights={name:weight*(1-amount) for name,weight in old.items()}
            pose.face_weights[pose.expression]=pose.face_weights.get(pose.expression,0.)+amount
        return pose


def blend_pose(first,second,amount):
    """Blend every physical channel, preserving authored view/action identity."""
    def value(a,b,key=''):
        if isinstance(a,dict) or isinstance(b,dict):
            a=a if isinstance(a,dict) else {};b=b if isinstance(b,dict) else {}
            return {k:value(a.get(k,1. if k in ('sx','sy') else 0.),b.get(k,1. if k in ('sx','sy') else 0.),k) for k in a.keys()|b.keys()}
        if isinstance(a,(tuple,list)) and isinstance(b,(tuple,list)):
            return tuple(value(x,y) for x,y in zip(a,b))
        if type(a) in (int,float) and type(b) in (int,float):return a+(b-a)*amount
        return b
    keys=('transforms','root_x','root_y','root_angle','root_anchor','pelvis','legs','seat','head_pitch','head_yaw','gaze','hands','arm_base','tail_energy','hair','cloth','blink','turn_tail')
    contacts=tuple(a and b for a,b in zip(first.contacts,second.contacts)) if amount<.999 else second.contacts
    return replace(second,contacts=contacts,**{k:value(getattr(first,k),getattr(second,k)) for k in keys})
