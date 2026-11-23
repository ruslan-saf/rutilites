from __future__ import annotations

import subprocess
import sys
from functools import lru_cache
from pathlib import Path

# Bump by hand when releasing: MAJOR.MINOR.PATCH
# (MINOR for a new feature, PATCH for a fix).
APP_VERSION = "1.2.0"

_REPO = Path(__file__).resolve().parent
_CREATE_NO_WINDOW = 0x08000000  # no console flash when running under pythonw


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(_REPO), *args], capture_output=True, text=True,
                             timeout=2, creationflags=_CREATE_NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


@lru_cache(maxsize=1)
def build_info() -> str:
    """Commit hash and date of the running code, e.g. '9be63c7 от 08.10.2026',
    plus a note when the files differ from that commit. Empty for a built .exe
    or when git is unavailable."""
    if getattr(sys, "frozen", False):
        return ""
    line = _git("log", "-1", "--format=%h %cd", "--date=format:%d.%m.%Y")
    if not line:
        return ""
    commit, date = line.split(" ", 1)
    info = f"{commit} от {date}"
    if _git("status", "--porcelain", "--untracked-files=no"):
        info += ", есть незакоммиченные изменения"
    return info


def version_text() -> str:
    info = build_info()
    return f"Версия {APP_VERSION}" + (f" ({info})" if info else "")
