from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QSize, pyqtSignal
from zametka_dbs.ui.styles import _THEME_VARS
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetricsF, QPen, QTextCursor

from zametka_dbs.core.config import get_config
from zametka_dbs.core.rust_bridge import HAS_RUST, rust_compute_line_numbers


def _py_compute_line_numbers(text: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    display = 0
    for line in text.split('\n'):
        t = line.strip()
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
    gutter_clicked = pyqtSignal(int)

    def __init__(self, editor=None):
        super().__init__(editor)
        self._editor = editor
        self._current_line = 0
        self._line_data: list[tuple[int, str]] = []
        config = get_config()
        self._dark = config.get("theme", "dark") == "dark"
        self._font = QFont()
        self._fmf = None
        self.setFixedWidth(40)

    def set_dark(self, dark: bool):
        self._dark = dark
        self.update()

    def set_editor(self, editor):
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

    def _on_blocks_changed(self, count):
        self._classify()
        self._update_width()

    def _on_cursor_moved(self):
        if self._editor:
            self._current_line = self._editor.textCursor().blockNumber()
            self.update()

    def _classify(self):
        if not self._editor:
            return
        text = self._editor.toPlainText()
        if HAS_RUST and rust_compute_line_numbers is not None:
            self._line_data = rust_compute_line_numbers(text)
        else:
            self._line_data = _py_compute_line_numbers(text)
        self._update_width()

    def _update_width(self):
        max_num = max((d for d, t in self._line_data if t != "blank"), default=0)
        digits = max(3, len(str(max(max_num, 1))))
        new_w = int(self._fmf.horizontalAdvance("0" * digits)) + 20
        self.setFixedWidth(new_w)
        if self._editor:
            self._editor.setViewportMargins(new_w, 0, 0, 0)

    def paintEvent(self, event):
        if not self._editor or self._fmf is None:
            return

        painter = QPainter(self)
        bg = "#0a0a0a" if self._dark else "#ffffff"
        border = "#1a1a1a" if self._dark else "#e0e0e0"
        painter.fillRect(event.rect(), QColor(bg))

        painter.setPen(QPen(QColor(border), 1))
        x_right = self.width() - 1
        painter.drawLine(x_right, event.rect().top(),
                         x_right, event.rect().bottom())

        doc = self._editor.document()
        offset = self._editor.contentOffset()
        visible_top = event.rect().top()
        visible_bot = event.rect().bottom()

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
                n = block.blockNumber()
                if n < len(self._line_data):
                    display_num, typ = self._line_data[n]
                else:
                    display_num, typ = 0, "normal"
                active = n == self._current_line

                cursor = QTextCursor(block)
                cursor_rect = self._editor.cursorRect(cursor)
                draw_y = cursor_rect.y()
                line_h = cursor_rect.height()

                if active:
                    hl = QColor(_THEME_VARS["dark" if self._dark else "light"]["fg1"])
                    hl.setAlpha(10)
                    painter.fillRect(QRectF(0, draw_y, self.width() - 1, line_h), hl)

                if active:
                    c = QColor(_THEME_VARS["dark" if self._dark else "light"]["fg1"])
                elif typ == "heading":
                    c = QColor("#9d7cd8" if self._dark else "#8250df")
                elif typ == "code":
                    c = QColor("#7fd88f" if self._dark else "#1a7f37")
                elif typ == "list":
                    c = QColor("#56b6c2" if self._dark else "#0891b1")
                elif typ == "blank":
                    c = QColor("transparent")
                else:
                    c = QColor("#808080" if self._dark else "#666666")

                painter.setPen(c)
                painter.setFont(self._font)
                txt = str(display_num) if typ != "blank" else ""
                if txt:
                    text_w = self._fmf.horizontalAdvance(txt)
                    x = self.width() - text_w - 18
                    rect = QRectF(x, draw_y, text_w + 8, line_h)
                    painter.drawText(rect, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), txt)

            block = block.next()

        painter.end()

    def sizeHint(self):
        return QSize(self.width(), 0)
