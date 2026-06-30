import re

from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QFont, QColor,
)

from zametka_dbs.core.config import get_config


class MarkdownHighlighter(QSyntaxHighlighter):
    """
    QSyntaxHighlighter for Markdown syntax.

    Highlights:
      - Headings h1-h6
      - Bold, italic, strikethrough, highlight
      - Inline code and fenced code blocks (multi-block state)
      - Links, wikilinks, images
      - Lists, blockquotes, horizontal rules
      - Tags (#tag), inline math ($...$)
      - Callouts (> [!type])

    Uses QSyntaxHighlighter's built-in block state for multi-line
    code fences and blockquotes.
    """

    # Block states
    NORMAL = 0
    CODE_FENCE = 1
    CODE_INDENTED = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        config = get_config()
        size = config.get("editor.font_size", 14)

        # Define formats once
        self._formats = self._build_formats(size)
        # Compile regex rules
        self._rules = self._build_rules()

    def _build_formats(self, size: int) -> dict:
        base_size = size
        h_sizes = {
            1: base_size + 4,
            2: base_size + 2,
            3: base_size,
        }

        def fmt(color, bold=False, italic=False, size_off=0, bg=None):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Weight.Bold)
            if italic:
                f.setFontItalic(True)
            if size_off:
                f.setFontPointSize(base_size + size_off)
            if bg:
                f.setBackground(QColor(bg))
            return f

        return {
            "h1": fmt("#9d7cd8", bold=True, size_off=4),
            "h2": fmt("#9d7cd8", bold=True, size_off=2),
            "h3": fmt("#9d7cd8", bold=True),
            "h4": fmt("#e5c07b", bold=True),
            "h5": fmt("#808080", bold=True),
            "h6": fmt("#808080", bold=True),
            "bold": fmt("#f5a742", bold=True),
            "italic": fmt("#e5c07b", italic=True),
            "bold_italic": fmt("#f5a742", bold=True, italic=True),
            "code": fmt("#7fd88f", bg="rgba(127, 216, 143, 0.08)"),
            "code_fence": fmt("#7fd88f", bg="rgba(127, 216, 143, 0.04)"),
            "link": fmt("#fab283"),
            "wikilink": fmt("#fab283", bg="rgba(250, 178, 131, 0.08)"),
            "image": fmt("#56b6c2"),
            "list": fmt("#fab283"),
            "blockquote": fmt("#808080"),
            "tag": fmt("#7fd88f", bg="rgba(127, 216, 143, 0.10)"),
            "strikethrough": fmt("#808080"),
            "highlight": fmt("#eeeeee", bg="rgba(245, 167, 66, 0.20)"),
            "math": fmt("#56b6c2"),
            "hr": fmt("#2a2a2a"),
            "callout": fmt("#fab283", bg="rgba(250, 178, 131, 0.04)"),
        }

    def _build_rules(self) -> list:
        return [
            # ── Headings (must be at start of line) ──
            (re.compile(r"^#{6}\s+.*$"), "h6"),
            (re.compile(r"^#{5}\s+.*$"), "h5"),
            (re.compile(r"^#{4}\s+.*$"), "h4"),
            (re.compile(r"^#{3}\s+.*$"), "h3"),
            (re.compile(r"^#{2}\s+.*$"), "h2"),
            (re.compile(r"^#{1}\s+.*$"), "h1"),

            # ── Callouts > [!type] ──
            (re.compile(r"^>\s*\[!.+\].*$"), "callout"),

            # ── Blockquotes ──
            (re.compile(r"^>.*$"), "blockquote"),

            # ── Horizontal rules ──
            (re.compile(r"^[-*_]{3,}\s*$"), "hr"),

            # ── List markers ──
            (re.compile(r"^(\s*[-*+]\s|^\s*\d+\.\s)"), "list"),

            # ── Inline math ──
            (re.compile(r"\$[^$]+\$"), "math"),

            # ── Wikilinks [[...]] ──
            (re.compile(r"\[\[.+?\]\]"), "wikilink"),

            # ── Images ![alt](url) ──
            (re.compile(r"!\[.*?\]\(.*?\)"), "image"),

            # ── Links [text](url) ──
            (re.compile(r"\[.*?\]\(.*?\)"), "link"),

            # ── Strikethrough ~~text~~ ──
            (re.compile(r"~~.+?~~"), "strikethrough"),

            # ── Highlight ==text== ──
            (re.compile(r"==.+?=="), "highlight"),

            # ── Bold+Italic ***text*** ──
            (re.compile(r"\*\*\*.+?\*\*\*"), "bold_italic"),

            # ── Bold **text** or __text__ ──
            (re.compile(r"\*\*.+?\*\*"), "bold"),
            (re.compile(r"__(.+?)__"), "bold"),

            # ── Italic *text* or _text_ ──
            (re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)"), "italic"),
            (re.compile(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)"), "italic"),

            # ── Inline code `text` ──
            (re.compile(r"`[^`]+?`"), "code"),

            # ── Tags #tag (word boundary) ──
            (re.compile(r"#[\w\-/]+"), "tag"),
        ]

    def highlightBlock(self, text: str):
        block_state = self.previousBlockState()

        # ── Handle fenced code blocks ──
        if block_state == self.CODE_FENCE:
            # Check if this block ends the fence
            if text.strip().startswith("```"):
                self.setCurrentBlockState(self.NORMAL)
                self._apply_format(0, len(text), "code_fence")
                return
            self.setCurrentBlockState(self.CODE_FENCE)
            self._apply_format(0, len(text), "code_fence")
            return
        else:
            if text.strip().startswith("```"):
                # Check if it closes on same line
                stripped = text.strip()
                if stripped.count("```") == 2 and len(stripped) > 3:
                    self.setCurrentBlockState(self.NORMAL)
                else:
                    self.setCurrentBlockState(self.CODE_FENCE)
                self._apply_format(0, len(text), "code_fence")
                return

        self.setCurrentBlockState(self.NORMAL)

        # ── Apply inline rules ──
        for pattern, fmt_key in self._rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self._apply_format(start, length, fmt_key, text)

    def _apply_format(self, start: int, length: int, fmt_key: str, text: str = ""):
        fmt = self._formats.get(fmt_key)
        if fmt is None:
            return
        self.setFormat(start, length, fmt)
