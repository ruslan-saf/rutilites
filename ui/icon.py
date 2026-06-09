from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap


def _draw(active: bool, size: int = 64) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    # gradient background circle
    g = QLinearGradient(0, 0, 0, size)
    if active:
        g.setColorAt(0.0, QColor("#5EE2A0"))
        g.setColorAt(1.0, QColor("#1FA971"))
        ring = QColor("#0E5B3D")
    else:
        g.setColorAt(0.0, QColor("#7AA7FF"))
        g.setColorAt(1.0, QColor("#3A6BD8"))
        ring = QColor("#1B3B85")

    p.setBrush(QBrush(g))
    p.setPen(QPen(ring, max(2, size // 32)))
    margin = size // 10
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    p.drawEllipse(rect)

    # central glyph: a stylised "R"
    p.setPen(QPen(QColor("white"), max(2, size // 16)))
    f = p.font()
    f.setFamily("Segoe UI")
    f.setBold(True)
    f.setPixelSize(int(size * 0.55))
    p.setFont(f)
    p.drawText(rect, Qt.AlignCenter, "R")

    p.end()
    return pm


def app_icon(active: bool = False) -> QIcon:
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_draw(active, s))
    return icon
