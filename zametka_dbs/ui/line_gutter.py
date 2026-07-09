from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QPlainTextEdit
from PyQt6.QtCore import Qt, QRectF, QSize
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QFont,
    QFontMetricsF,
    QPen,
    QTextCursor,
    QPaintEvent,
)
from zametka_dbs.ui.styles import _THEME_VARS
from zametka_dbs.core.config import get_config
from zametka_dbs.core.rust_bridge import HAS_RUST, rust_compute_line_numbers


def _py_compute_line_numbers(text: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    display = 0
    for line in text.split("\n"):
        t: str = line.strip()
        if not t:
            result.append((display, "blank"))
        else:
            display += 1
            if t.startswith("```"):
                result.append((display, "code"))
            elif t.startswith("#"):
                result.append((display, "heading"))
            elif t.startswith(("- ", "* ", "+ ")):
                result.append((display, "list"))
            else:
                result.append((display, "normal"))
    return result


class LineGutter(QWidget):
    def __init__(self, editor: QPlainTextEdit | None = None) -> None:
        super().__init__(editor)
        self._editor: QPlainTextEdit | None = editor
        self._current_line: int = 0
        self._line_data: list[tuple[int, str]] = []
        config = get_config()
        self._dark: bool = config.get("theme", "dark") == "dark"
        self._font: QFont = QFont()
        self._fmf: QFontMetricsF | None = None
        self.setFixedWidth(40)

    def set_dark(self, dark: bool) -> None:
        self._dark = dark
        self.update()

    def set_editor(self, editor: QPlainTextEdit | None) -> None:
        self._editor = editor
        if editor is None:
            return
        self._font = QFont(editor.font())
        self._font.setPointSize(max(6, self._font.pointSize() - 2))
        self._fmf = QFontMetricsF(self._font)
        editor.blockCountChanged.connect(self._on_blocks_changed)
        editor.verticalScrollBar().valueChanged.connect(self.update)
        editor.cursorPositionChanged.connect(self._on_cursor_moved)
        editor.textChanged.connect(self._classify)
        editor.selectionChanged.connect(self.update)
        editor.document().contentsChanged.connect(self._classify)
        self._classify()
        self._update_width()

    def _on_blocks_changed(self, count: int) -> None:
        self._classify()
        self._update_width()

    def _on_cursor_moved(self) -> None:
        if self._editor:
            self._current_line = self._editor.textCursor().blockNumber()
            self.update()

    def _classify(self) -> None:
        if not self._editor:
            return
        text: str = self._editor.toPlainText()
        if HAS_RUST and rust_compute_line_numbers is not None:
            self._line_data = rust_compute_line_numbers(text)
        else:
            self._line_data = _py_compute_line_numbers(text)
        self._update_width()

    def _update_width(self) -> None:
        max_num = max((d for d, t in self._line_data if t != "blank"), default=0)
        digits = max(3, len(str(max(max_num, 1))))
        if self._fmf is not None:
            new_w: int = int(self._fmf.horizontalAdvance("0" * digits)) + 20
        else:
            new_w = 40
        self.setFixedWidth(new_w)
        if self._editor:
            self._editor.setViewportMargins(new_w, 0, 0, 0)

    def paintEvent(self, event: QPaintEvent | None) -> None:
        if not self._editor or self._fmf is None:
            return

        painter: QPainter = QPainter(self)
        self._draw_background(painter, event)

        doc = self._editor.document()
        offset = self._editor.contentOffset()
        if event is not None:
            visible_top: int = event.rect().top()
            visible_bot: int = event.rect().bottom()
        else:
            visible_top = 0
            visible_bot = self.height()

        block = doc.begin()
        while block.isValid():
            geo = self._editor.blockBoundingGeometry(block)
            viewport_rect = geo.translated(-offset)
            top = viewport_rect.y()
            height = viewport_rect.height()
            bot = top + height

            if top > visible_bot:
                break
            if bot >= visible_top:
                n: int = block.blockNumber()
                if n < len(self._line_data):
                    display_num, typ = self._line_data[n]
                else:
                    display_num, typ = 0, "normal"
                active: bool = n == self._current_line

                cursor: QTextCursor = QTextCursor(block)
                cursor_rect = self._editor.cursorRect(cursor)
                draw_y = cursor_rect.y()
                line_h = cursor_rect.height()

                if active:
                    hl: QColor = QColor(
                        _THEME_VARS["dark" if self._dark else "light"]["fg1"]
                    )
                    hl.setAlpha(10)
                    painter.fillRect(
                        QRectF(0, draw_y, self.width() - 1, line_h), hl
                    )

                c = self._line_color(typ, active)
                painter.setPen(c)
                painter.setFont(self._font)
                txt: str = str(display_num) if typ != "blank" else ""
                if txt:
                    text_w = self._fmf.horizontalAdvance(txt)
                    x: float = self.width() - text_w - 18
                    rect = QRectF(x, draw_y, text_w + 8, line_h)
                    painter.drawText(
                        rect,
                        int(
                            Qt.AlignmentFlag.AlignRight
                            | Qt.AlignmentFlag.AlignVCenter
                        ),
                        txt,
                    )

            block = block.next()

        painter.end()

    def _draw_background(self, painter: QPainter, event: QPaintEvent | None) -> None:
        bg: str = "#0a0a0a" if self._dark else "#ffffff"
        border: str = "#1a1a1a" if self._dark else "#e0e0e0"
        if event is not None:
            painter.fillRect(event.rect(), QColor(bg))
        painter.setPen(QPen(QColor(border), 1))
        x_right: int = self.width() - 1
        if event is not None:
            painter.drawLine(x_right, event.rect().top(), x_right, event.rect().bottom())

    def _line_color(self, typ: str, active: bool) -> QColor:
        if active:
            return QColor(
                _THEME_VARS["dark" if self._dark else "light"]["fg1"]
            )
        if typ == "heading":
            return QColor("#9d7cd8" if self._dark else "#8250df")
        if typ == "code":
            return QColor("#7fd88f" if self._dark else "#1a7f37")
        if typ == "list":
            return QColor("#56b6c2" if self._dark else "#0891b1")
        if typ == "blank":
            return QColor("transparent")
        return QColor("#808080" if self._dark else "#666666")

    def sizeHint(self) -> QSize:
        return QSize(self.width(), 0)
