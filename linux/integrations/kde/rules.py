#!/usr/bin/env python3
"""Manage one owned KWin rule, preserving unrelated groups byte for byte.

Run after closing the pet and the KDE rules editor. No KWin scripting is installed.
"""
import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

GROUP = "gpt-niang-linux-position-v1"
DESCRIPTION = "GPT-Niang Linux Pet — position memory"
RULE = {"Description": DESCRIPTION, "wmclass": "org.gptniang.Linux", "wmclassmatch": "1",
        "wmclasscomplete": "false", "title": "GPT-Niang Pet", "titlematch": "1",
        "types": "4294967295", "position": "40,40", "positionrule": "4"}


def sections(text):
    result = {}
    current = None
    for line in text.splitlines(keepends=True):
        match = re.fullmatch(r"\[([^\[\]]+)\]\s*", line.strip())
        if match:
            current = match[1]
            if current in result:
                raise ValueError("重复配置分组，请通过 KDE 规则编辑器管理。")
            result[current] = []
        elif current is not None:
            result[current].append(line)
    return result


def values(lines):
    return dict(line.strip().split("=", 1) for line in lines if "=" in line and not line.lstrip().startswith("#"))


def update(text, remove=False):
    groups = sections(text)
    owned = values(groups.get(GROUP, []))
    if owned and owned.get("Description") != DESCRIPTION:
        raise ValueError("项目规则分组已被其他配置占用，拒绝修改。")
    general = values(groups.get("General", []))
    if "rules" in general:
        ids = [part for part in general["rules"].split(",") if part]
        if any(not re.fullmatch(r"[\w-]+", part) for part in ids):
            raise ValueError("存在复杂的规则分组名称，请使用 KDE 导入功能。")
    else:
        count = int(general.get("count", "0"))
        if not 0 <= count <= 10000:
            raise ValueError("无效的 KWin 规则数量")
        ids = [str(index) for index in range(1, count + 1)]
    ids = list(dict.fromkeys(ids))
    if remove:
        ids = [item for item in ids if item != GROUP]
    elif GROUP not in ids:
        ids.insert(0, GROUP)
    if remove and GROUP not in groups and GROUP not in general.get("rules", ""):
        return text
    # Preserve KWin's remembered coordinates and any user changes on repeated install.
    rule_text = "" if remove else "[" + GROUP + "]\n" + "".join(f"{key}={value}\n" for key, value in (owned or RULE).items())
    general_lines = [line for line in groups.get("General", []) if not re.match(r"^(count|rules)=", line)]
    general_text = "[General]\n" + "".join(general_lines) + f"count={len(ids)}\nrules={','.join(ids)}\n"
    output = []
    skip = False
    for line in text.splitlines(keepends=True):
        match = re.fullmatch(r"\[([^\[\]]+)\]\s*", line.strip())
        if match:
            name = match[1]
            skip = name in ("General", GROUP)
            if name == "General":
                output.append(general_text)
            elif name == GROUP:
                output.append(rule_text)
        if not skip:
            output.append(line)
    result = "".join(output)
    if result and not result.endswith("\n"):
        result += "\n"
    if "General" not in groups:
        result += general_text
    if GROUP not in groups and not remove:
        result += rule_text
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "remove", "status"])
    parser.add_argument("--config", type=Path, default=Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "kwinrulesrc")
    args = parser.parse_args()
    text = args.config.read_text(encoding="utf-8") if args.config.exists() else ""
    if args.action == "status":
        present = GROUP in sections(text)
        print("已写入项目规则；是否命中和恢复成功仍须实际验证。" if present else "未安装项目规则。")
        return
    # Do not change a live pet's rule while KWin may be saving its remembered position.
    lock_path = Path(os.environ.get("XDG_RUNTIME_DIR", f"/tmp/gpt-niang-{os.getuid()}")) / "gpt-niang-linux.lock"
    import fcntl
    if lock_path.exists():
        with lock_path.open("a+") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                parser.error("请先退出桌宠，再修改规则。")
    try:
        result = update(text, remove=args.action == "remove")
    except ValueError as error:
        parser.error(str(error))
    if result == text:
        print("规则无需修改。")
        return
    args.config.parent.mkdir(parents=True, exist_ok=True)
    if args.config.exists():
        backup = args.config.with_name(args.config.name + ".gpt-niang-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".bak")
        shutil.copy2(args.config, backup)
        print(f"原配置备份：{backup}")
    descriptor, temporary = tempfile.mkstemp(dir=args.config.parent, prefix=".gpt-niang-rules-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(result)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, args.config)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    qdbus = shutil.which("qdbus6")
    if qdbus:
        subprocess.run([qdbus, "org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure"], check=False, capture_output=True, timeout=5)
    print("已安装专用规则。" if args.action == "install" else "已移除本项目规则。")


if __name__ == "__main__":
    main()
