#!/usr/bin/env python3
"""One-shot KDE acceptance probe, unloaded on exit; not a runtime bridge.

Only windows belonging to --pid AND this application's app ID are examined.
--move changes only its exact pet window, to exercise KWin Remember rules.
"""
import argparse
import json
import os
from pathlib import Path
import tempfile

from PySide6.QtCore import ClassInfo, QCoreApplication, QObject, QTimer, Slot
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage

INTERFACE = "org.gptniang.Linux.Acceptance1"


@ClassInfo(**{"D-Bus Interface": INTERFACE})
class Receiver(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.result = None

    @Slot(str)
    def Report(self, payload):
        self.result = json.loads(payload)
        self.app.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--move", type=int, nargs=2, metavar=("X", "Y"))
    args = parser.parse_args()
    app = QCoreApplication([])
    bus = QDBusConnection.sessionBus()
    service = f"org.gptniang.Linux.Acceptance.Runner{os.getpid()}"
    receiver = Receiver(app)
    if not bus.registerService(service) or not bus.registerObject("/Probe", receiver, QDBusConnection.RegisterOption.ExportAllSlots):
        raise RuntimeError("无法注册一次性验收接口")
    scripting = QDBusInterface("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", bus)
    move = ""
    if args.move:
        move = f"if (w.caption === 'GPT-Niang Pet') {{var g=w.frameGeometry; w.frameGeometry={{x:{args.move[0]},y:{args.move[1]},width:g.width,height:g.height}};}}"
    source = f"""
var result = [];
workspace.windowList().forEach(function(w) {{
    if (w.pid !== {args.pid} || w.resourceClass !== 'org.gptniang.Linux') return;
    {move}
    var g = w.frameGeometry;
    result.push({{title:w.caption, appId:w.resourceClass, x:g.x, y:g.y,
                 width:g.width, height:g.height, keepAbove:w.keepAbove}});
}});
callDBus('{service}', '/Probe', '{INTERFACE}', 'Report', JSON.stringify(result));
"""
    name = f"gpt-niang-acceptance-{os.getpid()}"
    with tempfile.TemporaryDirectory(prefix="gpt-niang-probe-") as directory:
        script = Path(directory) / "probe.js"
        script.write_text(source)
        reply = scripting.call("loadScript", str(script), name)
        if reply.type() == QDBusMessage.MessageType.ErrorMessage:
            raise RuntimeError(reply.errorMessage())
        script_id = reply.arguments()[0]
        if script_id < 0:
            raise RuntimeError("KWin 无法加载一次性验收探针")
        try:
            runner = QDBusInterface("org.kde.KWin", f"/Scripting/Script{script_id}", "org.kde.kwin.Script", bus)
            result = runner.call("run")
            if result.type() == QDBusMessage.MessageType.ErrorMessage:
                raise RuntimeError(result.errorMessage())
            QTimer.singleShot(5000, app.quit)
            app.exec()
            if receiver.result is None:
                raise RuntimeError("一次性 KWin 探针未收到结果")
            print(json.dumps(receiver.result, ensure_ascii=False))
        finally:
            scripting.call("unloadScript", name)
            bus.unregisterService(service)


if __name__ == "__main__":
    main()
