#!/usr/bin/env bash
set -euo pipefail
app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -x "$app_dir/.venv/bin/python" ]]; then
    printf '请先运行 linux/setup.sh。\n' >&2
    exit 1
fi
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != --with-kwin-rules ) ]]; then
    printf '用法：install.sh [--with-kwin-rules]\n' >&2
    exit 2
fi
if [[ "${1:-}" == --with-kwin-rules ]]; then
    "$app_dir/.venv/bin/python" "$app_dir/integrations/kde/rules.py" install
fi
"$app_dir/.venv/bin/python" "$app_dir/packaging/desktop.py" install
