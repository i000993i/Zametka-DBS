from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit
from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import (
    QTextCursor, QColor, QFont, QFontMetrics,
)

from zametka_dbs.ui.line_gutter import LineGutter
from zametka_dbs.ui.syntax_highlighter import MarkdownHighlighter
from zametka_dbs.ui.language_highlighters import get_highlighter_for_file
from zametka_dbs.core.config import get_config
from zametka_dbs.core.event_bus import get_bus, Events


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bus = get_bus()
        config = get_config()

        family = config.get("editor.font_family", "Consolas")
        size = config.get("editor.font_size", 14)
        mono = QFont(family, size)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(mono)

        self._line_height = QFontMetrics(mono).height()
        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance(" ") * config.get("editor.tab_size", 4)
        )

        if config.get("editor.word_wrap", True):
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.setStyleSheet(self._stylesheet())
        self.document().setDocumentMargin(8)

        self._gutter = LineGutter(self)
        self._gutter.set_editor(self)
        self.setViewportMargins(self._gutter.width(), 0, 0, 0)

        self._highlighter = MarkdownHighlighter(self.document())

        self.cursorPositionChanged.connect(self._on_cursor_moved)
        self.textChanged.connect(self._on_text_changed)

        self._highlight_active_line()

    def _stylesheet(self):
        return """
            QPlainTextEdit {
                background-color: #0a0a0a;
                color: #eeeeee;
                border: none;
                selection-background-color: #333333;
                selection-color: #eeeeee;
            }
        """

    def _on_cursor_moved(self):
        self._highlight_active_line()
        c = self.textCursor()
        self._bus.emit(Events.EDITOR_CURSOR_MOVED,
                       line=c.blockNumber() + 1,
                       column=c.columnNumber() + 1)

    def _on_text_changed(self):
        self._bus.emit(Events.EDITOR_CONTENT_CHANGED)

    def set_language_for_file(self, filepath: str):
        hl = get_highlighter_for_file(self.document(), filepath)
        if hl is not None:
            self._highlighter.setDocument(None)
            self._highlighter.deleteLater()
            self._highlighter = hl
        else:
            if not isinstance(self._highlighter, MarkdownHighlighter):
                self._highlighter.setDocument(None)
                self._highlighter.deleteLater()
                self._highlighter = MarkdownHighlighter(self.document())
        self._highlighter.rehighlight()

    def _highlight_active_line(self):
        if self.isReadOnly():
            return
        sel = QTextEdit.ExtraSelection()
        c = QColor("#fab283")
        c.setAlpha(8)
        sel.format.setBackground(c)
        sel.cursor = self.textCursor()
        sel.cursor.clearSelection()
        self.setExtraSelections([sel])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        vp = self.viewport()
        self._gutter.setGeometry(0, vp.pos().y(), self._gutter.width(), vp.height())

    def get_line_count(self) -> int:
        return self.blockCount()

    def get_current_line(self) -> int:
        return self.textCursor().blockNumber() + 1

    def get_current_column(self) -> int:
        return self.textCursor().columnNumber() + 1

    def set_cursor_position(self, line: int, col: int):
        block = self.document().findBlockByNumber(line - 1)
        if block.isValid():
            cursor = QTextCursor(block)
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, col - 1)
            self.setTextCursor(cursor)

    def word_count(self) -> int:
        return len(self.toPlainText().split())
