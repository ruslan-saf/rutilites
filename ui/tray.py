from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from config import APP_NAME
from ui.icon import app_icon


class Tray(QObject):
    open_settings = Signal()
    quit_requested = Signal()
    restart_requested = Signal()
    check_updates_requested = Signal()
    toggle_keep_awake = Signal()
    keep_awake_mode_selected = Signal(str)  # "off" | "system" | "display"
    screen_off_requested = Signal()
    sleep_requested = Signal()
    toggle_autostart = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tray = QSystemTrayIcon(app_icon(False), parent)
        self._tray.setToolTip(APP_NAME)

        menu = QMenu()
        self._menu = menu

        self._status_action = QAction(f"{APP_NAME}", menu)
        self._status_action.setEnabled(False)
        menu.addAction(self._status_action)
        menu.addSeparator()

        self._keep_awake_action = QAction("Не уходить в сон (экран гаснет как обычно)", menu)
        self._keep_awake_action.setCheckable(True)
        self._keep_awake_action.triggered.connect(
            lambda checked: self.keep_awake_mode_selected.emit("system" if checked else "off"))
        menu.addAction(self._keep_awake_action)

        self._keep_awake_display_action = QAction("Не уходить в сон и не гасить экран", menu)
        self._keep_awake_display_action.setCheckable(True)
        self._keep_awake_display_action.triggered.connect(
            lambda checked: self.keep_awake_mode_selected.emit("display" if checked else "off"))
        menu.addAction(self._keep_awake_display_action)

        self._fix_layout_info = QAction("Исправить раскладку: —", menu)
        self._fix_layout_info.setEnabled(False)
        menu.addAction(self._fix_layout_info)

        self._screen_off_action = QAction("Выключить экран", menu)
        self._screen_off_action.triggered.connect(lambda _checked: self.screen_off_requested.emit())
        menu.addAction(self._screen_off_action)

        self._sleep_action = QAction("Спящий режим", menu)
        self._sleep_action.triggered.connect(lambda _checked: self.sleep_requested.emit())
        menu.addAction(self._sleep_action)

        menu.addSeparator()

        self._autostart_action = QAction("Автозапуск", menu)
        self._autostart_action.setCheckable(True)
        self._autostart_action.triggered.connect(self.toggle_autostart.emit)
        menu.addAction(self._autostart_action)

        settings_action = QAction("Настройки…", menu)
        settings_action.triggered.connect(self.open_settings.emit)
        menu.addAction(settings_action)

        menu.addSeparator()

        updates_action = QAction("Проверить обновления…", menu)
        updates_action.triggered.connect(self.check_updates_requested.emit)
        menu.addAction(updates_action)

        restart_action = QAction("Перезапустить", menu)
        restart_action.triggered.connect(self.restart_requested.emit)
        menu.addAction(restart_action)

        quit_action = QAction("Выход", menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def notify(self, title: str, message: str) -> None:
        self._tray.showMessage(title, message, app_icon(False), 2500)

    def set_keep_awake(self, mode: str) -> None:
        on = mode != "off"
        self._keep_awake_action.setChecked(mode == "system")
        self._keep_awake_display_action.setChecked(mode == "display")
        self._tray.setIcon(app_icon(on))
        status = {
            "off": "обычный режим",
            "system": "не уходит в сон",
            "display": "не уходит в сон, экран не гаснет",
        }[mode]
        self._status_action.setText(f"{APP_NAME} · {status}")
        self._tray.setToolTip(f"{APP_NAME}\n" + ("Не уходить в сон: " + status if on else "Не уходить в сон: выкл"))

    def set_autostart(self, on: bool) -> None:
        self._autostart_action.setChecked(on)

    def set_hotkey_label(self, pretty: str) -> None:
        self._fix_layout_info.setText(f"Исправить раскладку: {pretty}")

    def set_screen_off_label(self, pretty: str) -> None:
        self._screen_off_action.setText(f"Выключить экран ({pretty})")

    def set_sleep_label(self, pretty: str) -> None:
        self._sleep_action.setText(f"Спящий режим ({pretty})")

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:  # single click
            self.toggle_keep_awake.emit()
        elif reason == QSystemTrayIcon.DoubleClick:
            self.open_settings.emit()

    def menu(self) -> QMenu:
        return self._menu
