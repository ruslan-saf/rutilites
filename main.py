from __future__ import annotations

import sys

from PySide6.QtCore import QSharedMemory, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from config import APP_NAME, Config
from features import autostart
from features.keep_awake import KeepAwake
from features.layout_fix import LayoutFix
from ui.icon import app_icon
from ui.settings_dialog import SettingsDialog, pynput_to_qt
from ui.styles import DARK_QSS
from ui.tray import Tray


def pretty_hotkey(s: str) -> str:
    return pynput_to_qt(s).toString() or s


class App:
    def __init__(self, qt_app: QApplication) -> None:
        self.qt_app = qt_app
        self.config = Config()
        self.keep_awake = KeepAwake()
        self.layout_fix = LayoutFix(self.config.get("hotkey_layout_fix"))
        self.tray = Tray()
        self._settings_dialog: SettingsDialog | None = None

        self._wire()
        self._apply_initial_state()

    def _wire(self) -> None:
        self.tray.toggle_keep_awake.connect(self._on_toggle_keep_awake)
        self.tray.open_settings.connect(self._open_settings)
        self.tray.quit_requested.connect(self._quit)
        self.tray.toggle_autostart.connect(self._on_toggle_autostart)
        self.layout_fix.converted.connect(self._on_layout_converted)
        self.layout_fix.failed.connect(self._on_layout_failed)

    def _apply_initial_state(self) -> None:
        # Keep-awake initial
        self.keep_awake.set(bool(self.config.get("keep_awake_on_start")))
        self.tray.set_keep_awake(self.keep_awake.enabled)

        # Autostart reflection (file presence is source of truth)
        self.tray.set_autostart(autostart.is_enabled())

        # Hotkey
        self.tray.set_hotkey_label(pretty_hotkey(self.config.get("hotkey_layout_fix")))
        self.layout_fix.start()

        self.tray.show()

    # --- handlers --------------------------------------------------------

    def _on_toggle_keep_awake(self) -> None:
        on = self.keep_awake.toggle()
        self.tray.set_keep_awake(on)
        self.tray.notify(APP_NAME, "Экран не будет гаснуть" if on else "Обычный режим включён")

    def _open_settings(self) -> None:
        if self._settings_dialog is not None and self._settings_dialog.isVisible():
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return
        dlg = SettingsDialog(self.config)
        dlg.setWindowIcon(app_icon(False))
        dlg.hotkey_changed.connect(self._on_hotkey_changed)
        dlg.autostart_toggled.connect(self.tray.set_autostart)
        self._settings_dialog = dlg
        dlg.exec()
        self._settings_dialog = None

    def _on_hotkey_changed(self, new_hotkey: str) -> None:
        self.layout_fix.set_hotkey(new_hotkey)
        self.tray.set_hotkey_label(pretty_hotkey(new_hotkey))

    def _on_toggle_autostart(self, checked: bool) -> None:
        autostart.set_enabled(checked)
        self.config.set("autostart", checked)
        # Re-read to confirm
        self.tray.set_autostart(autostart.is_enabled())

    def _on_layout_converted(self, direction: str) -> None:
        self.tray.notify(APP_NAME, f"Раскладка: {direction}")

    def _on_layout_failed(self, reason: str) -> None:
        self.tray.notify(APP_NAME, reason)

    def _quit(self) -> None:
        self.keep_awake.set(False)
        self.layout_fix.stop()
        self.qt_app.quit()


def main() -> int:
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName(APP_NAME)
    qt_app.setQuitOnLastWindowClosed(False)
    qt_app.setWindowIcon(app_icon(False))
    qt_app.setStyleSheet(DARK_QSS)

    # Single-instance lock
    lock = QSharedMemory(f"{APP_NAME}-singleton-lock")
    if not lock.create(1):
        QMessageBox.information(None, APP_NAME, "Приложение уже запущено (см. область уведомлений).")
        return 0

    _app = App(qt_app)
    return qt_app.exec()


if __name__ == "__main__":
    sys.exit(main())
