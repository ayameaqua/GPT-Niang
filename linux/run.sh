#!/usr/bin/env bash
set -euo pipefail
app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python_bin="${GPT_NIANG_PYTHON:-$app_dir/.venv/bin/python}"
if [[ ! -x "$python_bin" ]]; then
    printf '请先运行：%q/setup.sh\n' "$app_dir" >&2
    exit 1
fi
# Use only this venv's Qt libraries and plugins, including from a KDE launcher.
unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH QML2_IMPORT_PATH QML_IMPORT_PATH LD_LIBRARY_PATH
export QT_QUICK_CONTROLS_STYLE=Fusion
if [[ -z "${QT_QPA_PLATFORM:-}" ]]; then
    if [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
        export QT_QPA_PLATFORM=wayland
    elif [[ " $* " != *" --diagnose "* ]]; then
        printf '未检测到 Wayland。诊断可用 --diagnose；离屏测试可显式设置 QT_QPA_PLATFORM=offscreen。\n' >&2
        exit 1
    fi
fi
export PYTHONPATH="$app_dir${PYTHONPATH:+:$PYTHONPATH}"
exec "$python_bin" -m gpt_niang_linux "$@"
