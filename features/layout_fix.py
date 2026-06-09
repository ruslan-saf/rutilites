from __future__ import annotations

import ctypes
import logging
import threading
import time
from typing import Optional

import pyperclip
from PySide6.QtCore import QObject, Signal
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

log = logging.getLogger("layout_fix")
log.addHandler(logging.NullHandler())

EN_CHARS = "`qwertyuiop[]asdfghjkl;'zxcvbnm,./~QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?"
RU_CHARS = "ёйцукенгшщзхъфывапролджэячсмитьбю.ЁЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,"

EN_TO_RU = str.maketrans(EN_CHARS, RU_CHARS)
RU_TO_EN = str.maketrans(RU_CHARS, EN_CHARS)

# Virtual-key codes (subset)
VK_C = 0x43
VK_V = 0x56
VK_CONTROL = 0x11
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_SHIFT = 0x10
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_MENU = 0x12  # Alt
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_LWIN = 0x5B
VK_RWIN = 0x5C

ALL_MODIFIER_VKS = (
    VK_CONTROL, VK_LCONTROL, VK_RCONTROL,
    VK_SHIFT, VK_LSHIFT, VK_RSHIFT,
    VK_MENU, VK_LMENU, VK_RMENU,
    VK_LWIN, VK_RWIN,
)

# Token → generic modifier VK (either left/right counts as held)
MODIFIER_TOKENS: dict[str, int] = {
    "ctrl": VK_CONTROL,
    "shift": VK_SHIFT,
    "alt": VK_MENU,
    "cmd": VK_LWIN,  # GetAsyncKeyState on either LWIN/RWIN
    "win": VK_LWIN,
}

# Named non-modifier keys → VK
NAMED_VKS: dict[str, int] = {
    "space": 0x20, "enter": 0x0D, "return": 0x0D, "tab": 0x09,
    "esc": 0x1B, "escape": 0x1B, "pause": 0x13, "break": 0x13,
    "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pagedown": 0x22, "backspace": 0x08,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
}
for _i in range(1, 13):
    NAMED_VKS[f"f{_i}"] = 0x6F + _i  # F1=0x70 … F12=0x7B

KEYEVENTF_KEYUP = 0x0002
user32 = ctypes.WinDLL("user32", use_last_error=True)


def _get_async_key_state(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def _modifier_held(generic_vk: int) -> bool:
    """Return True if the given generic modifier (VK_CONTROL/SHIFT/MENU/LWIN)
    is held on either side of the keyboard."""
    if generic_vk == VK_CONTROL:
        return _get_async_key_state(VK_CONTROL) or _get_async_key_state(VK_LCONTROL) or _get_async_key_state(VK_RCONTROL)
    if generic_vk == VK_SHIFT:
        return _get_async_key_state(VK_SHIFT) or _get_async_key_state(VK_LSHIFT) or _get_async_key_state(VK_RSHIFT)
    if generic_vk == VK_MENU:
        return _get_async_key_state(VK_MENU) or _get_async_key_state(VK_LMENU) or _get_async_key_state(VK_RMENU)
    if generic_vk == VK_LWIN:
        return _get_async_key_state(VK_LWIN) or _get_async_key_state(VK_RWIN)
    return _get_async_key_state(generic_vk)


def _wait_modifiers_released(timeout: float = 0.6) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not any(_get_async_key_state(vk) for vk in ALL_MODIFIER_VKS):
            return
        time.sleep(0.015)


def _force_release_modifiers() -> None:
    released = []
    for vk in ALL_MODIFIER_VKS:
        if _get_async_key_state(vk):
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            released.append(hex(vk))
    if released:
        log.debug("force_release: %s", released)


def _kbd(vk: int, key_up: bool) -> None:
    flags = KEYEVENTF_KEYUP if key_up else 0
    user32.keybd_event(vk, 0, flags, 0)


def _send_ctrl_combo(vk: int) -> None:
    _kbd(VK_CONTROL, False)
    time.sleep(0.015)
    _kbd(vk, False)
    time.sleep(0.015)
    _kbd(vk, True)
    time.sleep(0.015)
    _kbd(VK_CONTROL, True)


def detect_and_convert(text: str) -> Optional[str]:
    if not text:
        return None
    ru_count = sum(1 for c in text if c in RU_CHARS)
    en_count = sum(1 for c in text if c in EN_CHARS)
    if ru_count == 0 and en_count == 0:
        return None
    if ru_count >= en_count:
        return text.translate(RU_TO_EN)
    return text.translate(EN_TO_RU)


def parse_hotkey(spec: str) -> tuple[frozenset[int], int]:
    """Parse pynput-style hotkey spec like '<ctrl>+<shift>+x' into
    (set of required modifier-VKs, main-key VK)."""
    parts = [p.strip() for p in spec.split("+") if p.strip()]
    mods: set[int] = set()
    main_vk: Optional[int] = None
    for raw in parts:
        token = raw.strip("<>").lower()
        if token in MODIFIER_TOKENS:
            mods.add(MODIFIER_TOKENS[token])
        elif token in NAMED_VKS:
            if main_vk is not None:
                raise ValueError(f"More than one main key in hotkey: {spec!r}")
            main_vk = NAMED_VKS[token]
        elif len(token) == 1:
            ch = token.upper()
            if main_vk is not None:
                raise ValueError(f"More than one main key in hotkey: {spec!r}")
            main_vk = ord(ch)  # Windows VK for A..Z, 0..9 == ASCII
        else:
            raise ValueError(f"Unknown hotkey token: {raw!r}")
    if main_vk is None:
        raise ValueError(f"Hotkey {spec!r} has no main key")
    return frozenset(mods), main_vk


def _vk_of(key) -> Optional[int]:  # type: ignore[no-untyped-def]
    if isinstance(key, Key):
        try:
            return key.value.vk
        except AttributeError:
            return None
    if isinstance(key, KeyCode):
        return key.vk
    return None


class LayoutFix(QObject):
    """Listens for a global hotkey and swaps the keyboard layout of the
    currently selected text (RU <-> EN). Layout-independent: matches by
    virtual-key code, so Russian/English input mode doesn't matter."""

    converted = Signal(str)
    failed = Signal(str)

    def __init__(self, hotkey: str) -> None:
        super().__init__()
        self._hotkey = hotkey
        self._mods: frozenset[int] = frozenset()
        self._main_vk: int = 0
        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        self.stop()
        try:
            self._mods, self._main_vk = parse_hotkey(self._hotkey)
            log.info(
                "registering hotkey=%r mods=%s main_vk=0x%02X",
                self._hotkey, [hex(m) for m in self._mods], self._main_vk,
            )
            self._listener = keyboard.Listener(on_press=self._on_press)
            self._listener.start()
            log.info("listener thread alive=%s", self._listener.is_alive())
        except Exception as e:
            log.exception("hotkey registration failed")
            self.failed.emit(f"Не удалось зарегистрировать хоткей: {e}")

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

    # --- listener --------------------------------------------------------

    def _on_press(self, key) -> None:  # type: ignore[no-untyped-def]
        vk = _vk_of(key)
        if vk is None:
            return
        if vk != self._main_vk:
            return
        # Check that all required modifiers are currently held.
        for m in self._mods:
            if not _modifier_held(m):
                return
        log.debug("hotkey matched (vk=0x%02X with mods=%s)",
                  vk, [hex(m) for m in self._mods])
        threading.Thread(target=self._perform, daemon=True).start()

    def _perform(self) -> None:
        if not self._lock.acquire(blocking=False):
            return
        try:
            self._do_swap()
        except Exception as e:
            log.exception("swap failed")
            self.failed.emit(str(e))
        finally:
            self._lock.release()

    def _do_swap(self) -> None:
        log.debug("=== hotkey fired ===")
        held_before = [hex(vk) for vk in ALL_MODIFIER_VKS if _get_async_key_state(vk)]
        log.debug("modifiers at start: %s", held_before)

        _wait_modifiers_released(timeout=0.6)
        _force_release_modifiers()
        time.sleep(0.05)

        try:
            saved = pyperclip.paste()
        except Exception as e:
            log.warning("clipboard read (save) failed: %s", e)
            saved = ""

        sentinel = "\x00__rutilites_clipboard_probe__\x00"
        try:
            pyperclip.copy(sentinel)
        except Exception as e:
            log.warning("clipboard write (sentinel) failed: %s", e)

        time.sleep(0.05)
        log.debug("sending Ctrl+C")
        _send_ctrl_combo(VK_C)

        text = sentinel
        deadline = time.time() + 0.7
        while time.time() < deadline:
            time.sleep(0.04)
            try:
                current = pyperclip.paste()
            except Exception:
                current = sentinel
            if current != sentinel:
                text = current
                break

        if text == sentinel or not text:
            try:
                pyperclip.copy(saved)
            except Exception:
                pass
            log.info("no selected text")
            self.failed.emit("Нет выделенного текста")
            return

        log.debug("captured text length=%d, preview=%r", len(text), text[:50])

        converted = detect_and_convert(text)
        if converted is None or converted == text:
            try:
                pyperclip.copy(saved)
            except Exception:
                pass
            self.failed.emit("Нет символов для замены")
            return

        try:
            pyperclip.copy(converted)
        except Exception as e:
            self.failed.emit(f"Буфер обмена: {e}")
            return

        time.sleep(0.05)
        _send_ctrl_combo(VK_V)

        ru = sum(1 for c in text if c in RU_CHARS)
        en = sum(1 for c in text if c in EN_CHARS)
        direction = "RU → EN" if ru >= en else "EN → RU"
        log.info("converted %s, len=%d", direction, len(text))
        self.converted.emit(direction)

        def restore() -> None:
            time.sleep(0.5)
            try:
                pyperclip.copy(saved)
            except Exception:
                pass

        threading.Thread(target=restore, daemon=True).start()
