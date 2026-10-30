#!/usr/bin/env bash
set -euo pipefail
app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${GPT_NIANG_PYTHON:-python3}"
"$python_bin" "$app_dir/integrations/kde/rules.py" remove
"$python_bin" "$app_dir/packaging/desktop.py" remove
printf '入口与本项目 KDE 规则已移除。源码、venv、设置及配置备份保留。\n'
