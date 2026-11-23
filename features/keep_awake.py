from __future__ import annotations

import ctypes

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

MODE_OFF = "off"
MODE_SYSTEM = "system"    # no sleep; the display still turns off on its timer
MODE_DISPLAY = "display"  # no sleep and the display stays on
ON_MODES = (MODE_SYSTEM, MODE_DISPLAY)

_FLAGS = {
    MODE_OFF: ES_CONTINUOUS,
    MODE_SYSTEM: ES_CONTINUOUS | ES_SYSTEM_REQUIRED,
    MODE_DISPLAY: ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED,
}


class KeepAwake:
    """Prevents Windows from sleeping, optionally keeping the display on too.

    MODE_SYSTEM only blocks system sleep, so the display still turns off
    after the power-plan timeout. MODE_DISPLAY also blocks that timeout.
    Implemented via SetThreadExecutionState. Flags persist until cleared
    (must be called from the same thread that set them — keep this object
    on the main GUI thread).
    """

    def __init__(self) -> None:
        self._mode = MODE_OFF

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def enabled(self) -> bool:
        return self._mode != MODE_OFF

    def set_mode(self, mode: str) -> None:
        if mode not in _FLAGS:
            raise ValueError(f"unknown keep-awake mode: {mode!r}")
        if mode == self._mode:
            return
        ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint(_FLAGS[mode]))
        self._mode = mode
