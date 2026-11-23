from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import APP_NAME
from features import updater


class _Bridge(QObject):
    """Carries results from the worker thread back to the GUI thread."""
    checked = Signal(object)   # UpdateInfo
    applied = Signal()
    progress = Signal(str)
    failed = Signal(str)


class UpdateDialog(QDialog):
    """Check for updates on open; offer to install and restart."""

    restart_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — обновления")
        self.setMinimumWidth(520)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self._info: updater.UpdateInfo | None = None

        root = QWidget(self)
        root.setObjectName("Root")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        title = QLabel("Обновления")
        title.setObjectName("Title")
        lay.addWidget(title)

        self._status = QLabel("Проверяю…")
        self._status.setWordWrap(True)
        self._status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self._status)

        self._details = QPlainTextEdit()
        self._details.setReadOnly(True)
        self._details.setMinimumHeight(140)
        self._details.hide()
        lay.addWidget(self._details)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self._close_btn = QPushButton("Закрыть")
        self._close_btn.clicked.connect(self.reject)
        self._update_btn = QPushButton("Обновить и перезапустить")
        self._update_btn.setObjectName("Primary")
        self._update_btn.clicked.connect(self._start_apply)
        self._update_btn.hide()
        btns.addWidget(self._close_btn)
        btns.addWidget(self._update_btn)
        lay.addLayout(btns)

        self._bridge = _Bridge()
        self._bridge.checked.connect(self._on_checked)
        self._bridge.applied.connect(self._on_applied)
        self._bridge.progress.connect(self._status.setText)
        self._bridge.failed.connect(self._on_failed)
        self._run(self._check_worker)

    # --- workers (background thread) ---------------------------------------

    def _run(self, target) -> None:  # type: ignore[no-untyped-def]
        threading.Thread(target=target, daemon=True).start()

    def _check_worker(self) -> None:
        try:
            self._bridge.checked.emit(updater.check())
        except updater.UpdateError as e:
            self._bridge.failed.emit(str(e))
        except Exception as e:  # unexpected: still show it instead of hanging
            self._bridge.failed.emit(f"Ошибка проверки: {e}")

    def _apply_worker(self) -> None:
        try:
            updater.apply(self._info, self._bridge.progress.emit)  # type: ignore[arg-type]
            self._bridge.applied.emit()
        except updater.UpdateError as e:
            self._bridge.failed.emit(str(e))
        except Exception as e:
            self._bridge.failed.emit(f"Ошибка обновления: {e}")

    # --- GUI thread --------------------------------------------------------

    def _on_checked(self, info: updater.UpdateInfo) -> None:
        self._info = info
        if not info.available:
            extra = f" В этой копии {info.ahead} коммит(ов), которых нет на сервере." if info.ahead else ""
            self._status.setText(f"Установлена последняя версия ({info.current_version}).{extra}")
            return
        same = info.remote_version == info.current_version
        version = f"Доступно обновление ({info.behind} коммит(ов))" if same else \
            f"Доступна версия {info.remote_version} (сейчас {info.current_version}), коммитов: {info.behind}"
        notes = []
        if info.needs_requirements:
            notes.append("Будут установлены новые библиотеки, это может занять несколько минут.")
        if info.local_changes:
            notes.append("В файлах программы есть локальные изменения, автоматически обновить нельзя: "
                         + ", ".join(info.local_changes))
        if info.ahead:
            notes.append(f"В этой копии {info.ahead} коммит(ов), которых нет на сервере; обновите вручную.")
        self._status.setText(version + ("\n" + "\n".join(notes) if notes else ""))
        self._details.setPlainText("\n".join(info.commits))
        self._details.show()
        self._update_btn.setVisible(not info.local_changes and not info.ahead)

    def _start_apply(self) -> None:
        self._update_btn.setEnabled(False)
        self._close_btn.setEnabled(False)
        self._status.setText("Обновляю…")
        self._run(self._apply_worker)

    def _on_applied(self) -> None:
        self._status.setText("Обновлено. Перезапускаю…")
        self.accept()
        self.restart_requested.emit()

    def _on_failed(self, message: str) -> None:
        self._status.setText(message)
        self._update_btn.hide()
        self._close_btn.setEnabled(True)
