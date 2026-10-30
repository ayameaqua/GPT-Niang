"""Source checkout entry point; no system Python or Qt plugins are modified."""
import argparse
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import random
import signal
import sys

import PySide6
from PySide6.QtCore import ClassInfo, QObject, Property, QTimer, QUrl, Signal, Slot, qVersion
from PySide6.QtDBus import QDBusConnection, QDBusInterface
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtQuick import QQuickWindow

from . import __version__
from .paths import APP_ID, ASSETS, LINUX_ROOT, resolve_executable, xdg_path
from .quota_controller import QuotaController
from .settings import Settings
from .window_backend import WindowBackend


@ClassInfo(**{"D-Bus Interface": "org.gptniang.Linux.Control1"})
class Preferences(QObject):
    changed = Signal()
    settingsRequested = Signal()
    modelPreviewRequested = Signal()
    quoteChanged = Signal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.store = settings
        self.notice_text = settings.warning
        self.quote_text = "Ciallo～ 今天也请多关照。"
        payload = json.loads((ASSETS / "quotes.json").read_text(encoding="utf-8"))
        self.quotes = [quote for quote in payload["quotes"] if isinstance(quote.get("text"), str)]

    @Property(float, notify=changed)
    def scale(self):
        return self.store.values["scale"]

    @Property(bool, notify=changed)
    def quotesEnabled(self):
        return self.store.values["quotesEnabled"]

    @Property(str, notify=changed)
    def nodePath(self):
        return self.store.values["nodePath"]

    @Property(str, notify=changed)
    def codexPath(self):
        return self.store.values["codexPath"]

    @Property(str, notify=changed)
    def notice(self):
        return self.notice_text

    @Property(str, notify=quoteChanged)
    def quote(self):
        return self.quote_text

    @Property(bool, notify=changed)
    def modelEnabled(self):
        return self.store.values["modelEnabled"]

    @Slot(bool)
    def setModelEnabled(self, enabled):
        self.save(modelEnabled=enabled)

    @Property(str, constant=True)
    def characterUrl(self):
        return QUrl.fromLocalFile(str(ASSETS / "gpt-dragon-niang-bust.png")).toString()

    @Property(str, constant=True)
    def version(self):
        return __version__

    def save(self, **changes):
        try:
            self.store.save(**changes)
            self.notice_text = "设置已保存"
        except OSError:
            self.notice_text = "无法保存设置，请检查配置目录权限。"
        self.changed.emit()

    @Slot(float)
    def setScale(self, value):
        self.save(scale=value)

    @Slot(bool)
    def setQuotesEnabled(self, enabled):
        self.save(quotesEnabled=enabled)

    @Slot(str, str)
    def setPaths(self, node, codex):
        self.save(nodePath=node.strip(), codexPath=codex.strip())

    @Slot()
    def detectPaths(self):
        self.save(nodePath=resolve_executable("node"), codexPath=resolve_executable("codex"))

    @Slot()
    def nextQuote(self):
        if self.quotes:
            self.quote_text = random.choices(self.quotes, weights=[max(0.01, float(q.get("weight", 1))) for q in self.quotes])[0]["text"]
            self.quoteChanged.emit()

    @Slot()
    def showSettings(self):
        self.settingsRequested.emit()

    @Slot()
    def showModelPreview(self):
        self.modelPreviewRequested.emit()

    @Slot()
    def openKdeRules(self):
        from PySide6.QtCore import QProcess
        executable = resolve_executable("kcmshell6")
        if executable:
            QProcess.startDetached(executable, ["kcm_kwinrules"])
        else:
            self.notice_text = "未找到 KDE 窗口规则工具，请打开系统设置 → 窗口管理 → 窗口规则。"
            self.changed.emit()


class InstanceLock:
    """Kernel ownership, not a PID file; crash recovery needs no stale-file deletion."""
    def __init__(self):
        root = Path(os.environ.get("XDG_RUNTIME_DIR", f"/tmp/gpt-niang-{os.getuid()}"))
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.stream = (root / "gpt-niang-linux.lock").open("a+")
        os.set_inheritable(self.stream.fileno(), False)

    def acquire(self):
        try:
            fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False


def configure_logging():
    directory = xdg_path("XDG_STATE_HOME", ".local/state") / "gpt-niang"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    handler = RotatingFileHandler(directory / "linux.log", maxBytes=256 * 1024, backupCount=2, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(message)s")


def main(argv=None):
    parser = argparse.ArgumentParser(description="GPT-Niang Linux / Qt Wayland")
    parser.add_argument("--import-model", type=Path, metavar="ZIP", help="import the pinned Coopanion v1.1.0 artwork locally (no JavaScript)")
    parser.add_argument("--model-preview", action="store_true", help="open the animation inspector without querying an account")
    parser.add_argument("--diagnose", action="store_true", help="print safe dependency diagnostics without opening a window")
    parser.add_argument("--settings", action="store_true", help="open preferences (including in an existing instance)")
    parser.add_argument("--smoke-test", action="store_true", help="load all QML without querying an account, then exit")
    parser.add_argument("--quit-after", type=float, default=0, metavar="SECONDS", help="bounded interactive diagnostic run")
    parser.add_argument("--capture", type=Path, help="capture the pet or model preview after startup")
    args = parser.parse_args(argv)
    settings = Settings()
    if args.import_model:
        from .model.assets import import_model
        try:
            print(f"已导入模型：{import_model(args.import_model)}")
            return 0
        except (OSError, ValueError) as error:
            parser.error(str(error))
    if args.diagnose:
        print(json.dumps({"version": __version__, "python": sys.version.split()[0], "pyside": PySide6.__version__,
                          "qt": qVersion(), "session": os.environ.get("XDG_SESSION_TYPE"),
                          "waylandDisplay": os.environ.get("WAYLAND_DISPLAY"),
                          "node": resolve_executable("node", settings.values["nodePath"]),
                          "codex": resolve_executable("codex", settings.values["codexPath"]),
                          "config": str(settings.path), "placement": "KWin Remember rule; effect requires session verification"}, ensure_ascii=False, indent=2))
        return 0
    QGuiApplication.setApplicationName("GPT-Niang Linux")
    QGuiApplication.setApplicationVersion(__version__)
    QGuiApplication.setOrganizationName("GPT-Niang")
    app = QGuiApplication([sys.argv[0]])
    app.setDesktopFileName(APP_ID)
    app.setWindowIcon(QIcon(str(ASSETS / "gpt-dragon-niang-bust.png")))
    app.setQuitOnLastWindowClosed(False)
    lock = InstanceLock()
    if not lock.acquire():
        if args.settings:
            QDBusInterface(APP_ID, "/Controller", "", QDBusConnection.sessionBus()).call("showSettings")
        if args.model_preview:
            QDBusInterface(APP_ID, "/Controller", "", QDBusConnection.sessionBus()).call("showModelPreview")
        print("GPT-Niang 已在此会话运行。使用 --settings 或 --model-preview 打开设置或模型预览。")
        return 0
    configure_logging()
    from .model.item import DragonItem
    qmlRegisterType(DragonItem, "GPTNiang.Model", 1, 0, "DragonModel")
    backend = WindowBackend()
    preferences = Preferences(settings)
    # Capture terminal-discovered paths so desktop launchers can use a minimal PATH.
    discovered = {key: resolve_executable(name, settings.values[key]) for key, name in (("nodePath", "node"), ("codexPath", "codex"))}
    if any(discovered[key] != settings.values[key] for key in discovered):
        preferences.save(**discovered)
    quota = QuotaController(settings)
    bus = QDBusConnection.sessionBus()
    if bus.isConnected() and bus.registerService(APP_ID):
        bus.registerObject("/Controller", preferences, QDBusConnection.RegisterOption.ExportAllSlots)
    engine = QQmlApplicationEngine()
    qml_warnings = []
    engine.warnings.connect(lambda warnings: qml_warnings.extend(str(warning) for warning in warnings))
    context = engine.rootContext()
    context.setContextProperty("preferences", preferences)
    context.setContextProperty("quota", quota)
    context.setContextProperty("windowBackend", backend)
    engine.load(QUrl.fromLocalFile(str(LINUX_ROOT / "gpt_niang_linux/qml/Main.qml")))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]
    backend.attach(window)
    dragon = window.findChild(DragonItem, "dragonRenderer")
    if dragon:
        backend.attach_renderer(dragon)
    QTimer.singleShot(0, backend.rebuild)
    if args.model_preview:
        QTimer.singleShot(50, lambda: window.setProperty("previewVisible", True))
    if args.settings or args.smoke_test:
        QTimer.singleShot(50, preferences.showSettings)
    app.aboutToQuit.connect(quota.shutdown)
    logging.info("Started Linux %s; Qt %s; QPA %s", __version__, qVersion(), backend.platform)
    print(f"GPT-Niang Linux {__version__} | Qt {qVersion()} | QPA={backend.platform}", flush=True)
    # A Qt timer gives Python signal handlers regular opportunities to run.
    signals = QTimer(app, interval=250)
    signals.timeout.connect(lambda: None)
    signals.start()
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    if args.smoke_test:
        def smoke_data():
            import time
            now = int(time.time() * 1000)
            quota.snapshot = {"ok": True, "queryOk": True, "observedAt": now, "planLabel": "演示",
                              "windows": [{"label": "个人额度", "minutes": None, "remaining": 0, "resetsAt": None},
                                          {"label": "5 小时", "minutes": 300, "remaining": 100, "resetsAt": 1},
                                          {"label": "每周", "minutes": 10080, "remaining": 42.5, "resetsAt": None}]}
            quota.message = "界面测试数据（不代表账户额度）"
            quota.changed.emit()
            window.setProperty("bubbleVisible", True)
        QTimer.singleShot(100, smoke_data)
        QTimer.singleShot(1400, app.quit)
    elif not args.model_preview:
        QTimer.singleShot(150, quota.refresh)
    if args.capture:
        def capture():
            args.capture.parent.mkdir(parents=True, exist_ok=True)
            target = next((w for w in app.allWindows() if w.objectName() == "modelPreview"), window) if args.model_preview else window
            target.grabWindow().save(str(args.capture))
        QTimer.singleShot(900, capture)
    if args.quit_after > 0:
        QTimer.singleShot(round(args.quit_after * 1000), app.quit)
    result = app.exec()
    # Destroy QML while its context objects are still alive.
    from shiboken6 import delete
    delete(engine)
    return 1 if args.smoke_test and qml_warnings else result


if __name__ == "__main__":
    raise SystemExit(main())
