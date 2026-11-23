from __future__ import annotations

import ctypes
import logging
import threading
import time
from typing import Optional

from PySide6.QtCore import QObject, Signal
from pynput import keyboard

from features.layout_fix import (
    ALL_MODIFIER_VKS,
    _get_async_key_state,
    _modifier_held,
    _vk_of,
    parse_hotkey,
)

log = logging.getLogger("sleep_hotkey")
log.addHandler(logging.NullHandler())

powrprof = ctypes.WinDLL("powrprof", use_last_error=True)


class SleepHotkey(QObject):
    """Global hotkey that puts the computer to sleep (S3), the same action the
    Logi Options+ "Sleep" macro performed.

    The suspend call runs on a worker thread and blocks there until the
    machine resumes; while it is pending, further presses are ignored so key
    auto-repeat or a press right after wake-up cannot send it back to sleep.
    """

    failed = Signal(str)

    # Ignore presses for this long after resuming (stuck keys, auto-repeat).
    RESUME_GRACE_S = 3.0

    def __init__(self, hotkey: str) -> None:
        super().__init__()
        self._hotkey = hotkey
        self._mods: frozenset[int] = frozenset()
        self._main_vk: int = 0
        self._listener: Optional[keyboard.Listener] = None
        self._busy = threading.Lock()

    # --- hotkey ----------------------------------------------------------

    def start(self) -> None:
        self.stop()
        try:
            self._mods, self._main_vk = parse_hotkey(self._hotkey)
            self._listener = keyboard.Listener(on_press=self._on_press)
            self._listener.start()
        except Exception as e:
            log.exception("sleep hotkey registration failed")
            self.failed.emit(f"Не удалось зарегистрировать хоткей спящего режима: {e}")

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def set_hotkey(self, hotkey: str) -> None:
        self._hotkey = hotkey
        self.start()

    def _on_press(self, key) -> None:  # type: ignore[no-untyped-def]
        if _vk_of(key) != self._main_vk:
            return
        if all(_modifier_held(m) for m in self._mods):
            self.sleep_now(delay=0.3)

    # --- action ----------------------------------------------------------

    def sleep_now(self, delay: float = 0.3) -> None:
        """Suspend once the hotkey keys are released. Safe to call from any
        thread (hotkey listener or the tray menu)."""
        if not self._busy.acquire(blocking=False):
            return
        threading.Thread(target=self._suspend, args=(delay,), daemon=True).start()

    def _suspend(self, delay: float) -> None:
        try:
            # A key release arriving during suspend can count as a wake event.
            deadline = time.time() + 2.0
            while time.time() < deadline:
                if not any(_get_async_key_state(vk) for vk in (*ALL_MODIFIER_VKS, self._main_vk)):
                    break
                time.sleep(0.02)
            time.sleep(delay)
            log.info("suspending")
            # SetSuspendState(hibernate=False, force=False, wakeup_events_disabled=False)
            ok = powrprof.SetSuspendState(False, False, False)
            if not ok:
                err = ctypes.get_last_error()
                self.failed.emit(f"Не удалось перевести компьютер в сон (код {err})")
            time.sleep(self.RESUME_GRACE_S)  # returns only after resume
        finally:
            self._busy.release()
