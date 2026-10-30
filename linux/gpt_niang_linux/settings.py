"""Atomic preferences; quota snapshots and credentials never go here."""
import json
import math
import os
from pathlib import Path
import tempfile
import time

from .paths import xdg_path

DEFAULTS = {"schemaVersion": 1, "scale": 1.0, "nodePath": "", "codexPath": "", "quotesEnabled": True}


def normalize(raw):
    if not isinstance(raw, dict):
        raise ValueError("preferences must be an object")
    version = raw.get("schemaVersion", 1)
    if type(version) is not int or version != 1:
        raise ValueError("unsupported preferences schema")
    result = dict(DEFAULTS)
    scale = raw.get("scale", 1.0)
    if type(scale) in (int, float) and math.isfinite(scale):
        result["scale"] = round(max(0.6, min(2.5, scale)), 2)
    for key in ("nodePath", "codexPath"):
        value = raw.get(key, "")
        if isinstance(value, str) and len(value) <= 4096 and "\0" not in value:
            result[key] = value
    if type(raw.get("quotesEnabled")) is bool:
        result["quotesEnabled"] = raw["quotesEnabled"]
    return result


class Settings:
    def __init__(self, path=None):
        self.path = Path(path) if path else xdg_path("XDG_CONFIG_HOME", ".config") / "gpt-niang/settings.json"
        self.values = dict(DEFAULTS)
        self.warning = ""
        if self.path.exists():
            try:
                if self.path.stat().st_size > 65536:
                    raise ValueError("preferences too large")
                self.values = normalize(json.loads(self.path.read_text(encoding="utf-8")))
            except (ValueError, OSError, UnicodeError):
                backup = self.path.with_name(f"settings.corrupt-{time.time_ns()}.json")
                try:
                    self.path.rename(backup)
                    self.warning = f"设置损坏，已使用默认值；原文件保留于 {backup}"
                except OSError:
                    self.warning = "设置无法读取；已使用默认值，原文件保留。"

    def save(self, **changes):
        values = normalize({**self.values, **changes})
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary = tempfile.mkstemp(prefix=".settings-", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(values, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            self.values = values
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
