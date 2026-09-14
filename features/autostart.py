from __future__ import annotations

import os
import sys
from pathlib import Path

from config import APP_NAME

# A plain .lnk in the Startup folder was found to be unreliable: on repeated
# real reboots Explorer would process sibling .vbs autostart entries (with a
# noticeable delay) but never actually invoke the .lnk at all, even though
# manually launching the exact same shortcut always worked. A .vbs stub that
# calls WScript.Shell.Run — the pattern already proven reliable for another
# tray app on this machine — reproducibly launches instead.
_OLD_SHORTCUT_NAME = f"{APP_NAME}.lnk"
_VBS_NAME = f"{APP_NAME}.vbs"


def startup_dir() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def entry_path() -> Path:
    return startup_dir() / _VBS_NAME


def _old_shortcut_path() -> Path:
    return startup_dir() / _OLD_SHORTCUT_NAME


def _resolve_target() -> tuple[str, str, str]:
    """Return (target, args, workdir) for launching the app."""
    if getattr(sys, "frozen", False):
        # Built executable (PyInstaller / Nuitka)
        target = sys.executable
        args = ""
        workdir = str(Path(target).parent)
    else:
        # Source mode: run pythonw.exe main.py (no console window)
        py = sys.executable
        pyw = py.replace("python.exe", "pythonw.exe")
        target = pyw if Path(pyw).exists() else py
        main_py = Path(__file__).resolve().parent.parent / "main.py"
        args = f'"{main_py}"'
        workdir = str(Path(__file__).resolve().parent.parent)
    return target, args, workdir


def _vbs_quote(s: str) -> str:
    """Escape a string for embedding inside a double-quoted VBScript literal."""
    return s.replace('"', '""')


def is_enabled() -> bool:
    return entry_path().exists()


def enable() -> bool:
    startup_dir().mkdir(parents=True, exist_ok=True)
    target, args, workdir = _resolve_target()
    command_line = f'"{target}"' + (f" {args}" if args else "")
    vbs = (
        f"' {APP_NAME} - system tray launcher (autostart entry)\n"
        "Option Explicit\n"
        "Dim sh\n"
        'Set sh = CreateObject("WScript.Shell")\n'
        f'sh.CurrentDirectory = "{_vbs_quote(workdir)}"\n'
        f'sh.Run "{_vbs_quote(command_line)}", 0, False\n'
    )
    entry_path().write_text(vbs, encoding="utf-8")
    # Clean up a stale .lnk from the previous (unreliable) autostart mechanism.
    _old_shortcut_path().unlink(missing_ok=True)
    return True


def disable() -> None:
    entry_path().unlink(missing_ok=True)
    _old_shortcut_path().unlink(missing_ok=True)


def set_enabled(on: bool) -> bool:
    if on:
        return enable()
    disable()
    return True
