from __future__ import annotations

import json
import re
from pathlib import Path

from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QFont, QColor,
)

from zametka_dbs.core.config import get_config


_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
with open(_DATA_DIR / "syntax_colors.json", encoding="utf-8") as _f:
    _SYNTAX_COLORS: dict[str, dict[str, str]] = json.load(_f)
_LIGHT_COLORS: dict[str, str] = _SYNTAX_COLORS["light"]
_DARK_COLORS: dict[str, str] = _SYNTAX_COLORS["dark"]


class MarkdownHighlighter(QSyntaxHighlighter):
    NORMAL = 0
    CODE_FENCE = 1

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        config = get_config()
        size: int = config.get("editor.font_size", 14)
        self._size: int = size
        self._dark: bool = True

        self._formats: dict[str, QTextCharFormat] = self._build_formats(size)
        self._rules: list[tuple[re.Pattern, str]] = self._compile_rules()

    def _build_formats(self, size: int) -> dict[str, QTextCharFormat]:
        def fmt(color: str, bold: bool = False, italic: bool = False, mono: bool = False) -> QTextCharFormat:
            f: QTextCharFormat = QTextCharFormat()
            c: QColor = QColor(color)
            f.setForeground(c)
            if bold:
                f.setFontWeight(QFont.Weight.Bold)
            if italic:
                f.setFontItalic(True)
            if mono:
                f.setFontFixedPitch(True)
                f.setFontPointSize(size - 2)
            return f

        colors: dict = _DARK_COLORS if self._dark else _LIGHT_COLORS
        return {k: fmt(v) for k, v in colors.items()}

    def _compile_rules(self) -> list[tuple[re.Pattern, str]]:
        return [
            (re.compile(r"^#{1,6}\s+.*$"), "h1"),
            (re.compile(r"\*\*(.+?)\*\*"), "bold"),
            (re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)"), "italic"),
            (re.compile(r"~~(.+?)~~"), "strikethrough"),
            (re.compile(r"==(.+?)=="), "highlight"),
            (re.compile(r"`([^`]+)`"), "code"),
            (re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), "link"),
            (re.compile(r"!\[([^\]]*)\]\(([^)]+)\)"), "image"),
            (re.compile(r"^(\s*[-*+]\s)"), "list"),
            (re.compile(r"^(\s*>\s)"), "blockquote"),
            (re.compile(r"^(\s*---\s*)$"), "hr"),
            (re.compile(r"(?<!`)#(\w[\w-]*)"), "tag"),
            (re.compile(r"\$\$(.+?)\$\$"), "math"),
            (re.compile(r"\$([^\$]+)\$"), "math"),
            (re.compile(r"\[\[([^\]]+)\]\]"), "wikilink"),
            (re.compile(r"^> \[!(?:\w+)\]"), "callout"),
        ]

    def set_theme(self, dark: bool) -> None:
        self._dark = dark
        self._formats = self._build_formats(self._size)
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        if self._dark is None:
            return
        if self.previousBlockState() == self.CODE_FENCE:
            self._highlight_code_fence(text)
            return

        for pattern, key in self._rules:
            for match in pattern.finditer(text):
                start: int = match.start()
                end: int = match.end()
                fmt: QTextCharFormat = self._formats.get(key, QTextCharFormat())
                self.setFormat(start, end - start, fmt)

        if text.strip().startswith("```"):
            self.setCurrentBlockState(self.CODE_FENCE)
            fmt = self._formats.get("code", QTextCharFormat())
            self.setFormat(0, len(text), fmt)

    def _highlight_code_fence(self, text: str) -> None:
        fmt = self._formats.get("code", QTextCharFormat())
        self.setFormat(0, len(text), fmt)
        if text.strip().startswith("```"):
            self.setCurrentBlockState(self.NORMAL)
