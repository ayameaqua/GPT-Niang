"""Ordinary xdg-shell window. KWin owns placement; Qt owns size and input."""
import math

from PySide6.QtCore import QObject, Property, QEvent, QRect, QTimer, Signal, Slot
from PySide6.QtGui import QBitmap, QColor, QGuiApplication, QImage, QRegion

from .paths import ASSETS


def alpha_region(image, width, height, threshold=16):
    """Build a logical-pixel input region, preserving transparent internal holes."""
    scaled = image.scaled(width, height).convertToFormat(QImage.Format.Format_ARGB32)
    # A one-bit bitmap is cheap for QRegion; avoid a bounding rectangle over the PNG.
    mask = QImage(width, height, QImage.Format.Format_Mono)
    # QBitmap's color1 is black. An indexed image's default color1 is white,
    # which fromImage() otherwise inverts and makes transparent pixels clickable.
    mask.setColorTable([QColor("white").rgba(), QColor("black").rgba()])
    mask.fill(0)
    for y in range(height):
        for x in range(width):
            if scaled.pixelColor(x, y).alpha() >= threshold:
                mask.setPixel(x, y, 1)
    return QRegion(QBitmap.fromImage(mask))


class WindowBackend(QObject):
    changed = Signal()
    petClicked = Signal()
    dragStarted = Signal()
    dragEnded = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = None
        self.renderer = None
        self.image = QImage(str(ASSETS / "gpt-dragon-niang-bust.png"))
        if self.image.isNull():
            raise RuntimeError("角色素材缺失")
        self.layout = None
        self.cached_size = None
        self.cached_region = None
        self.state = "idle"
        self.press = (0, 0)
        self.release_watchdog = QTimer(self, interval=1500, singleShot=True)
        self.release_watchdog.timeout.connect(self.cancelPointer)

    @Property(str, constant=True)
    def platform(self):
        return QGuiApplication.platformName()

    @Property(str, constant=True)
    def placementStatus(self):
        return "位置由 KDE 管理；请安装专用记忆规则。实际恢复效果需在 KDE 会话验证。"

    @Property(bool, notify=changed)
    def pressed(self):
        return self.state == "pressed"

    @Property(float, constant=True)
    def imageAspect(self):
        return self.image.width() / self.image.height()

    def attach(self, window):
        self.window = window
        window.installEventFilter(self)
        window.screenChanged.connect(self.rebuild)

    def attach_renderer(self, renderer):
        self.renderer = renderer
        renderer.frameReady.connect(self.rebuild)

    @Slot(float, float, float, float, bool, float, float, float, float)
    def updateMask(self, x, y, width, height, bubble, bx, by, bw, bh):
        self.layout = (x, y, width, height, bubble, bx, by, bw, bh)
        self.rebuild()

    @Slot()
    def rebuild(self, *_):
        if not self.window or not self.layout:
            return
        x, y, width, height, bubble, bx, by, bw, bh = self.layout
        size = (max(1, math.ceil(width)), max(1, math.ceil(height)))
        if size != self.cached_size:
            self.cached_size = size
            self.cached_region = alpha_region(self.image, *size)
        if self.renderer and self.renderer.active and self.renderer.available and self.renderer.isVisible():
            region = self.renderer.input_region.translated(round(x), round(y))
        else:
            region = self.cached_region.translated(round(x), round(y))
        if bubble:
            # Rounded bubble corners stay transparent. Controls are contained within it.
            rect = QRect(round(bx), round(by), math.ceil(bw), math.ceil(bh))
            rounded = QRegion(rect.adjusted(12, 0, -12, 0)) | QRegion(rect.adjusted(0, 12, 0, -12))
            for cx, cy in ((rect.left(), rect.top()), (rect.right() - 23, rect.top()),
                           (rect.left(), rect.bottom() - 23), (rect.right() - 23, rect.bottom() - 23)):
                rounded |= QRegion(QRect(cx, cy, 24, 24), QRegion.RegionType.Ellipse)
            region |= rounded
        # Qt interprets an empty mask as removing the mask, so retain a nonempty fallback.
        self.window.setMask(region if not region.isEmpty() else QRegion(QRect(round(x), round(y), 1, 1)))

    @Slot(float, float)
    def pointerPress(self, x, y):
        self.release_watchdog.stop()
        self.press = (x, y)
        self.state = "pressed"
        self.changed.emit()

    @Slot(float, float)
    def pointerMove(self, x, y):
        if self.state != "pressed":
            return
        threshold = QGuiApplication.styleHints().startDragDistance()
        if math.hypot(x - self.press[0], y - self.press[1]) < threshold:
            return
        # Mark moving before the compositor takes the grab. No click on a failed move.
        self.state = "moving"
        self.changed.emit()
        self.dragStarted.emit()
        self.window.startSystemMove()
        self.release_watchdog.start()

    @Slot()
    def pointerRelease(self):
        clicked = self.state == "pressed"
        self.cancelPointer()
        if clicked:
            self.petClicked.emit()

    @Slot()
    def cancelPointer(self):
        moving = self.state == "moving"
        self.release_watchdog.stop()
        self.state = "idle"
        self.changed.emit()
        if moving:
            self.dragEnded.emit()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.WindowDeactivate, QEvent.Type.UngrabMouse, QEvent.Type.Hide):
            self.cancelPointer()
        if event.type() in (QEvent.Type.DevicePixelRatioChange,):
            QTimer.singleShot(0, self.rebuild)
        return super().eventFilter(watched, event)
