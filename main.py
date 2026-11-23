from __future__ import annotations

import sys
import time

from PySide6.QtCore import QSharedMemory, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from config import APP_NAME, Config
from features import autostart
from features.keep_awake import MODE_DISPLAY, MODE_OFF, MODE_SYSTEM, ON_MODES, KeepAwake
from features.restart import KEEP_AWAKE_FLAG, RESTART_FLAG, spawn_new_instance
from features.layout_fix import LayoutFix
from features.screen_off import ScreenOff
from features.sleep_hotkey import SleepHotkey
from ui.icon import app_icon
from ui.settings_dialog import SettingsDialog, pynput_to_qt
from ui.styles import DARK_QSS
from ui.tray import Tray


def pretty_hotkey(s: str) -> str:
    return pynput_to_qt(s).toString() or s


class App:
    def __init__(self, qt_app: QApplication, lock: QSharedMemory) -> None:
        self.qt_app = qt_app
        self._lock = lock
        self.config = Config()
        self.keep_awake = KeepAwake()
        self.layout_fix = LayoutFix(self.config.get("hotkey_layout_fix"))
        self.screen_off = ScreenOff(self.config.get("hotkey_screen_off"))
        self.sleep = SleepHotkey(self.config.get("hotkey_sleep"))
        self._screen_poll = QTimer()
        self._screen_poll.setInterval(500)
        self.tray = Tray()
        self._settings_dialog: SettingsDialog | None = None

        self._wire()
        self._apply_initial_state()

    def _wire(self) -> None:
        self.tray.toggle_keep_awake.connect(self._on_toggle_keep_awake)
        self.tray.keep_awake_mode_selected.connect(self._on_keep_awake_mode)
        self.tray.open_settings.connect(self._open_settings)
        self.tray.quit_requested.connect(self._quit)
        self.tray.restart_requested.connect(self._restart)
        self.tray.toggle_autostart.connect(self._on_toggle_autostart)
        self.layout_fix.converted.connect(self._on_layout_converted)
        self.layout_fix.failed.connect(self._on_layout_failed)
        self.screen_off.triggered.connect(self._on_screen_toggle)
        self.tray.screen_off_requested.connect(self._on_screen_off_from_menu)
        self.screen_off.failed.connect(self._on_layout_failed)
        self.tray.sleep_requested.connect(lambda: self.sleep.sleep_now(delay=1.0))
        self.sleep.failed.connect(self._on_layout_failed)
        self._screen_poll.timeout.connect(self._poll_screen)

    def _apply_initial_state(self) -> None:
        # Keep-awake initial
        mode = MODE_OFF
        if self.config.get("keep_awake_on_start"):
            mode = self._preferred_keep_awake_mode()
        for arg in sys.argv[1:]:
            if arg.startswith(KEEP_AWAKE_FLAG) and arg[len(KEEP_AWAKE_FLAG):] in ON_MODES:
                mode = arg[len(KEEP_AWAKE_FLAG):]  # state carried over by "Перезапустить"
        self.keep_awake.set_mode(mode)
        self.tray.set_keep_awake(mode)

        # Autostart reflection (file presence is source of truth)
        self.tray.set_autostart(autostart.is_enabled())

        # Hotkey
        self.tray.set_hotkey_label(pretty_hotkey(self.config.get("hotkey_layout_fix")))
        self.layout_fix.start()

        self.tray.set_screen_off_label(pretty_hotkey(self.config.get("hotkey_screen_off")))
        self.screen_off.start()

        self.tray.set_sleep_label(pretty_hotkey(self.config.get("hotkey_sleep")))
        self.sleep.start()

        self.tray.show()

    # --- handlers --------------------------------------------------------

    def _preferred_keep_awake_mode(self) -> str:
        mode = self.config.get("keep_awake_mode")
        return mode if mode in ON_MODES else MODE_SYSTEM

    def _on_toggle_keep_awake(self) -> None:
        """Single tray click: off <-> the last used keep-awake mode."""
        self._on_keep_awake_mode(MODE_OFF if self.keep_awake.enabled else self._preferred_keep_awake_mode())

    def _on_keep_awake_mode(self, mode: str) -> None:
        self.keep_awake.set_mode(mode)
        if mode in ON_MODES and mode != self.config.get("keep_awake_mode"):
            self.config.set("keep_awake_mode", mode)
        self.tray.set_keep_awake(mode)
        messages = {
            MODE_OFF: "Обычный режим включён",
            MODE_SYSTEM: "Компьютер не уснёт, экран гаснет как обычно",
            MODE_DISPLAY: "Компьютер не уснёт, экран не гаснет",
        }
        self.tray.notify(APP_NAME, messages[mode])

    def _open_settings(self) -> None:
        if self._settings_dialog is not None and self._settings_dialog.isVisible():
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return
        dlg = SettingsDialog(self.config)
        dlg.setWindowIcon(app_icon(False))
        dlg.hotkey_changed.connect(self._on_hotkey_changed)
        dlg.screen_off_hotkey_changed.connect(self._on_screen_off_hotkey_changed)
        dlg.sleep_hotkey_changed.connect(self._on_sleep_hotkey_changed)
        dlg.autostart_toggled.connect(self.tray.set_autostart)
        dlg.keep_awake_mode_changed.connect(self._on_keep_awake_default_mode_changed)
        self._settings_dialog = dlg
        dlg.exec()
        self._settings_dialog = None

    def _on_keep_awake_default_mode_changed(self, mode: str) -> None:
        # If keep-awake is on right now, switch it to the newly chosen mode.
        if self.keep_awake.enabled and self.keep_awake.mode != mode:
            self._on_keep_awake_mode(mode)

    def _on_hotkey_changed(self, new_hotkey: str) -> None:
        self.layout_fix.set_hotkey(new_hotkey)
        self.tray.set_hotkey_label(pretty_hotkey(new_hotkey))

    def _on_screen_off_hotkey_changed(self, new_hotkey: str) -> None:
        self.screen_off.set_hotkey(new_hotkey)
        self.tray.set_screen_off_label(pretty_hotkey(new_hotkey))

    def _on_sleep_hotkey_changed(self, new_hotkey: str) -> None:
        self.sleep.set_hotkey(new_hotkey)
        self.tray.set_sleep_label(pretty_hotkey(new_hotkey))

    def _on_screen_toggle(self) -> None:
        if self.screen_off.is_off:
            self.screen_off.turn_on()
            self._screen_poll.stop()
        else:
            self.screen_off.turn_off()
            self._screen_poll.start()

    def _on_screen_off_from_menu(self) -> None:
        # Give the mouse time to settle after the click, otherwise it wakes the display.
        if not self.screen_off.is_off:
            self.screen_off.turn_off(delay=1.0)
            self._screen_poll.start()

    def _poll_screen(self) -> None:
        if self.screen_off.woken_by_input():
            self._screen_poll.stop()

    def _on_toggle_autostart(self, checked: bool) -> None:
        autostart.set_enabled(checked)
        self.config.set("autostart", checked)
        # Re-read to confirm
        self.tray.set_autostart(autostart.is_enabled())

    def _on_layout_converted(self, direction: str) -> None:
        self.tray.notify(APP_NAME, f"Раскладка: {direction}")

    def _on_layout_failed(self, reason: str) -> None:
        self.tray.notify(APP_NAME, reason)

    def _shutdown(self) -> None:
        self.keep_awake.set_mode(MODE_OFF)
        self.layout_fix.stop()
        self.screen_off.stop()
        self.sleep.stop()
        self.tray.hide()

    def _quit(self) -> None:
        self._shutdown()
        self.qt_app.quit()

    def _restart(self) -> None:
        """Re-launch the app from its files on disk (picks up code changes)."""
        keep_awake_mode = self.keep_awake.mode
        self._shutdown()
        self._lock.detach()  # let the new copy take the single-instance lock
        try:
            spawn_new_instance(keep_awake_mode)
        except Exception as e:
            self.tray.show()
            self._lock.create(1)
            self._apply_initial_state()
            self.tray.notify(APP_NAME, f"Не удалось перезапустить: {e}")
            return
        self.qt_app.quit()


def main() -> int:
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName(APP_NAME)
    qt_app.setQuitOnLastWindowClosed(False)
    qt_app.setWindowIcon(app_icon(False))
    qt_app.setStyleSheet(DARK_QSS)

    # Single-instance lock
    lock = QSharedMemory(f"{APP_NAME}-singleton-lock")
    created = lock.create(1)
    if not created and RESTART_FLAG in sys.argv:
        # Restart from the tray: the old copy may still be shutting down.
        deadline = time.time() + 10
        while not created and time.time() < deadline:
            time.sleep(0.2)
            created = lock.create(1)
    if not created:
        QMessageBox.information(None, APP_NAME, "Приложение уже запущено (см. область уведомлений).")
        return 0

    _app = App(qt_app, lock)
    return qt_app.exec()


if __name__ == "__main__":
    sys.exit(main())
