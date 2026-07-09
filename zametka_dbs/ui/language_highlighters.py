from __future__ import annotations

import re
import os

from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor

NORMAL: int = 0
IN_BLOCK_COMMENT: int = 1
IN_TRIPLE_STRING: int = 2


def _fmt(color: str, bold: bool = False, italic: bool = False, size_offset: int = 0) -> QTextCharFormat:
    f: QTextCharFormat = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


DARK_STYLES: dict[str, QTextCharFormat] = {
    "keyword": _fmt("#9d7cd8", bold=True),
    "builtin": _fmt("#9d7cd8"),
    "string": _fmt("#7fd88f"),
    "number": _fmt("#79c0ff"),
    "comment": _fmt("#8b949e", italic=True),
    "function": _fmt("#d2a8ff"),
    "class": _fmt("#ffa657"),
    "decorator": _fmt("#ffa657"),
    "operator": _fmt("#ff7b72"),
    "type": _fmt("#ffa657"),
    "variable": _fmt("#ffa657"),
    "constant": _fmt("#79c0ff"),
    "parameter": _fmt("#ffa657"),
    "preprocessor": _fmt("#8b949e"),
}

LIGHT_STYLES: dict[str, QTextCharFormat] = {
    "keyword": _fmt("#8250df", bold=True),
    "builtin": _fmt("#8250df"),
    "string": _fmt("#1a7f37"),
    "number": _fmt("#0550ae"),
    "comment": _fmt("#6e7781", italic=True),
    "function": _fmt("#8250df"),
    "class": _fmt("#953800"),
    "decorator": _fmt("#953800"),
    "operator": _fmt("#cf222e"),
    "type": _fmt("#953800"),
    "variable": _fmt("#953800"),
    "constant": _fmt("#0550ae"),
    "parameter": _fmt("#953800"),
    "preprocessor": _fmt("#6e7781"),
}


class LanguageHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: object | None, lang: str, config: dict | None = None) -> None:
        super().__init__(parent)
        self._dark: bool = True
        self._lang: str = lang
        self._rules: list[tuple[re.Pattern, str]] = []
        self._block_comment: tuple[str, str] | None = None
        self._triple_strings: bool = False
        self._single_comment: str | None = None

        self._styles = DARK_STYLES
        self._compile_rules()

    def _compile_rules(self) -> None:
        rules: list[tuple[re.Pattern, str]] = []
        info: dict = EXTENSION_MAP.get(self._lang, {})
        for kw in info.get("keywords", []):
            rules.append((re.compile(r"\b" + kw + r"\b"), "keyword"))
        for b in info.get("builtins", []):
            rules.append((re.compile(r"\b" + b + r"\b"), "builtin"))
        for t in info.get("types", []):
            rules.append((re.compile(r"\b" + t + r"\b"), "type"))
        self._single_comment = info.get("single_comment")
        self._block_comment = info.get("block_comment")
        self._triple_strings = info.get("triple_strings", False)
        self._rules = rules

    def set_theme(self, dark: bool) -> None:
        self._dark = dark
        self._styles = DARK_STYLES if dark else LIGHT_STYLES
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        if not text:
            return
        state: int = self.previousBlockState()
        if state == IN_BLOCK_COMMENT and self._block_comment:
            end_idx: int = text.find(self._block_comment[1])
            if end_idx >= 0:
                self.setFormat(0, end_idx + len(self._block_comment[1]), self._styles["comment"])
                self.setCurrentBlockState(NORMAL)
                remaining: str = text[end_idx + len(self._block_comment[1]):]
                if remaining:
                    self._apply_rules(remaining, end_idx + len(self._block_comment[1]))
            else:
                self.setFormat(0, len(text), self._styles["comment"])
                self.setCurrentBlockState(IN_BLOCK_COMMENT)
            return

        if self._triple_strings and state == IN_TRIPLE_STRING:
            end_idx = text.find('"""')
            if end_idx >= 0:
                self.setFormat(0, end_idx + 3, self._styles["string"])
                self.setCurrentBlockState(NORMAL)
                remaining = text[end_idx + 3:]
                if remaining:
                    self._apply_rules(remaining, end_idx + 3)
            else:
                self.setFormat(0, len(text), self._styles["string"])
                self.setCurrentBlockState(IN_TRIPLE_STRING)
            return

        self._apply_rules(text, 0)

    def _highlight_strings(self, text: str, offset: int) -> None:
        for m in re.finditer(r'"[^"\\]*(?:\\.[^"\\]*)*"', text):
            self.setFormat(offset + m.start(), m.end() - m.start(), self._styles["string"])
        for m in re.finditer(r"'[^'\\]*(?:\\.[^'\\]*)*'", text):
            self.setFormat(offset + m.start(), m.end() - m.start(), self._styles["string"])
        if self._triple_strings:
            for m in re.finditer(r'"""', text):
                idx: int = m.start()
                self.setFormat(offset + idx, 3, self._styles["string"])
                after: str = text[idx + 3:]
                end: int = after.find('"""')
                if end >= 0:
                    self.setFormat(offset + idx + 3, end + 3, self._styles["string"])
                else:
                    self.setCurrentBlockState(IN_TRIPLE_STRING)
                    self.setFormat(offset + idx + 3, len(after), self._styles["string"])

    def _apply_rules(self, text: str, offset: int) -> None:
        if self._single_comment:
            idx: int = text.find(self._single_comment)
            if idx >= 0:
                self.setFormat(offset + idx, len(text) - idx, self._styles["comment"])
                text = text[:idx]

        if self._block_comment:
            start: int = text.find(self._block_comment[0])
            if start >= 0:
                end: int = text.find(self._block_comment[1], start + len(self._block_comment[0]))
                if end >= 0:
                    self.setFormat(offset + start, end + len(self._block_comment[1]) - start,
                                   self._styles["comment"])
                else:
                    self.setFormat(offset + start, len(text) - start, self._styles["comment"])
                    self.setCurrentBlockState(IN_BLOCK_COMMENT)
                    text = text[:start]

        self._highlight_strings(text, offset)

        for pattern, key in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(offset + match.start(), match.end() - match.start(),
                               self._styles.get(key, self._styles["keyword"]))


_PYTHON_KEYWORDS: list[str] = [
    "and", "as", "assert", "async", "await", "break", "class", "continue",
    "def", "del", "elif", "else", "except", "finally", "for", "from",
    "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
    "or", "pass", "raise", "return", "try", "while", "with", "yield",
    "False", "None", "True",
]

_PYTHON_BUILTINS: list[str] = [
    "print", "len", "range", "int", "str", "float", "list", "dict",
    "set", "tuple", "bool", "type", "super", "open", "isinstance",
    "hasattr", "getattr", "setattr", "enumerate", "zip", "map",
    "filter", "sorted", "reversed", "any", "all", "sum", "min", "max",
    "abs", "round", "repr", "property", "classmethod", "staticmethod",
    "self",
]

_JS_KEYWORDS: list[str] = [
    "const", "let", "var", "function", "class", "return", "if", "else",
    "for", "while", "do", "switch", "case", "break", "continue",
    "new", "this", "typeof", "instanceof", "try", "catch", "finally",
    "throw", "import", "export", "default", "from", "async", "await",
    "yield", "in", "of", "null", "undefined", "true", "false",
]

_TS_KEYWORDS: list[str] = _JS_KEYWORDS + [
    "interface", "type", "enum", "implements", "extends", "abstract",
    "private", "protected", "public", "readonly", "static", "as",
    "any", "void", "never", "unknown", "string", "number", "boolean",
]

_CPP_KEYWORDS: list[str] = [
    "int", "float", "double", "char", "void", "bool", "auto", "const",
    "static", "class", "struct", "enum", "union", "namespace", "using",
    "template", "typename", "virtual", "override", "public", "private",
    "protected", "if", "else", "for", "while", "do", "switch", "case",
    "break", "continue", "return", "new", "delete", "try", "catch",
    "throw", "include", "define", "pragma", "true", "false", "nullptr",
]

_RUST_KEYWORDS: list[str] = [
    "let", "mut", "fn", "impl", "struct", "enum", "trait", "pub",
    "use", "mod", "crate", "self", "super", "where", "as", "in",
    "for", "while", "loop", "if", "else", "match", "return",
    "break", "continue", "true", "false", "Some", "None",
    "Ok", "Err", "async", "await", "move", "ref", "unsafe",
    "dyn", "type", "const", "static", "extern",
]

_GO_KEYWORDS: list[str] = [
    "func", "var", "const", "type", "struct", "interface", "map",
    "chan", "go", "defer", "select", "range", "return", "if",
    "else", "for", "switch", "case", "break", "continue", "fallthrough",
    "default", "package", "import", "nil", "true", "false",
    "int", "string", "bool", "float64", "error", "byte", "rune",
    "uintptr",
]

_JAVA_KEYWORDS: list[str] = [
    "public", "private", "protected", "static", "final", "class",
    "interface", "enum", "extends", "implements", "abstract",
    "synchronized", "volatile", "transient", "native", "strictfp",
    "if", "else", "for", "while", "do", "switch", "case", "break",
    "continue", "return", "new", "this", "super", "try", "catch",
    "finally", "throw", "throws", "import", "package", "true",
    "false", "null", "int", "float", "double", "long", "short",
    "byte", "char", "boolean", "void", "String",
]

_CSHARP_KEYWORDS: list[str] = [
    "public", "private", "protected", "internal", "static", "readonly",
    "virtual", "override", "abstract", "sealed", "async", "await",
    "class", "struct", "interface", "enum", "record", "namespace",
    "using", "if", "else", "for", "foreach", "while", "do", "switch",
    "case", "break", "continue", "return", "new", "this", "base",
    "try", "catch", "finally", "throw", "var", "int", "string",
    "bool", "float", "double", "char", "byte", "object", "void",
    "null", "true", "false", "get", "set", "value",
]

_SQL_KEYWORDS: list[str] = [
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE",
    "SET", "DELETE", "CREATE", "TABLE", "DROP", "ALTER", "INDEX",
    "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "ON", "AND", "OR",
    "NOT", "IN", "LIKE", "BETWEEN", "IS", "NULL", "AS", "ORDER",
    "BY", "GROUP", "HAVING", "LIMIT", "OFFSET", "DISTINCT", "COUNT",
    "SUM", "AVG", "MIN", "MAX", "EXISTS", "CASE", "WHEN", "THEN",
    "ELSE", "END", "PRIMARY", "KEY", "FOREIGN", "REFERENCES",
    "AUTO_INCREMENT", "DEFAULT", "CHECK", "UNIQUE", "CASCADE",
]

EXTENSION_MAP: dict[str, dict] = {
    "python": {
        "keywords": _PYTHON_KEYWORDS,
        "builtins": _PYTHON_BUILTINS,
        "single_comment": "#",
        "block_comment": None,
        "triple_strings": True,
        "types": ["list", "dict", "set", "tuple", "int", "str", "float", "bool", "None",
                   "Any", "Optional", "Union", "Callable", "Type", "Iterable"],
    },
    "javascript": {
        "keywords": _JS_KEYWORDS,
        "single_comment": "//",
        "block_comment": ("/*", "*/"),
    },
    "typescript": {
        "keywords": _TS_KEYWORDS,
        "single_comment": "//",
        "block_comment": ("/*", "*/"),
    },
    "cpp": {
        "keywords": _CPP_KEYWORDS,
        "single_comment": "//",
        "block_comment": ("/*", "*/"),
    },
    "rust": {
        "keywords": _RUST_KEYWORDS,
        "single_comment": "//",
        "block_comment": ("/*", "*/"),
    },
    "go": {
        "keywords": _GO_KEYWORDS,
        "single_comment": "//",
        "block_comment": ("/*", "*/"),
    },
    "java": {
        "keywords": _JAVA_KEYWORDS,
        "single_comment": "//",
        "block_comment": ("/*", "*/"),
    },
    "csharp": {
        "keywords": _CSHARP_KEYWORDS,
        "single_comment": "//",
        "block_comment": ("/*", "*/"),
    },
    "sql": {
        "keywords": _SQL_KEYWORDS,
        "single_comment": "--",
        "block_comment": ("/*", "*/"),
    },
}


def get_highlighter_for_file(parent: object, filepath: str) -> LanguageHighlighter | None:
    ext: str = os.path.splitext(filepath)[1].lower()
    lang_map: dict[str, str] = {
        ".py": "python", ".pyw": "python",
        ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
        ".ts": "typescript", ".tsx": "typescript",
        ".c": "cpp", ".cpp": "cpp", ".h": "cpp", ".hpp": "cpp",
        ".rs": "rust",
        ".go": "go",
        ".java": "java", ".cls": "java",
        ".cs": "csharp",
        ".sql": "sql",
    }
    lang: str | None = lang_map.get(ext)
    if lang is None:
        return None
    return LanguageHighlighter(parent, lang)
