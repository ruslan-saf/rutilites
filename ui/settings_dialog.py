from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import APP_NAME, Config
from features import autostart


def qt_to_pynput(seq: QKeySequence) -> str:
    text = seq.toString(QKeySequence.PortableText)  # e.g. "Ctrl+Shift+Z"
    if not text:
        return ""
    # Only first chord
    if "," in text:
        text = text.split(",", 1)[0]
    parts = [p.strip() for p in text.split("+") if p.strip()]
    out = []
    for p in parts:
        pl = p.lower()
        if pl in ("ctrl", "shift", "alt"):
            out.append(f"<{pl}>")
        elif pl == "meta":
            out.append("<cmd>")
        elif len(p) == 1:
            out.append(pl)
        else:
            out.append(f"<{pl}>")
    return "+".join(out)


def pynput_to_qt(s: str) -> QKeySequence:
    if not s:
        return QKeySequence()
    parts = s.split("+")
    mapping = {"ctrl": "Ctrl", "shift": "Shift", "alt": "Alt", "cmd": "Meta"}
    out = []
    for p in parts:
        pl = p.strip().strip("<>").lower()
        if pl in mapping:
            out.append(mapping[pl])
        elif len(pl) == 1:
            out.append(pl.upper())
        else:
            out.append(pl.capitalize())
    return QKeySequence("+".join(out))


class _Card(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(16, 14, 16, 14)
        self._lay.setSpacing(10)

    def add(self, w: QWidget) -> None:
        self._lay.addWidget(w)


class SettingsDialog(QDialog):
    hotkey_changed = Signal(str)
    autostart_toggled = Signal(bool)
    keep_awake_default_changed = Signal(bool)

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle(f"{APP_NAME} — настройки")
        self.setMinimumWidth(440)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        root = QWidget(self)
        root.setObjectName("Root")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel(APP_NAME)
        title.setObjectName("Title")
        subtitle = QLabel("Маленькие удобства для Windows")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # --- Hotkey card ---
        hdr = QLabel("Раскладка")
        hdr.setObjectName("SectionHeader")
        layout.addWidget(hdr)

        hotkey_card = _Card()
        hk_label = QLabel("Хоткей для смены раскладки выделенного текста")
        self._hotkey_edit = QKeySequenceEdit()
        self._hotkey_edit.setKeySequence(pynput_to_qt(config.get("hotkey_layout_fix")))
        hint = QLabel("Например: Ctrl+Shift+Z. Каз-раскладка не обрабатывается.")
        hint.setObjectName("Subtitle")
        hint.setWordWrap(True)
        hotkey_card.add(hk_label)
        hotkey_card.add(self._hotkey_edit)
        hotkey_card.add(hint)
        layout.addWidget(hotkey_card)

        # --- Behaviour card ---
        hdr2 = QLabel("Поведение")
        hdr2.setObjectName("SectionHeader")
        layout.addWidget(hdr2)

        beh_card = _Card()
        self._autostart_cb = QCheckBox("Запускать при входе в Windows")
        self._autostart_cb.setChecked(autostart.is_enabled())
        self._keep_awake_default_cb = QCheckBox("Включать «не выключать экран» при старте")
        self._keep_awake_default_cb.setChecked(bool(config.get("keep_awake_on_start")))
        beh_card.add(self._autostart_cb)
        beh_card.add(self._keep_awake_default_cb)
        layout.addWidget(beh_card)

        layout.addStretch(1)

        # --- Buttons ---
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Сохранить")
        save.setObjectName("Primary")
        save.setDefault(True)
        save.clicked.connect(self._save)
        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _save(self) -> None:
        new_hotkey = qt_to_pynput(self._hotkey_edit.keySequence())
        if new_hotkey and new_hotkey != self._config.get("hotkey_layout_fix"):
            self._config.set("hotkey_layout_fix", new_hotkey)
            self.hotkey_changed.emit(new_hotkey)

        autostart_on = self._autostart_cb.isChecked()
        if autostart_on != autostart.is_enabled():
            autostart.set_enabled(autostart_on)
            self._config.set("autostart", autostart_on)
            self.autostart_toggled.emit(autostart_on)

        kad = self._keep_awake_default_cb.isChecked()
        if kad != bool(self._config.get("keep_awake_on_start")):
            self._config.set("keep_awake_on_start", kad)
            self.keep_awake_default_changed.emit(kad)

        self.accept()
