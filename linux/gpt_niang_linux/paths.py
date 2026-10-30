"""Paths shared by source launchers, diagnostics and the Qt frontend."""
import os
from pathlib import Path
import re
import shutil

LINUX_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LINUX_ROOT.parent
ASSETS = REPO_ROOT / "gpt-niang-usage" / "assets"
APP_ID = "org.gptniang.Linux"


def xdg_path(variable, fallback):
    value = os.environ.get(variable, "")
    return Path(value) if value and Path(value).is_absolute() else Path.home() / fallback


def executable(path):
    return bool(path and Path(path).is_absolute() and Path(path).is_file() and os.access(path, os.X_OK))


def resolve_executable(name, configured="", *, env=None, home=None):
    """Do not source shell startup files; recover from obsolete nvm paths."""
    env = os.environ if env is None else env
    home = Path.home() if home is None else Path(home)
    if executable(configured):
        return str(Path(configured).absolute())
    found = shutil.which(name, path=env.get("PATH", "/usr/local/bin:/usr/bin:/bin"))
    if found:
        return str(Path(found).absolute())
    directories = [home / ".local/bin", home / ".npm-global/bin", Path("/usr/local/bin"), Path("/usr/bin"), Path("/snap/bin")]
    nvm_root = Path(env.get("NVM_DIR", str(home / ".nvm"))) / "versions/node"
    def version_key(p):
        return tuple(int(n) for n in re.findall(r"\d+", p.name))
    if nvm_root.is_dir():
        directories += [p / "bin" for p in sorted(nvm_root.glob("v*"), key=version_key, reverse=True)]
    for directory in directories:
        candidate = directory / name
        if executable(candidate):
            return str(candidate.absolute())
    return ""
