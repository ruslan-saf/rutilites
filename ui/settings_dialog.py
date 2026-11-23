from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import APP_NAME, DEFAULTS, Config
from features import autostart
from features.layout_fix import NAMED_VKS, parse_hotkey
from version import version_text

# Qt's portable key names -> the names parse_hotkey() understands.
_QT_TO_PYNPUT_NAMES = {
    "pgup": "pageup", "pgdown": "pagedown", "ins": "insert", "del": "delete",
    "backspace": "backspace", "return": "enter", "enter": "enter", "esc": "esc",
}
_PYNPUT_TO_QT_NAMES = {
    "pageup": "PgUp", "pagedown": "PgDown", "insert": "Ins", "delete": "Del",
    "enter": "Return", "return": "Return", "esc": "Esc", "escape": "Esc",
    "backspace": "Backspace", "space": "Space", "tab": "Tab",
}
# A hotkey pressed while the Russian layout is active is recorded by Qt as the
# Cyrillic letter; hotkeys match by key position, so map it to the Latin key.
_RU_TO_LATIN = dict(zip("йцукенгшщзфывапролдячсмить", "qwertyuiopasdfghjklzxcvbnm"))


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
            out.append(_RU_TO_LATIN.get(pl, pl))
        else:
            out.append(f"<{_QT_TO_PYNPUT_NAMES.get(pl, pl)}>")
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
            out.append(_PYNPUT_TO_QT_NAMES.get(pl, pl.capitalize()))
    return QKeySequence("+".join(out))


def hotkey_problem(spec: str) -> str | None:
    """Why this hotkey cannot be used, or None if it is fine."""
    if not spec:
        return "комбинация не задана"
    try:
        mods, _vk = parse_hotkey(spec)
    except ValueError:
        return "эта клавиша не поддерживается (буквы A–Z, цифры, F1–F12, стрелки, Home/End и т. п.)"
    tokens = [t.strip("<>").lower() for t in spec.split("+")]
    main = next((t for t in tokens if t not in ("ctrl", "shift", "alt", "cmd", "win")), "")
    if len(main) == 1 and not main.isascii():
        return "эта клавиша не поддерживается"
    if len(main) == 1 and not main.isalnum():
        return "знаки препинания не поддерживаются, выберите букву, цифру или F1–F12"
    if not mods and not (main in NAMED_VKS and main.startswith("f")):
        return "нужен модификатор (Ctrl, Alt, Shift или Win), иначе клавиша перестанет работать как обычно"
    return None


# (config key, label, hint, signal name)
HOTKEYS = [
    ("hotkey_layout_fix", "Исправить раскладку выделенного текста",
     "RU ↔ EN, каз-раскладка не обрабатывается", "hotkey_changed"),
    ("hotkey_screen_off", "Выключить / включить экран",
     "гасит только дисплей, включается любой клавишей", "screen_off_hotkey_changed"),
    ("hotkey_sleep", "Спящий режим",
     "переводит компьютер в сон (S3)", "sleep_hotkey_changed"),
]


class _Card(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(16, 14, 16, 14)
        self._lay.setSpacing(10)

    def add(self, w: QWidget) -> None:
        self._lay.addWidget(w)

    def add_layout(self, lay) -> None:  # type: ignore[no-untyped-def]
        self._lay.addLayout(lay)


class SettingsDialog(QDialog):
    hotkey_changed = Signal(str)
    screen_off_hotkey_changed = Signal(str)
    sleep_hotkey_changed = Signal(str)
    autostart_toggled = Signal(bool)
    keep_awake_default_changed = Signal(bool)
    keep_awake_mode_changed = Signal(str)
    check_updates_requested = Signal()

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle(f"{APP_NAME} — настройки")
        self.setMinimumWidth(680)
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
        version = QLabel(version_text())
        version.setObjectName("Subtitle")
        version.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        version.setTextInteractionFlags(Qt.TextSelectableByMouse)
        head = QHBoxLayout()
        head_text = QVBoxLayout()
        head_text.setSpacing(2)
        head_text.addWidget(title)
        head_text.addWidget(subtitle)
        updates_btn = QPushButton("Проверить обновления")
        updates_btn.clicked.connect(self.check_updates_requested.emit)
        head_ver = QVBoxLayout()
        head_ver.setSpacing(6)
        head_ver.addWidget(version, 0, Qt.AlignRight)
        head_ver.addWidget(updates_btn, 0, Qt.AlignRight)
        head.addLayout(head_text)
        head.addStretch(1)
        head.addLayout(head_ver)
        layout.addLayout(head)

        # --- Hotkeys card ---
        hdr = QLabel("Горячие клавиши")
        hdr.setObjectName("SectionHeader")
        layout.addWidget(hdr)

        hk_card = _Card()
        how = QLabel("Щёлкните по полю и нажмите новую комбинацию.")
        how.setObjectName("Subtitle")
        hk_card.add(how)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(0, 1)
        self._edits: dict[str, QKeySequenceEdit] = {}
        for row, (key, label, hint, _signal) in enumerate(HOTKEYS):
            name = QLabel(label)
            name.setWordWrap(True)
            sub = QLabel(hint)
            sub.setObjectName("Subtitle")
            sub.setWordWrap(True)
            text_box = QVBoxLayout()
            text_box.setSpacing(0)
            text_box.addWidget(name)
            text_box.addWidget(sub)

            edit = QKeySequenceEdit()
            edit.setMaximumSequenceLength(1)
            edit.setFixedWidth(170)
            edit.setKeySequence(pynput_to_qt(config.get(key)))
            edit.keySequenceChanged.connect(self._validate)
            self._edits[key] = edit

            reset = QPushButton("По умолчанию")
            reset.setToolTip(f"Вернуть {pynput_to_qt(DEFAULTS[key]).toString()}")
            reset.clicked.connect(lambda _c=False, k=key: self._reset(k))

            grid.addLayout(text_box, row * 2, 0)
            grid.addWidget(edit, row * 2, 1)
            grid.addWidget(reset, row * 2, 2)
            if row < len(HOTKEYS) - 1:
                line = QFrame()
                line.setObjectName("Divider")
                line.setFixedHeight(1)
                grid.addWidget(line, row * 2 + 1, 0, 1, 3)
        hk_card.add_layout(grid)

        self._error = QLabel("")
        self._error.setObjectName("Error")
        self._error.setWordWrap(True)
        self._error.hide()
        hk_card.add(self._error)
        layout.addWidget(hk_card)

        # --- Behaviour card ---
        hdr2 = QLabel("Поведение")
        hdr2.setObjectName("SectionHeader")
        layout.addWidget(hdr2)

        beh_card = _Card()
        self._autostart_cb = QCheckBox("Запускать при входе в Windows")
        self._autostart_cb.setChecked(autostart.is_enabled())
        self._keep_awake_default_cb = QCheckBox("Включать «не уходить в сон» при старте")
        self._keep_awake_default_cb.setChecked(bool(config.get("keep_awake_on_start")))
        beh_card.add(self._autostart_cb)
        beh_card.add(self._keep_awake_default_cb)
        mode_label = QLabel("Режим «не уходить в сон» (одиночный клик по значку и запуск):")
        mode_label.setWordWrap(True)
        self._keep_awake_mode_combo = QComboBox()
        self._keep_awake_mode_combo.addItem("Экран гаснет как обычно", "system")
        self._keep_awake_mode_combo.addItem("Экран не гаснет", "display")
        idx = self._keep_awake_mode_combo.findData(config.get("keep_awake_mode"))
        self._keep_awake_mode_combo.setCurrentIndex(max(idx, 0))
        beh_card.add(mode_label)
        beh_card.add(self._keep_awake_mode_combo)
        layout.addWidget(beh_card)

        layout.addStretch(1)

        # --- Buttons ---
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        self._save_btn = QPushButton("Сохранить")
        self._save_btn.setObjectName("Primary")
        self._save_btn.setDefault(True)
        self._save_btn.clicked.connect(self._save)
        btns.addWidget(cancel)
        btns.addWidget(self._save_btn)
        layout.addLayout(btns)

        self._validate()

    # --- hotkeys ---------------------------------------------------------

    def _reset(self, key: str) -> None:
        self._edits[key].setKeySequence(pynput_to_qt(DEFAULTS[key]))

    def _specs(self) -> dict[str, str]:
        return {key: qt_to_pynput(edit.keySequence()) for key, edit in self._edits.items()}

    def _validate(self) -> bool:
        labels = {key: label for key, label, _h, _s in HOTKEYS}
        problems = []
        specs = self._specs()
        for key, spec in specs.items():
            why = hotkey_problem(spec)
            if why:
                problems.append(f"«{labels[key]}»: {why}.")
        seen: dict[tuple, str] = {}
        for key, spec in specs.items():
            if hotkey_problem(spec):
                continue
            parsed = parse_hotkey(spec)
            if parsed in seen:
                problems.append(f"«{labels[seen[parsed]]}» и «{labels[key]}» – одинаковая комбинация.")
            seen.setdefault(parsed, key)
        self._error.setText("\n".join(problems))
        self._error.setVisible(bool(problems))
        self._save_btn.setEnabled(not problems)
        return not problems

    # --- save ------------------------------------------------------------

    def _save(self) -> None:
        if not self._validate():
            return
        for key, spec in self._specs().items():
            if spec != self._config.get(key):
                self._config.set(key, spec)
                signal_name = next(s for k, _l, _h, s in HOTKEYS if k == key)
                getattr(self, signal_name).emit(spec)

        autostart_on = self._autostart_cb.isChecked()
        if autostart_on != autostart.is_enabled():
            autostart.set_enabled(autostart_on)
            self._config.set("autostart", autostart_on)
            self.autostart_toggled.emit(autostart_on)

        kad = self._keep_awake_default_cb.isChecked()
        if kad != bool(self._config.get("keep_awake_on_start")):
            self._config.set("keep_awake_on_start", kad)
            self.keep_awake_default_changed.emit(kad)

        mode = self._keep_awake_mode_combo.currentData()
        if mode != self._config.get("keep_awake_mode"):
            self._config.set("keep_awake_mode", mode)
            self.keep_awake_mode_changed.emit(mode)

        self.accept()
