from __future__ import annotations

import os

from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QResizeEvent,
    QTextCursor,
    QColor,
    QFont,
    QFontMetrics,
    QSyntaxHighlighter,
)

from zametka_dbs.ui.line_gutter import LineGutter
from zametka_dbs.ui.syntax_highlighter import MarkdownHighlighter
from zametka_dbs.ui.language_highlighters import get_highlighter_for_file
from zametka_dbs.core.config import get_config
from zametka_dbs.core.event_bus import get_bus, Events
from zametka_dbs.ui.styles import _THEME_VARS


class NullHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str) -> None:
        pass

    def set_theme(self, dark: bool) -> None:
        pass


_MD_EXTS: set[str] = {".md", ".mdx", ".markdown"}


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dark: bool = True
        self._bus = get_bus()
        config = get_config()

        self._setup_font(config)
        self._setup_tabs(config)
        self._setup_wrap(config)

        self.document().setDocumentMargin(8)

        self._gutter: LineGutter = LineGutter(self)
        self._gutter.set_editor(self)
        self.setViewportMargins(self._gutter.width(), 0, 0, 0)

        self._highlighter: QSyntaxHighlighter = NullHighlighter(self.document())

        self.cursorPositionChanged.connect(self._on_cursor_moved)
        self.textChanged.connect(self._on_text_changed)

        self._cursor_timer: QTimer = QTimer(self)
        self._cursor_timer.setSingleShot(True)
        self._cursor_timer.timeout.connect(self._do_cursor_moved)

        self._text_timer: QTimer = QTimer(self)
        self._text_timer.setSingleShot(True)
        self._text_timer.timeout.connect(self._do_text_changed)

        self._highlight_active_line()

    def _setup_font(self, config):
        family: str = config.get("editor.font_family", "Consolas")
        size: int = config.get("editor.font_size", 14)
        mono: QFont = QFont(family, size)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(mono)
        self._line_height: int = QFontMetrics(mono).height()

    def _setup_tabs(self, config):
        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance(" ") * config.get("editor.tab_size", 4)
        )

    def _setup_wrap(self, config):
        if config.get("editor.word_wrap", True):
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def _on_cursor_moved(self) -> None:
        self._highlight_active_line()
        self._cursor_timer.start(50)

    def _on_text_changed(self) -> None:
        self._text_timer.start(100)

    def _do_cursor_moved(self) -> None:
        c: QTextCursor = self.textCursor()
        self._bus.emit(Events.EDITOR_CURSOR_MOVED,
                       line=c.blockNumber() + 1,
                       column=c.columnNumber() + 1)

    def _do_text_changed(self) -> None:
        self._bus.emit(Events.EDITOR_CONTENT_CHANGED)

    def set_language_for_file(self, filepath: str) -> None:
        ext: str = os.path.splitext(filepath)[1].lower()
        is_md: bool = ext in _MD_EXTS or filepath.startswith("__handbook_")

        if is_md:
            if not isinstance(self._highlighter, MarkdownHighlighter):
                self._highlighter.setDocument(None)
                self._highlighter.deleteLater()
                self._highlighter = MarkdownHighlighter(self.document())
            self._highlighter.rehighlight()
            return

        hl = get_highlighter_for_file(self.document(), filepath)
        if hl is not None:
            self._highlighter.setDocument(None)
            self._highlighter.deleteLater()
            self._highlighter = hl
            self._highlighter.rehighlight()
            return

        if not isinstance(self._highlighter, NullHighlighter):
            self._highlighter.setDocument(None)
            self._highlighter.deleteLater()
            self._highlighter = NullHighlighter(self.document())

    def _highlight_active_line(self) -> None:
        if self.isReadOnly():
            return
        selections: list[QTextEdit.ExtraSelection] = [
            s for s in self.extraSelections() if s.format.property(256) is None
        ]
        sel: QTextEdit.ExtraSelection = QTextEdit.ExtraSelection()
        c: QColor = QColor(_THEME_VARS["dark" if self._dark else "light"]["fg1"])
        c.setAlpha(8)
        sel.format.setBackground(c)
        sel.format.setProperty(256, True)
        sel.cursor = self.textCursor()
        sel.cursor.clearSelection()
        selections.append(sel)
        self.setExtraSelections(selections)

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        vp = self.viewport()
        self._gutter.setGeometry(0, vp.pos().y(), self._gutter.width(), vp.height())

    def get_current_line(self) -> int:
        return self.textCursor().blockNumber() + 1

    def get_current_column(self) -> int:
        return self.textCursor().columnNumber() + 1

    def set_cursor_position(self, line: int, col: int) -> None:
        block = self.document().findBlockByNumber(line - 1)
        if block.isValid():
            cursor: QTextCursor = QTextCursor(block)
            cursor.movePosition(
                QTextCursor.MoveOperation.Right,
                QTextCursor.MoveMode.MoveAnchor,
                col - 1,
            )
            self.setTextCursor(cursor)

    def update_theme(self, dark: bool) -> None:
        self._gutter.set_dark(dark)
        self._highlighter.set_theme(dark)

    def word_count(self) -> int:
        return len(self.toPlainText().split())
