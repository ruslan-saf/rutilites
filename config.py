from __future__ import annotations

import json
import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

APP_NAME = "RuTilites"

# Defaults are the author's own settings, so a fresh copy behaves the same
# on every machine without copying config.json around.
DEFAULTS: dict[str, Any] = {
    "hotkey_layout_fix": "<ctrl>+<shift>+x",
    "hotkey_screen_off": "<ctrl>+<alt>+<f12>",
    "hotkey_sleep": "<ctrl>+<alt>+q",
    "keep_awake_on_start": False,
    # Mode used by a single tray click and by keep_awake_on_start:
    # "system" (display turns off as usual) or "display" (display stays on).
    "keep_awake_mode": "system",
    "autostart": True,
    "theme": "dark",
}

CONFIG_NAME = "config.json"


def app_dir() -> Path:
    """Folder the program runs from (next to main.py, or the built .exe)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def legacy_config_dir() -> Path:
    """Where settings lived before portable mode: %APPDATA%\\RuTilites."""
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / APP_NAME


@lru_cache(maxsize=1)
def _app_dir_writable() -> bool:
    probe = app_dir() / ".write_test"
    try:
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def config_dir() -> Path:
    """Portable mode: settings are kept next to the program, so copying the
    folder carries them along. Falls back to %APPDATA%\\RuTilites only when
    the program folder is read-only (e.g. under Program Files)."""
    if _app_dir_writable():
        return app_dir()
    p = legacy_config_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    return config_dir() / CONFIG_NAME


def _migrate_legacy_config() -> None:
    """One-time copy of %APPDATA%\\RuTilites\\config.json into the program
    folder. The old file is left in place."""
    target = config_path()
    legacy = legacy_config_dir() / CONFIG_NAME
    if target.exists() or not legacy.exists() or target == legacy:
        return
    try:
        shutil.copy2(legacy, target)
    except OSError:
        pass


class Config:
    def __init__(self) -> None:
        self._data: dict[str, Any] = dict(DEFAULTS)
        _migrate_legacy_config()
        self.load()

    def load(self) -> None:
        path = config_path()
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    self._data.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        with config_path().open("w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()
