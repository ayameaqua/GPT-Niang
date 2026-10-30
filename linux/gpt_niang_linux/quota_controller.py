"""QProcess owner: bounded queries, crash recovery and UI-facing quota state."""
from datetime import datetime
import json
import logging
import os
import signal
import time

from PySide6.QtCore import QObject, Property, QProcess, QProcessEnvironment, QTimer, Signal, Slot

from .paths import LINUX_ROOT, resolve_executable
from .protocol import Decoder, ProtocolError

log = logging.getLogger(__name__)


def time_label(milliseconds):
    try:
        return datetime.fromtimestamp(milliseconds / 1000).astimezone().strftime("%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError, OverflowError):
        return "尚无"


class QuotaController(QObject):
    changed = Signal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.snapshot = None
        self.refreshing = False
        self.message = "点击角色读取 Codex 额度"
        self.failure_count = 0
        self.last_attempt = 0
        self.last_manual = -100.0
        self.counter = 0
        self.active_id = None
        self.closing = False
        self.decoder = Decoder()
        self.process = QProcess(self)
        # Give this worker and its children a private process group for bounded cleanup.
        params = QProcess.UnixProcessParameters()
        params.flags = QProcess.UnixProcessFlag.CreateNewSession
        self.process.setUnixProcessParameters(params)
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.readyReadStandardError.connect(self._drain_stderr)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self.process.started.connect(self._send_refresh)
        self.deadline = QTimer(self, singleShot=True, interval=35000)
        self.deadline.timeout.connect(self._timeout)
        self.poll = QTimer(self, singleShot=True)
        self.poll.timeout.connect(self.refresh)
        self.age_timer = QTimer(self, interval=15000)
        self.age_timer.timeout.connect(self.changed)
        self.age_timer.start()
        self.worker_pid = 0

    @Property(bool, notify=changed)
    def busy(self):
        return self.refreshing

    @Property(str, notify=changed)
    def status(self):
        if self.refreshing:
            return "正在读取额度…"
        return self.message

    @Property(str, notify=changed)
    def planLabel(self):
        return (self.snapshot or {}).get("planLabel", "未知套餐")

    @Property(str, notify=changed)
    def updatedLabel(self):
        snapshot = self.snapshot or {}
        return time_label(snapshot.get("observedAt")) if snapshot.get("ok") else "尚无成功数据"

    @Property(str, notify=changed)
    def attemptedLabel(self):
        return time_label(self.last_attempt) if self.last_attempt else "尚未尝试"

    @Property(bool, notify=changed)
    def stale(self):
        return any(window["freshness"] != "fresh" for window in self.windows) or bool(self.snapshot and not self.snapshot.get("queryOk"))

    @Property("QVariantList", notify=changed)
    def windows(self):
        snapshot = self.snapshot or {}
        result = []
        now = time.time()
        for raw in snapshot.get("windows", []):
            reset = raw.get("resetsAt")
            freshness = "fresh"
            if isinstance(reset, (float, int)) and reset > 0 and reset <= now:
                freshness = "expired"
            elif now * 1000 - snapshot.get("observedAt", 0) > 180000:
                freshness = "stale"
            result.append({**raw, "freshness": freshness,
                           "resetLabel": time_label(reset * 1000) if isinstance(reset, (float, int)) and reset > 0 else "未提供",
                           "remainingLabel": f"{raw['remaining']:.1f}%"})
        return result

    @Slot()
    def manualRefresh(self):
        now = time.monotonic()
        if now - self.last_manual < 2:
            return
        self.last_manual = now
        self.refresh()

    @Slot()
    def ensureFresh(self):
        observed = (self.snapshot or {}).get("observedAt", 0)
        if not self.refreshing and (not self.snapshot or not self.snapshot.get("queryOk") or time.time() * 1000 - observed > 60000 or self.stale):
            self.refresh()

    @Slot()
    def refresh(self):
        if self.closing or self.refreshing:
            return
        self.poll.stop()
        node = resolve_executable("node", self.settings.values["nodePath"])
        codex = resolve_executable("codex", self.settings.values["codexPath"])
        self.last_attempt = int(time.time() * 1000)
        if not node or not codex:
            # An unverified identity cannot authorize stale data reuse.
            self.snapshot = None
            self._failure("未找到 Node.js 或 Codex。请在设置中配置可执行文件路径。")
            return
        self.codex_path = codex
        if self.process.state() == QProcess.ProcessState.Running and self.process.program() != node:
            self._send({"type": "shutdown", "requestId": "reconfigure"})
            self.process.closeWriteChannel()
            if not self.process.waitForFinished(1500):
                self._kill_group()
                self.process.waitForFinished(1000)
        self.counter += 1
        self.active_id = str(self.counter)
        self.refreshing = True
        self.changed.emit()
        self.deadline.start()
        if self.process.state() == QProcess.ProcessState.NotRunning:
            self.decoder = Decoder()
            environment = QProcessEnvironment.systemEnvironment()
            # npm-installed Codex uses /usr/bin/env node, including from a desktop launcher.
            environment.insert("PATH", os.pathsep.join([os.path.dirname(node), os.path.dirname(codex), environment.value("PATH", "/usr/bin:/bin")]))
            self.process.setProcessEnvironment(environment)
            self.process.setProgram(node)
            self.process.setArguments([str(LINUX_ROOT / "runtime/usage-adapter.mjs")])
            self.process.start()
        elif self.process.state() == QProcess.ProcessState.Running:
            self._send_refresh()

    def _send(self, message):
        self.process.write((json.dumps({"schemaVersion": 1, **message}, ensure_ascii=False) + "\n").encode())

    def _send_refresh(self):
        self.worker_pid = self.process.processId()
        self._send({"type": "refresh", "requestId": self.active_id, "codexPath": self.codex_path})

    def _read(self):
        try:
            messages = self.decoder.feed(self.process.readAllStandardOutput())
            for message in messages:
                if message.get("requestId") != self.active_id or self.closing:
                    continue
                kind = message["type"]
                if kind == "snapshot":
                    data = message.get("data")
                    if data is None:
                        self.snapshot = None
                        self.changed.emit()
                        continue
                    if not self._valid_snapshot(data):
                        raise ProtocolError("invalid snapshot")
                    self.snapshot = data
                    log.info("Quota snapshot: queryOk=%s, windows=%d", data["queryOk"], len(data["windows"]))
                    self.deadline.stop()
                    self.refreshing = False
                    if data.get("queryOk"):
                        self.failure_count = 0
                        self.message = ("额度已更新（账户待确认）" if data.get("accountVerified") is False else "额度已更新") if data.get("ok") else "当前账户未返回可显示额度"
                        self.poll.start(60000)
                        self.changed.emit()
                    else:
                        self._failure(data.get("error", "额度读取失败"))
                elif kind == "error":
                    self.snapshot = None
                    self._failure(message.get("message", "查询进程出错"))
        except ProtocolError:
            self.snapshot = None
            self._failure("额度进程返回了无效数据，稍后将重新启动。")
            self._kill_group()

    @staticmethod
    def _valid_snapshot(data):
        if not isinstance(data, dict) or type(data.get("ok")) is not bool or type(data.get("queryOk")) is not bool:
            return False
        windows = data.get("windows")
        if not isinstance(windows, list) or len(windows) > 64:
            return False
        import math
        if type(data.get("observedAt", 0)) not in (int, float) or not math.isfinite(data.get("observedAt", 0)):
            return False
        for window in windows:
            if not isinstance(window, dict) or not isinstance(window.get("label"), str):
                return False
            value = window.get("remaining")
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
                return False
        return all(isinstance(data.get(key, ""), str) for key in ("planLabel", "error"))

    def _drain_stderr(self):
        # Discard raw upstream diagnostics: they may contain paths or account information.
        self.process.readAllStandardError()

    def _failure(self, message):
        self.deadline.stop()
        self.refreshing = False
        self.failure_count += 1
        self.message = message + ("（保留上次成功数据）" if self.snapshot and self.snapshot.get("ok") else "")
        self.poll.start([60000, 120000, 300000][min(self.failure_count - 1, 2)])
        log.info("Quota refresh unsuccessful (attempt %s)", self.failure_count)
        self.changed.emit()

    def _finished(self, *_):
        # A crashed Node process may leave app-server children in its process group.
        self._kill_group()
        self.worker_pid = 0
        if not self.closing and self.refreshing:
            self.snapshot = None
            self._failure("额度进程意外退出；可手动重试，将自动重新启动。")

    def _process_error(self, error):
        if not self.closing and error == QProcess.ProcessError.FailedToStart:
            self.snapshot = None
            self._failure("无法启动额度进程，请检查 Node.js 路径和执行权限。")

    def _kill_group(self):
        pid = self.worker_pid or self.process.processId()
        if pid:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def _timeout(self):
        self.snapshot = None
        self._failure("查询超时，已清理后台进程。可手动重试。")
        self._kill_group()

    def shutdown(self):
        self.closing = True
        self.poll.stop()
        self.deadline.stop()
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self._send({"type": "shutdown", "requestId": "exit"})
            self.process.closeWriteChannel()
            if not self.process.waitForFinished(1500):
                self._kill_group()
                self.process.waitForFinished(1000)
