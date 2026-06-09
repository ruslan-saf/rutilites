from __future__ import annotations

import os
import sys
from pathlib import Path

from config import APP_NAME

try:
    from win32com.client import Dispatch  # type: ignore
except ImportError:  # pragma: no cover
    Dispatch = None  # noqa: N816


def startup_dir() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def shortcut_path() -> Path:
    return startup_dir() / f"{APP_NAME}.lnk"


def _resolve_target() -> tuple[str, str, str]:
    """Return (target, args, workdir) suitable for the .lnk."""
    if getattr(sys, "frozen", False):
        # Built executable (PyInstaller / Nuitka)
        target = sys.executable
        args = ""
    else:
        # Source mode: run pythonw.exe main.py (no console window)
        py = sys.executable
        pyw = py.replace("python.exe", "pythonw.exe")
        if Path(pyw).exists():
            target = pyw
        else:
            target = py
        main_py = Path(__file__).resolve().parent.parent / "main.py"
        args = f'"{main_py}"'
    workdir = str(Path(target).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent)
    return target, args, workdir


def is_enabled() -> bool:
    return shortcut_path().exists()


def enable() -> bool:
    if Dispatch is None:
        return False
    startup_dir().mkdir(parents=True, exist_ok=True)
    target, args, workdir = _resolve_target()
    shell = Dispatch("WScript.Shell")
    sc = shell.CreateShortcut(str(shortcut_path()))
    sc.TargetPath = target
    sc.Arguments = args
    sc.WorkingDirectory = workdir
    sc.WindowStyle = 7  # minimized
    sc.Description = f"{APP_NAME} — tray utility"
    sc.Save()
    return True


def disable() -> None:
    p = shortcut_path()
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass


def set_enabled(on: bool) -> bool:
    if on:
        return enable()
    disable()
    return True
