"""Update RuTilites from its git remote: check, then fast-forward and restart.

Works only for a git clone. Nothing here touches config.json (git-ignored),
so user settings survive an update.
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from config import app_dir
from version import APP_VERSION, REPO_URL

_CREATE_NO_WINDOW = 0x08000000  # no console flash under pythonw


class UpdateError(Exception):
    """A step failed; the message is shown to the user as is."""


def _git(*args: str, timeout: float = 30) -> str:
    try:
        out = subprocess.run(["git", "-C", str(app_dir()), *args], capture_output=True,
                             text=True, encoding="utf-8", errors="replace",
                             timeout=timeout, creationflags=_CREATE_NO_WINDOW)
    except FileNotFoundError:
        raise UpdateError("Git не найден. Установите Git for Windows или обновите программу вручную.")
    except subprocess.TimeoutExpired:
        raise UpdateError(f"git {args[0]} не ответил за {timeout:.0f} с. Проверьте подключение к интернету.")
    if out.returncode != 0:
        msg = (out.stderr or out.stdout).strip().splitlines()
        raise UpdateError(f"git {args[0]}: {msg[-1] if msg else f'код {out.returncode}'}")
    return out.stdout.strip()


def is_git_checkout() -> bool:
    return (app_dir() / ".git").exists()


@dataclass
class UpdateInfo:
    current_version: str
    remote_version: str
    behind: int                       # commits on the remote we do not have
    ahead: int                        # local commits the remote does not have
    commits: list[str] = field(default_factory=list)  # "hash subject", newest first
    changed_files: list[str] = field(default_factory=list)
    local_changes: list[str] = field(default_factory=list)  # modified tracked files

    @property
    def available(self) -> bool:
        return self.behind > 0

    @property
    def needs_requirements(self) -> bool:
        return "requirements.txt" in self.changed_files


def check() -> UpdateInfo:
    """Fetch from the remote and compare. Raises UpdateError with a message
    meant for the user."""
    if not is_git_checkout():
        raise UpdateError("Программа установлена без git (например, из ZIP), поэтому обновить её "
                          f"автоматически нельзя. Новая версия: {REPO_URL}")
    try:
        upstream = _git("rev-parse", "--abbrev-ref", "@{u}")
    except UpdateError:
        raise UpdateError("У текущей ветки нет связанной ветки на сервере, сравнивать не с чем.")
    _git("fetch", "--quiet", "origin")
    behind = int(_git("rev-list", "--count", "HEAD..@{u}"))
    ahead = int(_git("rev-list", "--count", "@{u}..HEAD"))
    commits = _git("log", "--format=%h %s", "HEAD..@{u}").splitlines() if behind else []
    changed = _git("diff", "--name-only", "HEAD", "@{u}").splitlines() if behind else []
    remote_version = APP_VERSION
    if behind:
        try:
            m = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', _git("show", f"{upstream}:version.py"), re.M)
            if m:
                remote_version = m.group(1)
        except UpdateError:
            pass
    local = _git("diff", "--name-only", "HEAD").splitlines()  # staged or not, tracked files only
    return UpdateInfo(APP_VERSION, remote_version, behind, ahead, commits, changed, local)


def _python_console_exe() -> str:
    """python.exe next to the running pythonw.exe, for pip."""
    exe = Path(sys.executable)
    candidate = exe.with_name("python.exe")
    return str(candidate if candidate.exists() else exe)


def apply(info: UpdateInfo, progress=lambda text: None) -> None:  # type: ignore[no-untyped-def]
    """Fast-forward to the remote and install new requirements if needed.
    The caller restarts the app afterwards."""
    if info.local_changes:
        raise UpdateError("В файлах программы есть локальные изменения, обновление остановлено, "
                          "чтобы их не потерять:\n" + "\n".join(info.local_changes))
    if info.ahead:
        raise UpdateError(f"В этой копии есть {info.ahead} коммит(ов), которых нет на сервере. "
                          "Обновите вручную (git pull).")
    progress("Скачиваю изменения…")
    _git("merge", "--ff-only", "@{u}", timeout=60)
    if info.needs_requirements:
        progress("Устанавливаю библиотеки из requirements.txt…")
        try:
            out = subprocess.run([_python_console_exe(), "-m", "pip", "install", "--disable-pip-version-check",
                                  "-q", "-r", str(app_dir() / "requirements.txt")],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace",
                                 timeout=600, creationflags=_CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired:
            raise UpdateError("pip не уложился в 10 минут. Запустите install.cmd вручную.")
        if out.returncode != 0:
            tail = (out.stderr or out.stdout).strip().splitlines()[-3:]
            raise UpdateError("Код обновлён, но библиотеки не установились. Запустите install.cmd.\n"
                              + "\n".join(tail))
