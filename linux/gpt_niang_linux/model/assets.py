"""Pinned, data-only import. Third-party JavaScript is never installed or executed."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import time
import zipfile

from ..paths import xdg_path

SOURCE_URL = "https://github.com/zhengjihuaren/coopanion-gpt-dragon/releases/tag/v1.1.0"
SOURCE_SHA256 = "ec84d07a2144fb1850d5c85dddc558b5bd12cbf35560d0d8ee25ca1832ac7836"
MAX_ARCHIVE = 8 * 1024 * 1024


def model_directory():
    return xdg_path("XDG_DATA_HOME", ".local/share") / "gpt-niang/models/coopanion-dragon-1.1.0"


def import_model(archive, destination=None):
    archive = Path(archive)
    if archive.stat().st_size > MAX_ARCHIVE:
        raise ValueError("形象包过大")
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("形象包 SHA-256 不匹配，请使用固定的 v1.1.0 发布包")
    destination = Path(destination) if destination else model_directory()
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".dragon-", dir=destination.parent))
    try:
        with zipfile.ZipFile(archive) as source:
            model = json.loads(source.read("gpt-dragon/model.json"))
            validate_model(model)
            files = ["model.json", "figure.json", "README.md", "thumb.png"] + [p["src"] for p in model["parts"]]
            for name in files:
                info = source.getinfo("gpt-dragon/" + name)
                if info.file_size > 4 * 1024 * 1024:
                    raise ValueError("形象资源过大")
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read(info))
        (stage / "import.json").write_text(json.dumps({"schemaVersion": 1, "source": SOURCE_URL,
            "sha256": SOURCE_SHA256, "executableCodeImported": False}, indent=2) + "\n")
        # Reimport is idempotent. Never remove an unrelated directory.
        if destination.exists():
            marker = destination / "import.json"
            metadata = json.loads(marker.read_text()) if marker.is_file() else {}
            if not isinstance(metadata, dict) or metadata.get("sha256") != SOURCE_SHA256:
                raise ValueError("目标目录已有其他文件，拒绝覆盖")
            if all((destination/name).is_file() and (destination/name).read_bytes() == (stage/name).read_bytes() for name in files):
                return destination
            backup = destination.with_name(destination.name + f".backup-{time.time_ns()}")
            destination.rename(backup)
            try:
                os.replace(stage, destination)
            except OSError:
                if not destination.exists():
                    backup.rename(destination)
                raise
            return destination
        os.replace(stage, destination)
        return destination
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def validate_model(model):
    if (not isinstance(model, dict) or not isinstance(model.get("source"), dict)
            or model["source"].get("canvas") != [1024, 1024]
            or not isinstance(model.get("parts"), list) or len(model["parts"]) != 30):
        raise ValueError("不支持的模型画布或部件数量")
    ids = set()
    for part in model["parts"]:
        if not isinstance(part, dict):
            raise ValueError("无效的部件记录")
        name = part.get("id", "")
        if not isinstance(name, str) or not name or name in ids or not name.replace("-", "").isalnum() or part.get("src") != f"tex/{name}.png":
            raise ValueError("无效的部件路径或 ID")
        ids.add(name)
        box = part.get("box", [])
        if len(box) != 4 or any(type(v) not in (int, float) or not 0 <= v <= 2048 for v in box) or min(box[2:]) <= 0:
            raise ValueError("无效的部件坐标")
    if not isinstance(model.get("pivots"), dict):
        raise ValueError("缺失模型枢轴")
    for point in model["pivots"].values():
        if not isinstance(point, list) or len(point) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 2048 for v in point):
            raise ValueError("无效的模型枢轴")
    return model
