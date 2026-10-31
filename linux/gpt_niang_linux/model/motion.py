"""Deterministic pose evaluation, independent of Qt, wall time and quota polling."""
from dataclasses import dataclass, field
import math

EXPRESSIONS = dict(zip(
    "neutral happy wink love shy surprised angry sad sleepy thinking smug pout worried determined flustered scared excited cry confused".split(),
    "平静 开心 眨眼 喜欢 害羞 惊讶 生气 难过 犯困 思考 得意 嘟嘴 担心 认真 慌张 害怕 期待 大哭 疑惑".split()))
MOTIONS = {
    "stand": ("站起", 1.2), "jump": ("跳", 1.2), "hop": ("小跳", .9), "look": ("张望", 2.7),
    "turn": ("转身", .4), "nod": ("点头", .8), "shake": ("摇头", .8), "spin": ("转圈", .8),
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

    def set_expression(self, value):
        if value not in EXPRESSIONS:
            return False
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
        resume=self.action
        self.play("turn")
        self.turn_to="front-right" if self.view=="back-right" else "front-left"
        self.pending=resume

    def set_view(self, value):
        if value not in VIEWS:
            return False
        self.view = value
        self.settling=None
        self.head_return=None
        self.hand_return=None
        return True

    def play(self, action):
        if action not in MOTIONS:
            return False
        previous=self.pose()
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
        return True

    def cancel(self):
        current=self.pose()
        self.action = self.pending = ""
        self.elapsed = self.seat = 0.
        self.sleeping = self.speech = self.listening = False
        self.expression = "neutral"
        self.carry = 0.
        self.emotion = 0.
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
            duration = MOTIONS[self.action][1]
            p = clamp(self.elapsed / duration)
            target = 1. if self.action in ("sit", "sleep") else 0.
            self.seat = self.start_seat + (target-self.start_seat)*smooth(p)
            if self.action == "turn":
                order = list(VIEWS)
                start, end = order.index(self.turn_from), order.index(self.turn_to)
                delta = (end-start) % 8
                if delta > 4:
                    delta -= 8
                step = min(abs(delta), int(p*abs(delta)))
                self.view = order[(start + (step if delta >= 0 else -step)) % 8]
            if self.action == "spin":
                order = list(VIEWS)
                self.view = order[(order.index(self.turn_from) + int(p*8)) % 8]
            if p >= 1 and self.action != "carried":
                old = self.action
                self.action = ""
                if old == "spin":
                    self.view = self.turn_from
                if self.pending:
                    pending, self.pending = self.pending, ""
                    self.play(pending)
                if self.face_requested:
                    self._consume_face_request()
        return self.pose()

    def pose(self):
        t = self.clock
        a = self.action
        p = clamp(self.elapsed / MOTIONS[a][1]) if a else 0
        env = smooth(p/.18) * (1-smooth((p-.78)/.22)) if a else 0
        beat = math.sin(t*2)
        pose = Pose(expression=self.expression, view=self.view, seat=self.seat, gaze=self.gaze,
                    speech=(.35+.65*abs(math.sin(t*12))) if self.speech else 0,
                    phase=p,time=t,motion=a,hair=math.sin(t*1.7)*3,cloth=math.sin(t*1.3))
        if a in ("turn","spin"):
            order=list(VIEWS);start=order.index(self.turn_from)
            delta=8 if a=="spin" else (order.index(self.turn_to)-start)%8
            if a=="turn" and delta>4:delta-=8
            position=p*abs(delta);step=int(position);direction=1 if delta>=0 else -1
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
        pose.eye_closed = self.sleeping
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
            sway=math.sin(p*math.pi*(12 if a=='wave' else 8))*12*env if a in ('wave','dance') else 0.
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
        return pose
