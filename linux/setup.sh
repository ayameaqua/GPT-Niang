#!/usr/bin/env bash
set -euo pipefail
app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
"${PYTHON:-python3}" -m venv "$app_dir/.venv"
"$app_dir/.venv/bin/python" -m pip install -r "$app_dir/requirements.lock"
"$app_dir/run.sh" --diagnose
printf '\n依赖安装完成。启动：%q/run.sh\n' "$app_dir"
