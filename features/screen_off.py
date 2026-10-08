from __future__ import annotations

import ctypes
import logging
import threading
import time
from ctypes import wintypes
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

log = logging.getLogger("screen_off")
log.addHandler(logging.NullHandler())

HWND_BROADCAST = 0xFFFF
WM_SYSCOMMAND = 0x0112
SC_MONITORPOWER = 0xF170
MONITOR_ON = -1
MONITOR_OFF = 2

MOUSEEVENTF_MOVE = 0x0001

user32 = ctypes.WinDLL("user32", use_last_error=True)


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def _last_input_tick() -> int:
    info = _LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(_LASTINPUTINFO)
    user32.GetLastInputInfo(ctypes.byref(info))
    return info.dwTime


def _tick_after(a: int, b: int) -> bool:
    """True if tick a is later than tick b (32-bit wrap-safe)."""
    diff = (a - b) & 0xFFFFFFFF
    return 0 < diff < 0x80000000


def _post_monitor_power(state: int) -> None:
    user32.PostMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, state)


class ScreenOff(QObject):
    """Global hotkey that turns the display off without suspending the system
    and turns it back on with the same hotkey (or any other input).

    The hotkey press is reported via `triggered` (emitted from the listener
    thread, delivered to the GUI thread). The owner decides whether to turn
    the screen off or on according to `is_off`. Sleep/hibernation is not
    touched here (see KeepAwake for that).
    """

    triggered = Signal()
    failed = Signal(str)

    def __init__(self, hotkey: str) -> None:
        super().__init__()
        self._hotkey = hotkey
        self._mods: frozenset[int] = frozenset()
        self._main_vk: int = 0
        self._listener: Optional[keyboard.Listener] = None
        self._off = False
        self._baseline = 0
        self._baseline_set = False
        self._gen = 0

    @property
    def is_off(self) -> bool:
        return self._off

    # --- hotkey ----------------------------------------------------------

    def start(self) -> None:
        self.stop()
        try:
            self._mods, self._main_vk = parse_hotkey(self._hotkey)
            self._listener = keyboard.Listener(on_press=self._on_press)
            self._listener.start()
        except Exception as e:
            log.exception("screen-off hotkey registration failed")
            self.failed.emit(f"Не удалось зарегистрировать хоткей выключения экрана: {e}")

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
            self.triggered.emit()

    # --- display control -------------------------------------------------

    def turn_off(self, delay: float = 0.3) -> None:
        """Mark the screen as off and blank it once the hotkey is released
        (a key release while the screen is off would wake it at once)."""
        self._off = True
        self._baseline_set = False
        self._gen += 1
        threading.Thread(target=self._blank, args=(self._gen, delay), daemon=True).start()

    def _blank(self, gen: int, delay: float) -> None:
        deadline = time.time() + 2.0
        while time.time() < deadline:
            if not any(_get_async_key_state(vk) for vk in (*ALL_MODIFIER_VKS, self._main_vk)):
                break
            time.sleep(0.02)
        time.sleep(delay)
        if gen != self._gen or not self._off:
            return
        _post_monitor_power(MONITOR_OFF)
        time.sleep(0.2)
        self._baseline = _last_input_tick()
        self._baseline_set = True
        log.info("display off")

    def turn_on(self) -> None:
        self._off = False
        self._baseline_set = False
        self._gen += 1
        _post_monitor_power(MONITOR_ON)
        user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)  # input event wakes the display
        log.info("display on")

    def woken_by_input(self) -> bool:
        """True if user input arrived after the screen was blanked, i.e. the
        display was woken by something other than the hotkey handler."""
        if not (self._off and self._baseline_set):
            return False
        if _tick_after(_last_input_tick(), self._baseline):
            self._off = False
            self._baseline_set = False
            return True
        return False
