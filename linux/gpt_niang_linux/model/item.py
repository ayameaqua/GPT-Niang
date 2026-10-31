"""Quick-facing character controller and compositor."""
import logging
from functools import lru_cache
import math
import time

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot, Qt
from PySide6.QtGui import QBitmap, QImage, QRegion
from PySide6.QtQuick import QQuickPaintedItem

from .assets import model_directory
from .motion import Animator, EXPRESSIONS, HAND_GESTURES, MOTIONS, VIEWS
from .render import DragonRenderer


@lru_cache(maxsize=1)
def shared_renderer(directory):
    # The GUI thread owns the immutable texture set and bounded deformation cache.
    # A preview shares them with the pet; importing new files requires a restart.
    return DragonRenderer(directory)


class DragonItem(QQuickPaintedItem):
    changed = Signal()
    frameReady = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.animator = Animator()
        self.renderer = None
        self._follow = None
        self.error = "未导入 Coopanion v1.1.0 形象包，使用原静态角色"
        self.frame = QImage()
        self.input_region = QRegion()
        self._active = True
        self._debug = False
        self._render_count = 0
        self._render_ms = 0
        self._last = time.monotonic()
        try:
            self.renderer = shared_renderer(model_directory())
            self.error = "Coopanion 龙娘 · Qt 独立分层渲染"
            if self.renderer.view_errors:
                self.error += " · 部分扩展视角加载失败，基底仍可用"
        except (OSError, ValueError, KeyError, TypeError) as error:
            if not isinstance(error, FileNotFoundError):
                self.error = "模型资源无效，已回退静态角色；请核对或重新导入固定形象包"
            logging.info("Layered model unavailable (%s)", type(error).__name__)
        self.setAntialiasing(True)
        self.widthChanged.connect(self.render_frame)
        self.heightChanged.connect(self.render_frame)
        self.timer = QTimer(self, interval=33)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    @Property(QObject, notify=changed)
    def follow(self):
        return self._follow

    @follow.setter
    def follow(self, source):
        if self._follow:
            self._follow.frameReady.disconnect(self.render_frame)
        self._follow = source
        if source:
            self.animator = source.animator
            self.renderer = source.renderer
            self.timer.stop()
            source.frameReady.connect(self.render_frame)
        self.render_frame()
        self.changed.emit()

    @Property(bool, notify=changed)
    def available(self):
        return self.renderer is not None

    @Property(str, notify=changed)
    def status(self):
        return self.error

    @Property(bool, notify=changed)
    def active(self):
        return self._active

    @active.setter
    def active(self, value):
        if value == self._active:
            return
        self._active = value
        if value:
            self._last = time.monotonic()
            if not self._follow:
                self.timer.start()
            self.render_frame()
        else:
            self.timer.stop()
            if not self._follow:
                self.animator.cancel()
        self.changed.emit()
        self.frameReady.emit()

    @Property('QVariantList', constant=True)
    def expressions(self):
        return [{"id": key, "name": name} for key, name in EXPRESSIONS.items()]

    def turns_ready(self):
        return bool(self.renderer and all(v in self.renderer.rigs for v in VIEWS if v != "front-left"))

    @Property('QVariantList', constant=True)
    def motions(self):
        return [{"id":key,"name":spec[0],"ready":self.motion_ready(key)} for key,spec in MOTIONS.items()]

    def motion_ready(self,value):
        if not self.renderer or value not in MOTIONS:
            return False
        if value in ("turn","spin"):
            return self.turns_ready()
        if value in HAND_GESTURES:
            rig=self.renderer.rigs.get("front")
            if not rig:return False
            parts={p['id']:p for p in rig[0]['parts']}
            kind="point" if value=="point" else "raised"
            arms=("arm-far",) if value=="raise-right" else ("arm-near","arm-far") if value in ("raise-both","dance") else ("arm-near",)
            return all(parts.get(arm,{}).get('articulation') or kind in parts.get(arm,{}).get("variants",{}) for arm in arms)
        if value=="bow":
            return all(v in self.renderer.rigs for v in ("left","right"))
        if value=="look-back":
            return all(v in self.renderer.rigs for v in ("back-left","back-right","left","right"))
        return True

    @Property('QVariantList', notify=changed)
    def views(self):
        names = set(self.renderer.rigs) | {"front-left"} if self.renderer else set()
        return [{"id": key, "name": name + (" · 试验" if key in names and key != "front-left" else ""), "ready": key in names} for key, name in VIEWS.items()]

    @Property(str, notify=changed)
    def expression(self):
        return self.animator.expression

    @Property(str, notify=changed)
    def orientation(self):
        return self.animator.view

    @Property(str, notify=changed)
    def motion(self):
        return self.animator.action

    @Property(bool, notify=changed)
    def paused(self):
        return self.animator.paused

    @Property(float, notify=changed)
    def speed(self):
        return self.animator.speed

    @Property(bool, notify=changed)
    def speaking(self):
        return self.animator.speech

    @Property(bool, notify=changed)
    def listening(self):
        return self.animator.listening

    @Property(bool, notify=changed)
    def debug(self):
        return self._debug

    @Slot(str)
    def setExpression(self, value):
        if self.animator.set_expression(value):
            self._ensure_view()
            self.render_frame()
            self.changed.emit()

    @Slot(str)
    def setView(self, value):
        if value != "front-left" and (not self.renderer or value not in self.renderer.rigs):
            return
        self.animator.cancel()
        if self.animator.set_view(value):
            self.animator.speech = self.animator.listening = False
            self.animator.action = self.animator.pending = ""
            self.render_frame()
            self.changed.emit()

    @Slot(str)
    def play(self, value):
        if not self.motion_ready(value):
            return
        if self.animator.play(value):
            self.changed.emit()
            self.render_frame()

    @Slot()
    def reset(self):
        self.animator.cancel()
        self.render_frame()
        self.changed.emit()

    @Slot(bool)
    def setPaused(self, value):
        self.animator.paused = value
        self.changed.emit()

    @Slot(float)
    def setSpeed(self, value):
        self.animator.speed = max(.1, min(2., value))
        self.changed.emit()

    @Slot(bool)
    def setDebug(self, value):
        self._debug = value
        self.render_frame()
        self.changed.emit()

    @Slot(bool)
    def setSpeaking(self, value):
        self.animator.request_face_view("speech",value)
        self.animator.speech = value
        self.changed.emit()
        self.render_frame()

    @Slot(bool)
    def setListening(self, value):
        self.animator.request_face_view("listening",value)
        self.animator.listening = value
        self.changed.emit()
        self.render_frame()

    @Slot(float, float)
    def lookAt(self, x, y):
        self.animator.gaze = (max(-1., min(1., x)), max(-1., min(1., y)))

    def _ensure_view(self):
        if self.renderer and self.animator.view not in self.renderer.rigs and self.animator.view != "front-left":
            self.animator.view = "front-left"

    def tick(self):
        now = time.monotonic()
        dt, self._last = now-self._last, now
        if not self.renderer or not self._active or self.animator.paused:
            return
        old = (self.animator.action, self.animator.view)
        if not self._follow:
            self.animator.advance(dt)
        self._ensure_view()
        self.render_frame()
        if old != (self.animator.action, self.animator.view):
            self.changed.emit()

    @Slot()
    def render_frame(self):
        if not self.renderer or not self._active or self.width() < 1 or self.height() < 1:
            return
        start = time.monotonic()
        # Render at the actual output DPR, bounded by the source design resolution.
        # The mask stays in logical coordinates; no screenshot/GPU readback is used.
        dpr = self.window().devicePixelRatio() if self.window() else 1.
        resolution = min(1280, max(1, math.ceil(self.width()*dpr)))
        self.frame = self.renderer.render(self.animator.pose(), resolution,
            max(1, round(resolution*self.height()/self.width())), self._debug)
        logical = self.frame.scaled(round(self.width()), round(self.height()),
            Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        mask = logical.createAlphaMask(Qt.ImageConversionFlag.ThresholdAlphaDither)
        self.input_region = QRegion(QBitmap.fromImage(mask))
        self._render_count += 1
        self._render_ms += (time.monotonic()-start)*1000
        self.update()
        self.frameReady.emit()

    def paint(self, painter):
        if self._active and not self.frame.isNull():
            painter.drawImage(self.boundingRect(), self.frame)
