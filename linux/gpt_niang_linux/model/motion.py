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
}
VIEWS = dict(zip("front front-left left back-left back back-right right front-right".split(),
                 "正面 左前侧 左侧面 左后侧 背面 右后侧 右侧面 右前侧".split()))


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
    tear: float = 0
    phase: float = 0
    time: float = 0
    motion: str = ""
    eye_closed: bool = False


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

    def set_expression(self, value):
        if value not in EXPRESSIONS:
            return False
        if self.view not in ("front", "front-left", "front-right"):
            self.set_view("front-left")
        self.expression = value
        return True

    def set_view(self, value):
        if value not in VIEWS:
            return False
        self.view = value
        return True

    def play(self, action):
        if action not in MOTIONS:
            return False
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
        # Face-dependent gestures return to a readable view first.
        if action not in ("turn", "spin", "walk", "run", "stand", "raise-left", "raise-right", "raise-both", "carried", "land", "toss"):
            if self.view not in ("front", "front-left", "front-right"):
                self.pending = action
                self.turn_from, self.turn_to = self.view, "front-left"
                self.action = "turn"
        return True

    def cancel(self):
        self.action = self.pending = ""
        self.elapsed = self.seat = 0.
        self.sleeping = self.speech = self.listening = False
        self.expression = "neutral"

    def advance(self, dt):
        if self.paused:
            return self.pose()
        dt = clamp(dt, 0, .1) * self.speed
        self.clock += dt
        if self.action:
            self.elapsed += dt
            duration = MOTIONS[self.action][1]
            p = clamp(self.elapsed / duration)
            target = 1. if self.action in ("sit", "sleep") else 0.
            self.seat = self.start_seat + (target-self.start_seat)*smooth(p)
            if self.action == "turn" and p >= .5:
                self.view = self.turn_to
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
        return self.pose()

    def pose(self):
        t = self.clock
        a = self.action
        p = clamp(self.elapsed / MOTIONS[a][1]) if a else 0
        env = smooth(p/.18) * (1-smooth((p-.78)/.22)) if a else 0
        beat = math.sin(t*2)
        pose = Pose(expression=self.expression, view=self.view, seat=self.seat, gaze=self.gaze,
                    speech=(.35+.65*abs(math.sin(t*12))) if self.speech else 0,
                    phase=p, time=t, motion=a, hair=math.sin(t*1.7)*3)
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
            pose.root_y -= abs(math.sin(t*frequency))*7*env
            if a == "run":
                tr["upper"]["a"] = -10*env
                tr["armNear"]["a"], tr["armFar"]["a"] = -38*env, -32*env
            if a == "dance":
                pose.root_angle = stride*6
                tr["head"]["a"] -= stride*7
                tr["armFar"]["a"] += 35*env
                tr["armNear"]["a"] -= 65*env
        if a == "look":
            pose.gaze = (math.sin(p*math.pi*2)*.9, -.2)
            tr["head"]["a"] = math.sin(p*math.pi*2)*6
        if a == "nod":
            tr["head"]["a"] = math.sin(p*math.pi*4)*6*env
            tr["head"]["y"] = math.sin(p*math.pi*4)*7*env
        if a == "shake":
            tr["head"]["x"] = math.sin(p*math.pi*6)*10*env
            tr["head"]["a"] = math.sin(p*math.pi*6)*3*env
        if a.startswith("tilt-"):
            tr["head"]["a"] = (-12 if a == "tilt-left" else 12)*env
        if a in ("wave", "raise-left", "raise-right", "raise-both", "point"):
            if a in ("wave", "raise-left", "raise-both"):
                tr["armNear"]["a"] = -(110+(math.sin(p*math.pi*12)*12 if a == "wave" else 0))*env
            if a in ("raise-right", "raise-both"):
                tr["armFar"]["a"] = 110*env
            if a == "point":
                tr["armNear"]["a"] = -145*env
                tr["head"]["a"] = -5*env
                pose.gaze = (0, -.7)
        if a == "bow":
            tr["upper"]["a"] = -22*math.sin(math.pi*p)**2
            tr["head"]["a"] = -8*env
            pose.eye_closed = True
        if a == "shiver" or self.expression in ("angry", "scared"):
            pose.root_x = math.sin(t*45)*(2 if a != "shiver" else 4*env)
            tr["armFar"]["a"], tr["armNear"]["a"] = -10, 12
        if a == "flap":
            flap = math.sin(p*math.pi*12)*env
            tr["wingFar"]["a"], tr["wingNear"]["a"] = flap*30, -flap*30
        if a == "dizzy":
            pose.expression = "dizzy"
            pose.root_angle = math.sin(t*7)*7*env
        if a == "carried":
            pose.root_angle = math.sin(t*9)*8
            pose.root_y -= 30*env
            tr["armFar"]["a"], tr["armNear"]["a"] = 60, -80
            tr["legFar"]["a"], tr["legNear"]["a"] = -12, 18
        if a == "land":
            tr["upper"]["y"] += math.sin(math.pi*p)*22
            pose.hair += math.sin(p*math.pi*3)*8*(1-p)
        if a == "pet":
            pose.expression = "happy"
            tr["head"]["a"] = math.sin(p*math.pi*3)*4*env
        if a == "poke":
            pose.expression = "surprised"
            pose.root_x += math.sin(p*math.pi)*12
        if self.listening:
            tr["head"]["a"] += 5
        return pose
