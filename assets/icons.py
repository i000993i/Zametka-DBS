import os

from PyQt6.QtCore import Qt, QByteArray, QRectF
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer

_ICON_DIR = os.path.join(os.path.dirname(__file__), "svg")
_SIZES = (16, 24, 32, 48, 64)


def icon(name, color="#808080", hover_color="#eeeeee", size=None):
    path = os.path.join(_ICON_DIR, f"{name}.svg")
    if not os.path.isfile(path):
        return QIcon()
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    result = QIcon()
    sizes = (size,) if size else _SIZES
    for s in sizes:
        result.addPixmap(
            _svg_to_pixmap(raw.replace("currentColor", color), s),
            mode=QIcon.Mode.Normal,
        )
    for mode in (QIcon.Mode.Active, QIcon.Mode.Selected):
        for s in sizes:
            result.addPixmap(
                _svg_to_pixmap(raw.replace("currentColor", hover_color), s),
                mode=mode,
            )
    return result


def _svg_to_pixmap(svg_text: str, size: int = 24) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pix
