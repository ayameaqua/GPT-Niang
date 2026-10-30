#!/usr/bin/env python3
"""Generate a user desktop entry referencing this source checkout, with Exec escaping."""
import argparse
import os
from pathlib import Path
import subprocess
import shutil

ROOT = Path(__file__).resolve().parents[1]
APP_ID = "org.gptniang.Linux"


def escape_value(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def quote_exec(value):
    # Desktop Entry value decoding precedes Exec quoting. '%' is a field-code escape.
    quoted = str(value).replace("%", "%%")
    for character in ("\\", '"', "`", "$"):
        quoted = quoted.replace(character, "\\" + character)
    return escape_value('"' + quoted + '"')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["install", "remove"])
    args = parser.parse_args()
    data_dir = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    destination = data_dir / "applications" / (APP_ID + ".desktop")
    if args.action == "remove":
        destination.unlink(missing_ok=True)
        print(f"已移除 {destination}")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        icon = ROOT.parent / "gpt-niang-usage/assets/gpt-dragon-niang-bust.png"
        entry = ("[Desktop Entry]\nType=Application\nVersion=1.0\nName=GPT-Niang Linux\n"
                 "Comment=Codex 额度龙娘挂件\nTerminal=false\nCategories=Utility;\n"
                 f"Exec={quote_exec(ROOT / 'run.sh')}\nIcon={escape_value(icon)}\n"
                 "StartupWMClass=org.gptniang.Linux\nActions=Settings;\n\n"
                 f"[Desktop Action Settings]\nName=设置\nExec={quote_exec(ROOT / 'run.sh')} --settings\n")
        destination.write_text(entry, encoding="utf-8")
        destination.chmod(0o644)
        print(f"已安装 {destination}")
    update = shutil.which("update-desktop-database")
    if update:
        subprocess.run([update, str(destination.parent)], check=False, capture_output=True)


if __name__ == "__main__":
    main()
