"""Deterministic Qt tests; these do not certify compositor or real pointer behavior."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

from PySide6.QtCore import QPoint
from PySide6.QtGui import QGuiApplication, QImage, QColor
from PySide6.QtTest import QSignalSpy

from gpt_niang_linux.app import InstanceLock
from gpt_niang_linux.quota_controller import QuotaController
from gpt_niang_linux.settings import Settings
from gpt_niang_linux.window_backend import WindowBackend, alpha_region

app = QGuiApplication.instance() or QGuiApplication([])


class MaskTests(unittest.TestCase):
    def test_transparent_corners_and_internal_hole_are_excluded(self):
        image = QImage(9, 9, QImage.Format.Format_ARGB32)
        image.fill(QColor("transparent"))
        for y in range(2, 7):
            for x in range(2, 7):
                image.setPixelColor(x, y, QColor("white"))
        image.setPixelColor(4, 4, QColor("transparent"))
        region = alpha_region(image, 9, 9)
        self.assertTrue(region.contains(QPoint(2, 2)))
        self.assertFalse(region.contains(QPoint(0, 0)))
        self.assertFalse(region.contains(QPoint(4, 4)))

    def test_drag_suppresses_click_and_cancel_allows_next_click(self):
        class Window:
            moves = 0
            def startSystemMove(self):
                self.moves += 1
                return True
        backend = WindowBackend()
        backend.window = Window()
        spy = QSignalSpy(backend.petClicked)
        backend.pointerPress(1, 1)
        backend.pointerMove(2, 2)
        backend.pointerRelease()
        self.assertEqual(spy.count(), 1)
        backend.pointerPress(1, 1)
        backend.pointerMove(200, 100)
        backend.pointerRelease()
        self.assertEqual(spy.count(), 1)
        self.assertEqual(backend.window.moves, 1)
        backend.pointerPress(1, 1)
        backend.cancelPointer()
        backend.pointerRelease()
        self.assertEqual(spy.count(), 1)
        backend.pointerPress(1, 1)
        backend.pointerRelease()
        self.assertEqual(spy.count(), 2)


class QuotaTests(unittest.TestCase):
    def test_failed_check_does_not_advance_success_timestamp_or_refill_expired_quota(self):
        with tempfile.TemporaryDirectory() as directory:
            quota = QuotaController(Settings(Path(directory) / "settings.json"))
            observed = int(time.time() * 1000) - 600000
            quota.snapshot = {"ok": True, "queryOk": False, "observedAt": observed, "windows": [
                {"label": "个人额度", "minutes": None, "remaining": 0, "resetsAt": 1},
                {"label": "每周", "minutes": 10080, "remaining": 20, "resetsAt": None}]}
            quota._failure("offline")
            self.assertEqual(quota.snapshot["observedAt"], observed)
            self.assertEqual(quota.windows[0]["remaining"], 0)
            self.assertEqual(quota.windows[0]["freshness"], "expired")
            self.assertEqual(quota.windows[1]["freshness"], "stale")
            self.assertTrue(quota.stale)
            quota.shutdown()

    def test_invalid_snapshot_is_rejected(self):
        for data in ({}, {"ok": True, "queryOk": True, "windows": [None]},
                     {"ok": True, "queryOk": True, "windows": [{"label": "x", "remaining": float('nan')}]},
                     {"ok": True, "queryOk": True, "windows": [{"label": "x", "remaining": 101}]}):
            self.assertFalse(QuotaController._valid_snapshot(data))

    def test_kernel_lock_releases_without_deleting_file(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"XDG_RUNTIME_DIR": directory}):
            first, second = InstanceLock(), InstanceLock()
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            first.stream.close()
            self.assertTrue(second.acquire())
            second.stream.close()


@unittest.skipUnless(shutil.which("node"), "Node.js is required for isolated QProcess integration tests")
class ProcessTests(unittest.TestCase):
    @staticmethod
    def wait_for(predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            app.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        raise AssertionError("Qt process condition timed out")

    def fixture(self, root, hang=False):
        cli = root / "fake codex"
        pidfile = root / "cli-pid"
        code = ("#!/usr/bin/env node\n"
                "const fs=require('node:fs'); const readline=require('node:readline');\n"
                f"fs.writeFileSync({json.dumps(str(pidfile))},String(process.pid));\n")
        if hang:
            code += "process.on('SIGTERM',()=>{}); setInterval(()=>{},100);\n"
        else:
            code += """
readline.createInterface({input:process.stdin}).on('line', line=>{
  const m=JSON.parse(line); let result;
  if(m.method==='initialize')result={};
  else if(m.method==='account/read')result={account:{type:'chatgpt',email:'fixture@example.invalid',planType:'plus'}};
  else if(m.method==='account/rateLimits/read')result={rateLimits:{primary:{usedPercent:60,windowDurationMins:10080,resetsAt:null}}};
  else return;
  process.stdout.write(JSON.stringify({id:m.id,result})+'\\n');
});
"""
        cli.write_text(code)
        cli.chmod(0o755)
        settings = Settings(root / "settings.json")
        settings.save(nodePath=shutil.which("node"), codexPath=str(cli))
        return QuotaController(settings), pidfile

    def assert_dead(self, pid):
        def dead():
            try:
                os.kill(pid, 0)
                return False
            except ProcessLookupError:
                return True
        self.wait_for(dead)

    def test_qprocess_queries_fixture_and_shuts_down_cleanly(self):
        with tempfile.TemporaryDirectory(prefix="pet process ") as directory:
            quota, pidfile = self.fixture(Path(directory))
            try:
                quota.refresh()
                self.wait_for(lambda: quota.snapshot is not None)
                self.assertTrue(quota.snapshot["ok"])
                self.assertEqual(len(quota.windows), 1)
                self.assertEqual(quota.windows[0]["remaining"], 40)
                self.assertEqual(quota.planLabel, "Plus")
                self.assertNotIn("fixture@example.invalid", json.dumps(quota.snapshot))
                cli_pid = int(pidfile.read_text())
            finally:
                quota.shutdown()
            self.assert_dead(cli_pid)

    def test_worker_crash_cleans_group_and_next_refresh_restarts(self):
        with tempfile.TemporaryDirectory(prefix="pet crash ") as directory:
            quota, pidfile = self.fixture(Path(directory), hang=True)
            try:
                quota.refresh()
                self.wait_for(pidfile.exists)
                cli_pid = int(pidfile.read_text())
                old_worker = quota.worker_pid
                os.kill(old_worker, signal.SIGKILL)
                self.wait_for(lambda: not quota.busy)
                self.assert_dead(cli_pid)
                pidfile.unlink()
                quota.refresh()
                self.wait_for(pidfile.exists)
                self.assertNotEqual(quota.worker_pid, old_worker)
                restarted_cli = int(pidfile.read_text())
            finally:
                quota.shutdown()
            self.assert_dead(restarted_cli)

    def test_idle_worker_crash_invalidates_snapshot_identity(self):
        with tempfile.TemporaryDirectory(prefix="pet idle crash ") as directory:
            quota, _ = self.fixture(Path(directory))
            try:
                quota.refresh()
                self.wait_for(lambda: quota.snapshot is not None)
                self.assertFalse(quota.busy)
                os.kill(quota.worker_pid, signal.SIGKILL)
                self.wait_for(lambda: quota.snapshot is None)
                self.assertIn("意外退出", quota.status)
            finally:
                quota.shutdown()

    def test_outer_timeout_cleans_uncooperative_child(self):
        with tempfile.TemporaryDirectory(prefix="pet timeout ") as directory:
            quota, pidfile = self.fixture(Path(directory), hang=True)
            try:
                quota.deadline.setInterval(300)
                quota.refresh()
                self.wait_for(pidfile.exists)
                cli_pid = int(pidfile.read_text())
                self.wait_for(lambda: not quota.busy)
                self.assertIn("查询超时", quota.status)
                self.assert_dead(cli_pid)
            finally:
                quota.shutdown()

    @unittest.skipUnless(Path("/proc/self").exists(), "Linux /proc is required")
    def test_killed_gui_causes_worker_eof_cleanup_and_lock_recovery(self):
        with tempfile.TemporaryDirectory(prefix="pet killed gui ") as directory:
            root = Path(directory)
            quota, pidfile = self.fixture(root, hang=True)
            quota.shutdown()
            config = root / "config/gpt-niang"
            config.mkdir(parents=True)
            shutil.copyfile(root / "settings.json", config / "settings.json")
            runtime = root / "runtime"
            runtime.mkdir(mode=0o700)
            environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software",
                           "XDG_CONFIG_HOME": str(root / "config"), "XDG_STATE_HOME": str(root / "state"),
                           "XDG_RUNTIME_DIR": str(runtime)}
            launcher = Path(__file__).resolve().parents[1] / "run.sh"
            process = subprocess.Popen([str(launcher), "--quit-after", "20"], env=environment,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.wait_for(pidfile.exists)
                cli_pid = int(pidfile.read_text())
                children = Path(f"/proc/{process.pid}/task/{process.pid}/children").read_text().split()
                self.assertEqual(len(children), 1)
                worker_pid = int(children[0])
                process.kill()
                process.communicate(timeout=3)
                self.assert_dead(cli_pid)
                self.assert_dead(worker_pid)
                restarted = subprocess.run([str(launcher), "--smoke-test"], env=environment, capture_output=True, text=True, timeout=5)
                self.assertEqual(restarted.returncode, 0, restarted.stderr)
                self.assertNotIn("已在此会话运行", restarted.stdout)
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate(timeout=3)


if __name__ == "__main__":
    unittest.main()
