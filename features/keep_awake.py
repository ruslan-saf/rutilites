from __future__ import annotations

import ctypes

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


class KeepAwake:
    """Prevents Windows from sleeping or turning off the display while enabled.

    Implemented via SetThreadExecutionState. Flags persist until cleared
    (must be called from the same thread that set them — keep this object
    on the main GUI thread).
    """

    def __init__(self) -> None:
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set(self, on: bool) -> None:
        if on == self._enabled:
            return
        if on:
            flags = ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED
        else:
            flags = ES_CONTINUOUS
        ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint(flags))
        self._enabled = on

    def toggle(self) -> bool:
        self.set(not self._enabled)
        return self._enabled
