from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, QSize, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen


class LineGutter(QWidget):
    gutter_clicked = pyqtSignal(int)

    def __init__(self, editor=None):
        super().__init__(editor)
        self._editor = editor
        self._current_line = 0
        self._line_types: dict[int, str] = {}
        self._font = QFont("Consolas", 14)
        self._font.setStyleHint(QFont.StyleHint.Monospace)
        self._fm = QFontMetrics(self._font)
        self.setFixedWidth(self._calc_width(1))

    def set_editor(self, editor):
        self._editor = editor
        if editor is None:
            return
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
        return self._fm.horizontalAdvance("0" * digits) + 20

    def paintEvent(self, event):
        if not self._editor:
            return

        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#0a0a0a"))

        # Right border
        painter.setPen(QPen(QColor("#1a1a1a"), 1))
        x_right = self.width() - 1
        painter.drawLine(x_right, event.rect().top(),
                         x_right, event.rect().bottom())

        doc = self._editor.document()
        offset = self._editor.contentOffset()
        scroll = self._editor.verticalScrollBar().value()
        block = doc.begin()

        while block.isValid():
            geo = self._editor.blockBoundingGeometry(block)
            # Translate from content coords to viewport coords
            viewport_rect = geo.translated(-offset)
            top = int(viewport_rect.y())
            bot = top + int(viewport_rect.height())

            if top > self.height():
                break
            if bot >= 0:
                n = block.blockNumber()
                typ = self._line_types.get(n, "normal")
                active = n == self._current_line

                if active:
                    bg = QColor("#fab283")
                    bg.setAlpha(10)
                    painter.fillRect(QRect(0, top, self.width() - 1, bot - top), bg)

                if active:
                    c = QColor("#fab283")
                elif typ == "heading":
                    c = QColor("#9d7cd8")
                elif typ == "code":
                    c = QColor("#7fd88f")
                elif typ == "list":
                    c = QColor("#56b6c2")
                elif typ == "blank":
                    c = QColor("#0a0a0a")
                else:
                    c = QColor("#808080")

                painter.setPen(c)
                painter.setFont(self._font)
                txt = str(n + 1)
                x = self.width() - self._fm.horizontalAdvance(txt) - 10
                y = top + self._fm.ascent() + 2
                painter.drawText(x, y, txt)

            block = block.next()

        painter.end()

    def sizeHint(self):
        return QSize(self.width(), 0)
