from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QSize, pyqtSignal
from zametka_dbs.ui.styles import _THEME_VARS
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetricsF, QPen

from zametka_dbs.core.config import get_config


class LineGutter(QWidget):
    gutter_clicked = pyqtSignal(int)

    def __init__(self, editor=None):
        super().__init__(editor)
        self._editor = editor
        self._current_line = 0
        self._line_types: dict[int, str] = {}
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
        self._fmf = QFontMetricsF(self._font)
        self.setFixedWidth(self._calc_width(1))
        editor.blockCountChanged.connect(self._on_blocks_changed)
        editor.verticalScrollBar().valueChanged.connect(self.update)
        editor.cursorPositionChanged.connect(self._on_cursor_moved)
        editor.textChanged.connect(self._classify)
        editor.selectionChanged.connect(self.update)
        self._classify()

    def _on_blocks_changed(self, count):
        new_w = self._calc_width(count)
        self.setFixedWidth(new_w)
        if self._editor:
            self._editor.setViewportMargins(new_w, 0, 0, 0)
        self.update()

    def _on_cursor_moved(self):
        if self._editor:
            self._current_line = self._editor.textCursor().blockNumber()
            self.update()

    def _classify(self):
        if not self._editor:
            return
        self._line_types.clear()
        block = self._editor.document().begin()
        while block.isValid():
            t = block.text().strip()
            n = block.blockNumber()
            if not t:
                self._line_types[n] = "blank"
            elif t.startswith("```"):
                self._line_types[n] = "code"
            elif t.startswith("#"):
                self._line_types[n] = "heading"
            elif t.startswith(("- ", "* ", "+ ")):
                self._line_types[n] = "list"
            else:
                self._line_types[n] = "normal"
            block = block.next()

    def _calc_width(self, block_count: int) -> int:
        digits = max(3, len(str(max(block_count, 1))))
        return int(self._fmf.horizontalAdvance("0" * digits)) + 20

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
                typ = self._line_types.get(n, "normal")
                active = n == self._current_line

                block_layout = block.layout()
                draw_y = top
                line_h = height
                if block_layout and block_layout.lineCount() > 0:
                    line = block_layout.lineAt(0)
                    draw_y = top + line.y()
                    line_h = line.height()

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
                txt = str(n + 1)
                x = self.width() - self._fmf.horizontalAdvance(txt) - 12
                y = draw_y + self._fmf.ascent()
                painter.drawText(int(x), int(y), txt)

            block = block.next()

        painter.end()

    def sizeHint(self):
        return QSize(self.width(), 0)
