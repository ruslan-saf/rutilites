from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_NAME = "RuTilites"

DEFAULTS: dict[str, Any] = {
    "hotkey_layout_fix": "<ctrl>+<shift>+z",
    "keep_awake_on_start": False,
    "autostart": False,
    "theme": "dark",
}


def config_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    return config_dir() / "config.json"


class Config:
    def __init__(self) -> None:
        self._data: dict[str, Any] = dict(DEFAULTS)
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
