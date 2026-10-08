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
    toggle_keep_awake = Signal()
    screen_off_requested = Signal()
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

        self._keep_awake_action = QAction("Не уходить в сон", menu)
        self._keep_awake_action.setCheckable(True)
        self._keep_awake_action.triggered.connect(lambda _checked: self.toggle_keep_awake.emit())
        menu.addAction(self._keep_awake_action)

        self._fix_layout_info = QAction("Исправить раскладку: —", menu)
        self._fix_layout_info.setEnabled(False)
        menu.addAction(self._fix_layout_info)

        self._screen_off_action = QAction("Выключить экран", menu)
        self._screen_off_action.triggered.connect(lambda _checked: self.screen_off_requested.emit())
        menu.addAction(self._screen_off_action)

        menu.addSeparator()

        self._autostart_action = QAction("Автозапуск", menu)
        self._autostart_action.setCheckable(True)
        self._autostart_action.triggered.connect(self.toggle_autostart.emit)
        menu.addAction(self._autostart_action)

        settings_action = QAction("Настройки…", menu)
        settings_action.triggered.connect(self.open_settings.emit)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("Выход", menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)

    def show(self) -> None:
        self._tray.show()

    def notify(self, title: str, message: str) -> None:
        self._tray.showMessage(title, message, app_icon(False), 2500)

    def set_keep_awake(self, on: bool) -> None:
        self._keep_awake_action.setChecked(on)
        self._tray.setIcon(app_icon(on))
        self._status_action.setText(f"{APP_NAME} · " + ("не уходит в сон" if on else "обычный режим"))
        self._tray.setToolTip(f"{APP_NAME}\n" + ("Не уходить в сон: ВКЛ" if on else "Не уходить в сон: выкл"))

    def set_autostart(self, on: bool) -> None:
        self._autostart_action.setChecked(on)

    def set_hotkey_label(self, pretty: str) -> None:
        self._fix_layout_info.setText(f"Исправить раскладку: {pretty}")

    def set_screen_off_label(self, pretty: str) -> None:
        self._screen_off_action.setText(f"Выключить экран ({pretty})")

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:  # single click
            self.toggle_keep_awake.emit()
        elif reason == QSystemTrayIcon.DoubleClick:
            self.open_settings.emit()

    def menu(self) -> QMenu:
        return self._menu
