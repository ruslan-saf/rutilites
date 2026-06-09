DARK_QSS = """
* {
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 10pt;
    color: #E6E8EE;
}

QDialog, QWidget#Root {
    background: #1B1E26;
}

QLabel#Title {
    font-size: 16pt;
    font-weight: 600;
    color: #FFFFFF;
}

QLabel#Subtitle {
    color: #8A93A6;
    font-size: 9pt;
}

QLabel#SectionHeader {
    color: #A8B0C2;
    font-size: 9pt;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding-top: 6px;
}

QFrame#Card {
    background: #242833;
    border: 1px solid #2E3344;
    border-radius: 10px;
}

QPushButton {
    background: #2E3344;
    border: 1px solid #3B4258;
    border-radius: 6px;
    padding: 6px 14px;
    color: #E6E8EE;
}
QPushButton:hover { background: #353B50; }
QPushButton:pressed { background: #2A2F3E; }

QPushButton#Primary {
    background: #4C7DF0;
    border: 1px solid #4C7DF0;
    color: white;
    font-weight: 600;
}
QPushButton#Primary:hover { background: #5A88F5; }
QPushButton#Primary:pressed { background: #3F6BD8; }

QKeySequenceEdit, QLineEdit {
    background: #1B1E26;
    border: 1px solid #3B4258;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #4C7DF0;
}
QKeySequenceEdit:focus, QLineEdit:focus { border-color: #4C7DF0; }

QCheckBox { spacing: 10px; }
QCheckBox::indicator {
    width: 18px; height: 18px;
    border: 1px solid #3B4258;
    border-radius: 4px;
    background: #1B1E26;
}
QCheckBox::indicator:hover { border-color: #4C7DF0; }
QCheckBox::indicator:checked {
    background: #4C7DF0;
    border-color: #4C7DF0;
    image: none;
}

QMenu {
    background: #242833;
    border: 1px solid #2E3344;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    padding: 8px 16px 8px 28px;
    border-radius: 5px;
    margin: 1px 2px;
}
QMenu::item:selected { background: #353B50; }
QMenu::item:disabled { color: #6A7388; }
QMenu::separator {
    height: 1px;
    background: #2E3344;
    margin: 4px 6px;
}
QMenu::indicator { width: 16px; height: 16px; margin-left: 8px; }
QMenu::indicator:checked {
    image: none;
}
"""
