import re
import os

from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor

NORMAL = 0
IN_BLOCK_COMMENT = 1
IN_TRIPLE_STRING = 2


def _fmt(color, bold=False, italic=False, bg=None):
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    if bg:
        c = QColor(bg)
        c.setAlpha(20)
        f.setBackground(c)
    return f


STYLES = {
    "keyword":   _fmt("#9d7cd8", bold=True),
    "keyword2":  _fmt("#9d7cd8"),
    "string":    _fmt("#7fd88f"),
    "comment":   _fmt("#808080", italic=True),
    "number":    _fmt("#fab283"),
    "function":  _fmt("#fab283"),
    "type":      _fmt("#e5c07b"),
    "builtin":   _fmt("#56b6c2"),
    "decorator": _fmt("#e5c07b"),
    "operator":  _fmt("#56b6c2"),
    "property":  _fmt("#56b6c2"),
    "punctuation": _fmt("#808080"),
    "variable":  _fmt("#e06c75"),
    "attribute": _fmt("#56b6c2"),
    "constant":  _fmt("#f5a742"),
    "tag":       _fmt("#9d7cd8"),
    "params":    _fmt("#e5c07b"),
}


class LanguageHighlighter(QSyntaxHighlighter):
    def __init__(self, parent, lang_def):
        super().__init__(parent)
        self._lang = lang_def
        self._rules = self._compile_rules()
        self._block_comment = lang_def.get("block_comment")
        self._triple_strings = lang_def.get("triple_strings", [])
        self._single_comment = lang_def.get("single_comment")

    def _compile_rules(self):
        rules = []

        for word in self._lang.get("keywords", []):
            rules.append((re.compile(r"\b" + re.escape(word) + r"\b"), "keyword"))

        for word in self._lang.get("keywords2", []):
            rules.append((re.compile(r"\b" + re.escape(word) + r"\b"), "keyword2"))

        for word in self._lang.get("types", []):
            rules.append((re.compile(r"\b" + re.escape(word) + r"\b"), "type"))

        for word in self._lang.get("builtins", []):
            rules.append((re.compile(r"\b" + re.escape(word) + r"\b"), "builtin"))

        for word in self._lang.get("constants", []):
            rules.append((re.compile(r"\b" + re.escape(word) + r"\b"), "constant"))

        for word in self._lang.get("decorators", []):
            rules.append((re.compile(r"@" + re.escape(word) + r"\b"), "decorator"))

        for pat in self._lang.get("extra_patterns", []):
            rules.append((re.compile(pat[0]), pat[1]))

        # Number literals
        rules.append((re.compile(r"\b(0x[0-9a-fA-F]+|0o[0-7]+|0b[01]+|\d+\.?\d*[fFlL]?)\b"), "number"))

        return rules

    def highlightBlock(self, text):
        state = self.previousBlockState()
        if state < 0:
            state = NORMAL

        # ── Handle multi-line constructs ──
        if state == IN_BLOCK_COMMENT and self._block_comment:
            end_idx = text.find(self._block_comment[1])
            if end_idx >= 0:
                self.setFormat(0, end_idx + len(self._block_comment[1]), STYLES["comment"])
                self.setCurrentBlockState(NORMAL)
                remaining = text[end_idx + len(self._block_comment[1]):]
                self._apply_rules(remaining, end_idx + len(self._block_comment[1]))
            else:
                self.setFormat(0, len(text), STYLES["comment"])
                self.setCurrentBlockState(IN_BLOCK_COMMENT)
            return

        if state == IN_TRIPLE_STRING and self._triple_strings:
            for delim in self._triple_strings:
                idx = text.find(delim)
                if idx >= 0:
                    self.setFormat(0, idx + len(delim), STYLES["string"])
                    self.setCurrentBlockState(NORMAL)
                    remaining = text[idx + len(delim):]
                    self._apply_rules(remaining, idx + len(delim))
                    return
            self.setFormat(0, len(text), STYLES["string"])
            self.setCurrentBlockState(IN_TRIPLE_STRING)
            return

        self.setCurrentBlockState(NORMAL)

        # ── Single-line comment ──
        if self._single_comment:
            idx = text.find(self._single_comment)
            if idx >= 0 and not self._in_string(text, idx):
                self.setFormat(idx, len(text) - idx, STYLES["comment"])
                text = text[:idx]

        # ── Block comment start ──
        if self._block_comment:
            bcs, bce = self._block_comment
            start_idx = text.find(bcs)
            if start_idx >= 0:
                end_idx = text.find(bce, start_idx + len(bcs))
                if end_idx >= 0:
                    self.setFormat(start_idx, end_idx + len(bce) - start_idx, STYLES["comment"])
                    before = text[:start_idx]
                    after = text[end_idx + len(bce):]
                    self._apply_rules(before, 0)
                    self._apply_rules(after, end_idx + len(bce))
                else:
                    self.setFormat(start_idx, len(text) - start_idx, STYLES["comment"])
                    self.setCurrentBlockState(IN_BLOCK_COMMENT)
                return

        # ── Strings ──
        for delim in self._lang.get("strings", []):
            self._highlight_strings(text, delim)

        # ── Triple strings ──
        for delim in self._triple_strings:
            idx = text.find(delim)
            if idx >= 0:
                end_idx = text.find(delim, idx + len(delim))
                if end_idx >= 0:
                    self.setFormat(idx, end_idx + len(delim) - idx, STYLES["string"])
                    self._apply_rules(text[:idx], 0)
                    self._apply_rules(text[end_idx + len(delim):], end_idx + len(delim))
                else:
                    self.setFormat(idx, len(text) - idx, STYLES["string"])
                    self.setCurrentBlockState(IN_TRIPLE_STRING)
                return

        # ── Apply keyword/pattern rules ──
        self._apply_rules(text, 0)

    def _highlight_strings(self, text, delim):
        pattern = re.compile(rf'(?<!\\){re.escape(delim)}[^{delim}\n]*(?<!\\){re.escape(delim)}')
        for m in pattern.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), STYLES["string"])

    def _in_string(self, text, pos):
        for delim in self._lang.get("strings", []):
            pat = re.compile(rf'(?<!\\){re.escape(delim)}')
            count = 0
            for m in pat.finditer(text[:pos]):
                count += 1
            if count % 2 == 1:
                return True
        return False

    def _apply_rules(self, text, offset):
        for pattern, style_key in self._rules:
            for m in pattern.finditer(text):
                start = offset + m.start()
                end = offset + m.end()
                # Don't overwrite already formatted regions (comments/strings)
                if self.format(start) == STYLES["comment"] or self.format(start) == STYLES["string"]:
                    continue
                self.setFormat(start, end - start, STYLES[style_key])


# ── Language definitions ──

PYTHON = {
    "keywords": [
        "False", "None", "True", "and", "as", "assert", "async", "await",
        "break", "class", "continue", "def", "del", "elif", "else", "except",
        "finally", "for", "from", "global", "if", "import", "in", "is",
        "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
        "try", "while", "with", "yield",
    ],
    "builtins": [
        "abs", "all", "any", "bin", "bool", "bytearray", "bytes", "chr",
        "complex", "dict", "dir", "divmod", "enumerate", "eval", "exec",
        "filter", "float", "format", "frozenset", "getattr", "globals",
        "hasattr", "hash", "hex", "id", "input", "int", "isinstance",
        "issubclass", "iter", "len", "list", "locals", "map", "max",
        "min", "next", "object", "oct", "open", "ord", "pow", "print",
        "property", "range", "repr", "reversed", "round", "set", "setattr",
        "slice", "sorted", "staticmethod", "str", "sum", "super", "tuple",
        "type", "vars", "zip", "__import__",
    ],
    "types": ["int", "float", "str", "list", "dict", "tuple", "set", "frozenset", "bool", "bytes", "bytearray", "NoneType"],
    "constants": ["True", "False", "None", "Ellipsis", "NotImplemented"],
    "decorators": ["staticmethod", "classmethod", "property", "abstractmethod"],
    "single_comment": "#",
    "block_comment": None,
    "strings": ['"', "'"],
    "triple_strings": ['"""', "'''"],
    "extra_patterns": [
        (r"@\w+", "decorator"),
        (r"\bself\b", "variable"),
        (r"\bcls\b", "variable"),
    ],
}

JAVASCRIPT = {
    "keywords": [
        "async", "await", "break", "case", "catch", "class", "const",
        "continue", "debugger", "default", "delete", "do", "else", "export",
        "extends", "finally", "for", "function", "if", "import", "in",
        "instanceof", "let", "new", "of", "return", "static", "super",
        "switch", "this", "throw", "try", "typeof", "var", "void",
        "while", "with", "yield",
    ],
    "keywords2": ["from", "as", "get", "set"],
    "builtins": [
        "console", "window", "document", "Math", "JSON", "Array", "Object",
        "String", "Number", "Boolean", "Date", "RegExp", "Map", "Set",
        "Promise", "Symbol", "Error", "parseInt", "parseFloat",
        "isNaN", "isFinite", "fetch", "setTimeout", "setInterval",
        "clearTimeout", "clearInterval",
    ],
    "types": ["undefined", "null", "Infinity", "NaN"],
    "constants": ["true", "false", "null", "undefined", "Infinity", "NaN"],
    "single_comment": "//",
    "block_comment": ("/*", "*/"),
    "strings": ['"', "'", "`"],
    "triple_strings": [],
    "extra_patterns": [
        (r"\b(this|super)\b", "variable"),
        (r"\$\w+", "variable"),
    ],
}

TYPESCRIPT = {**JAVASCRIPT, "keywords": JAVASCRIPT["keywords"] + [
    "type", "interface", "enum", "implements", "abstract", "private",
    "protected", "public", "readonly", "declare", "namespace", "module",
    "keyof", "infer", "satisfies",
]}

HTML = {
    "keywords": [
        "html", "head", "body", "div", "span", "p", "a", "img", "input",
        "form", "button", "table", "tr", "td", "th", "ul", "ol", "li",
        "h1", "h2", "h3", "h4", "h5", "h6", "header", "footer", "nav",
        "section", "article", "aside", "main", "script", "style", "link",
        "meta", "title", "select", "option", "textarea", "label", "iframe",
    ],
    "strings": ['"', "'"],
    "block_comment": ("<!--", "-->"),
    "single_comment": None,
    "triple_strings": [],
    "builtins": [],
    "types": [],
    "constants": [],
    "extra_patterns": [
        (r"</?[\w-]+", "tag"),
        (r"\b(id|class|style|src|href|rel|type|name|value|placeholder|disabled|checked|selected|data-\w+)\s*=", "attribute"),
    ],
}

CSS = {
    "keywords": [],
    "strings": ['"', "'"],
    "single_comment": None,
    "block_comment": ("/*", "*/"),
    "triple_strings": [],
    "builtins": [],
    "types": [],
    "constants": [],
    "extra_patterns": [
        (r"\.[\w-]+", "property"),
        (r"#[\w-]+", "constant"),
        (r"@[\w-]+", "decorator"),
        (r"(margin|padding|color|background|font|border|display|width|height|flex|grid|position|top|left|right|bottom|text|align|justify|overflow|z-index|opacity|transform|transition|animation|box-shadow|cursor|list-style|text-decoration|white-space|word-break|gap)\b", "property"),
        (r"(rgb|rgba|hsl|hsla|url|calc|min|max|clamp)\(", "function"),
        (r"(\d+)(px|em|rem|vh|vw|%|s|ms)", "number"),
    ],
}

JAVA = {
    "keywords": [
        "abstract", "assert", "boolean", "break", "byte", "case", "catch",
        "char", "class", "continue", "default", "do", "double", "else",
        "enum", "extends", "final", "finally", "float", "for", "if",
        "implements", "import", "instanceof", "int", "interface", "long",
        "native", "new", "package", "private", "protected", "public",
        "return", "short", "static", "strictfp", "super", "switch",
        "synchronized", "this", "throw", "throws", "transient", "try",
        "void", "volatile", "while", "var",
    ],
    "types": [
        "String", "Integer", "Boolean", "Double", "Float", "Long", "Short",
        "Byte", "Character", "Object", "Class", "System", "List", "Map",
        "Set", "ArrayList", "HashMap", "HashSet", "Optional",
        "Exception", "RuntimeException", "Throwable",
    ],
    "builtins": [
        "System.out", "System.in", "System.err",
    ],
    "constants": ["true", "false", "null"],
    "single_comment": "//",
    "block_comment": ("/*", "*/"),
    "strings": ['"', "'"],
    "triple_strings": [],
    "extra_patterns": [
        (r"@\w+", "decorator"),
        (r"\b(this|super)\b", "variable"),
    ],
}

CPP = {
    "keywords": [
        "auto", "break", "case", "catch", "class", "const", "constexpr",
        "continue", "decltype", "default", "delete", "do", "else", "enum",
        "explicit", "export", "extern", "false", "final", "for", "friend",
        "goto", "if", "inline", "mutable", "namespace", "new", "noexcept",
        "nullptr", "operator", "override", "private", "protected", "public",
        "return", "sizeof", "static", "static_cast", "struct", "switch",
        "template", "this", "throw", "true", "try", "typedef", "typeid",
        "typename", "union", "using", "virtual", "void", "volatile",
        "while", "include", "define", "ifdef", "ifndef", "endif", "pragma",
    ],
    "types": [
        "int", "float", "double", "char", "bool", "short", "long",
        "string", "vector", "map", "set", "pair", "shared_ptr",
        "unique_ptr", "weak_ptr", "auto_ptr", "iostream",
        "ostream", "istream", "fstream", "ofstream", "ifstream",
        "stringstream", "size_t", "int32_t", "int64_t",
    ],
    "builtins": ["cout", "cin", "cerr", "endl"],
    "constants": ["true", "false", "nullptr", "NULL"],
    "single_comment": "//",
    "block_comment": ("/*", "*/"),
    "strings": ['"', "'"],
    "triple_strings": [],
    "extra_patterns": [
        (r"\b(this)\b", "variable"),
        (r"#\s*\w+", "decorator"),
    ],
}

CSHARP = {
    "keywords": [
        "abstract", "as", "async", "await", "base", "bool", "break",
        "byte", "case", "catch", "char", "checked", "class", "const",
        "continue", "decimal", "default", "delegate", "do", "double",
        "else", "enum", "event", "explicit", "extern", "false", "finally",
        "fixed", "float", "for", "foreach", "goto", "if", "implicit",
        "in", "int", "interface", "internal", "is", "lock", "long",
        "namespace", "new", "null", "object", "operator", "out",
        "override", "params", "private", "protected", "public",
        "readonly", "ref", "return", "sealed", "short", "sizeof",
        "stackalloc", "static", "string", "struct", "switch", "this",
        "throw", "true", "try", "typeof", "uint", "ulong",
        "unchecked", "unsafe", "ushort", "using", "var", "virtual",
        "void", "volatile", "while",
    ],
    "types": [
        "string", "int", "double", "float", "bool", "char", "byte",
        "long", "short", "decimal", "object", "dynamic",
        "List", "Dictionary", "IEnumerable", "Task", "Action", "Func",
        "Exception", "ArgumentException", "NullReferenceException",
    ],
    "builtins": ["Console", "Math", "Convert", "String", "DateTime"],
    "constants": ["true", "false", "null"],
    "single_comment": "//",
    "block_comment": ("/*", "*/"),
    "strings": ['"', "'"],
    "triple_strings": [],
    "extra_patterns": [
        (r"@\w+", "decorator"),
        (r"\b(this|base|value)\b", "variable"),
    ],
}

GO = {
    "keywords": [
        "break", "case", "chan", "const", "continue", "default", "defer",
        "else", "fallthrough", "for", "func", "go", "goto", "if",
        "import", "interface", "map", "package", "range", "return",
        "select", "struct", "switch", "type", "var",
    ],
    "types": [
        "bool", "byte", "complex64", "complex128", "error", "float32",
        "float64", "int", "int8", "int16", "int32", "int64", "rune",
        "string", "uint", "uint8", "uint16", "uint32", "uint64",
        "uintptr",
    ],
    "builtins": [
        "append", "cap", "close", "copy", "delete", "len", "make",
        "new", "panic", "print", "println", "recover",
        "fmt", "os", "io", "http", "json",
    ],
    "constants": ["true", "false", "nil", "iota"],
    "single_comment": "//",
    "block_comment": ("/*", "*/"),
    "strings": ['"', "'", "`"],
    "triple_strings": [],
    "extra_patterns": [],
}

RUST = {
    "keywords": [
        "as", "async", "await", "break", "const", "continue", "crate",
        "dyn", "else", "enum", "extern", "false", "fn", "for", "if",
        "impl", "in", "let", "loop", "match", "mod", "move", "mut",
        "pub", "ref", "return", "self", "Self", "static", "struct",
        "super", "trait", "true", "type", "unsafe", "use", "where",
        "while", "yield",
    ],
    "types": [
        "i8", "i16", "i32", "i64", "i128", "u8", "u16", "u32", "u64",
        "u128", "f32", "f64", "bool", "char", "str", "String", "Vec",
        "Box", "Option", "Result", "HashMap", "HashSet", "Iterator",
        "impl", "dyn", "usize", "isize",
    ],
    "builtins": [
        "print", "println", "dbg", "eprint", "eprintln", "format",
        "assert", "assert_eq", "assert_ne", "panic",
    ],
    "constants": ["true", "false", "None", "Some", "Ok", "Err"],
    "single_comment": "//",
    "block_comment": ("/*", "*/"),
    "strings": ['"', "'"],
    "triple_strings": [],
    "extra_patterns": [
        (r"#!?\[.*?\]", "decorator"),
        (r"\b(self|Self)\b", "variable"),
    ],
}

SQL = {
    "keywords": [
        "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE",
        "SET", "DELETE", "CREATE", "TABLE", "DROP", "ALTER", "INDEX",
        "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "FULL", "ON", "AND",
        "OR", "NOT", "IN", "IS", "NULL", "AS", "LIKE", "BETWEEN",
        "ORDER", "BY", "GROUP", "HAVING", "LIMIT", "OFFSET", "DISTINCT",
        "COUNT", "SUM", "AVG", "MIN", "MAX", "EXISTS", "UNION", "ALL",
        "CASE", "WHEN", "THEN", "ELSE", "END", "BEGIN", "COMMIT",
        "ROLLBACK", "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "CASCADE",
        "UNIQUE", "CHECK", "DEFAULT", "VIEW", "TRIGGER", "PROCEDURE",
        "FUNCTION", "RETURNS", "DECLARE", "CURSOR", "FETCH", "IF",
        "ELSE", "WHILE", "BREAK", "CONTINUE",
    ],
    "types": [
        "INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT", "VARCHAR",
        "CHAR", "TEXT", "BOOLEAN", "FLOAT", "DOUBLE", "DECIMAL", "DATE",
        "DATETIME", "TIMESTAMP", "BLOB", "ENUM", "JSON", "UUID", "SERIAL",
    ],
    "builtins": [
        "NOW", "CURDATE", "CURTIME", "DATE", "TIME", "YEAR", "MONTH",
        "DAY", "HOUR", "MINUTE", "SECOND", "UPPER", "LOWER", "LENGTH",
        "SUBSTRING", "TRIM", "REPLACE", "CONCAT", "COALESCE", "IFNULL",
        "CAST", "CONVERT",
    ],
    "constants": ["NULL", "TRUE", "FALSE"],
    "single_comment": "--",
    "block_comment": ("/*", "*/"),
    "strings": ["'"],
    "triple_strings": [],
    "extra_patterns": [
        (r"\b\d+\b", "number"),
    ],
}

RUBY = {
    "keywords": [
        "BEGIN", "END", "alias", "and", "begin", "break", "case",
        "class", "def", "defined?", "do", "else", "elsif", "end",
        "ensure", "false", "for", "if", "in", "module", "next", "nil",
        "not", "or", "redo", "rescue", "retry", "return", "self",
        "super", "then", "true", "undef", "unless", "until", "when",
        "while", "yield",
    ],
    "types": [
        "String", "Integer", "Float", "Array", "Hash", "Symbol",
        "Range", "TrueClass", "FalseClass", "NilClass",
    ],
    "builtins": [
        "puts", "print", "gets", "require", "include", "extend",
        "attr_reader", "attr_writer", "attr_accessor",
    ],
    "constants": ["true", "false", "nil"],
    "single_comment": "#",
    "block_comment": ("=begin", "=end"),
    "strings": ['"', "'"],
    "triple_strings": [],
    "extra_patterns": [
        (r"@\w+", "variable"),
        (r"@@\w+", "variable"),
        (r"\$\w+", "builtin"),
        (r":\w+", "property"),
    ],
}

PHP = {
    "keywords": [
        "abstract", "and", "array", "as", "break", "callable", "case",
        "catch", "class", "clone", "const", "continue", "declare",
        "default", "die", "do", "echo", "else", "elseif", "empty",
        "enddeclare", "endfor", "endforeach", "endif", "endswitch",
        "endwhile", "eval", "exit", "extends", "final", "finally",
        "fn", "for", "foreach", "function", "global", "goto", "if",
        "implements", "include", "include_once", "instanceof", "insteadof",
        "interface", "isset", "list", "match", "namespace", "new", "or",
        "print", "private", "protected", "public", "readonly", "require",
        "require_once", "return", "static", "switch", "throw", "trait",
        "try", "unset", "use", "var", "while", "xor", "yield",
    ],
    "types": [
        "int", "float", "bool", "string", "array", "object", "void",
        "mixed", "never", "iterable", "self", "parent",
    ],
    "builtins": [
        "true", "false", "null", "self", "parent",
        "define", "defined", "function_exists", "class_exists",
        "method_exists", "property_exists", "is_array", "is_string",
        "is_int", "is_float", "is_null", "is_object",
        "count", "array_merge", "array_keys", "array_values",
        "strlen", "strpos", "substr", "str_replace", "explode", "implode",
        "preg_match", "preg_replace", "json_encode", "json_decode",
        "file_get_contents", "file_put_contents",
    ],
    "constants": ["true", "false", "null", "__CLASS__", "__FILE__", "__LINE__", "__DIR__", "__FUNCTION__", "__METHOD__", "__NAMESPACE__"],
    "single_comment": "//",
    "block_comment": ("/*", "*/"),
    "strings": ['"', "'"],
    "triple_strings": [],
    "extra_patterns": [
        (r"\$\w+", "variable"),
    ],
}

SWIFT = {
    "keywords": [
        "associatedtype", "async", "await", "break", "case", "catch",
        "class", "continue", "default", "defer", "deinit", "do", "else",
        "enum", "extension", "fallthrough", "false", "fileprivate",
        "for", "func", "guard", "if", "import", "in", "indirect",
        "infix", "init", "inout", "internal", "is", "lazy", "let",
        "macro", "mutating", "nil", "nonmutating", "open", "operator",
        "optional", "override", "package", "postfix", "precedencegroup",
        "prefix", "private", "protocol", "public", "repeat", "required",
        "rethrows", "return", "self", "Self", "some", "static",
        "struct", "subscript", "super", "switch", "throw", "throws",
        "true", "try", "typealias", "var", "where", "while", "any",
    ],
    "types": [
        "Int", "Double", "Float", "Bool", "String", "Character",
        "Array", "Dictionary", "Set", "Optional", "Any", "AnyObject",
        "CGFloat", "CGPoint", "CGSize", "CGRect", "Data", "Date", "URL",
        "Error", "Result", "UUID",
    ],
    "builtins": [
        "print", "debugPrint", "dump", "fatalError", "precondition",
        "preconditionFailure", "assert", "assertionFailure",
    ],
    "constants": ["true", "false", "nil"],
    "single_comment": "//",
    "block_comment": ("/*", "*/"),
    "strings": ['"'],
    "triple_strings": [],
    "extra_patterns": [
        (r"@\w+", "decorator"),
        (r"\b(self|Self|super)\b", "variable"),
        (r"#\w+", "keyword2"),
    ],
}

KOTLIN = {
    "keywords": [
        "abstract", "actual", "annotation", "as", "break", "by",
        "catch", "class", "companion", "const", "continue", "crossinline",
        "data", "delegate", "do", "dynamic", "else", "enum", "expect",
        "external", "false", "field", "file", "final", "finally", "for",
        "fun", "if", "import", "in", "infix", "init", "inline",
        "inner", "interface", "internal", "is", "it", "lateinit",
        "noinline", "null", "object", "open", "operator", "out",
        "override", "package", "private", "protected", "public",
        "reified", "return", "sealed", "super", "suspend", "tailrec",
        "this", "throw", "true", "try", "typealias", "val", "var",
        "vararg", "when", "where", "while",
    ],
    "types": [
        "Int", "Long", "Double", "Float", "Boolean", "Char", "String",
        "Unit", "Nothing", "Any", "Nothing", "List", "MutableList",
        "Set", "MutableSet", "Map", "MutableMap", "Array", "Byte",
        "Short", "UByte", "UShort", "UInt", "ULong",
        "Pair", "Triple", "Result", "Sequence",
    ],
    "builtins": [
        "println", "print", "arrayOf", "listOf", "setOf", "mapOf",
        "mutableListOf", "mutableSetOf", "mutableMapOf",
        "emptyList", "emptySet", "emptyMap",
        "require", "check", "error", "TODO", "with", "apply", "let",
        "run", "also", "takeIf", "takeUnless", "repeat",
    ],
    "constants": ["true", "false", "null"],
    "single_comment": "//",
    "block_comment": ("/*", "*/"),
    "strings": ['"', "'"],
    "triple_strings": [],
    "extra_patterns": [
        (r"@\w+", "decorator"),
        (r"\b(this|super|it)\b", "variable"),
        (r"\$\w+", "variable"),
    ],
}

DART = {
    "keywords": [
        "abstract", "as", "assert", "async", "await", "break", "case",
        "catch", "class", "const", "continue", "covariant", "default",
        "deferred", "do", "dynamic", "else", "enum", "export", "extends",
        "extension", "external", "factory", "false", "final", "finally",
        "for", "function", "get", "hide", "if", "implements", "import",
        "in", "interface", "is", "late", "library", "mixin", "new",
        "null", "on", "operator", "part", "required", "rethrow",
        "return", "set", "show", "static", "super", "switch", "sync",
        "this", "throw", "true", "try", "typedef", "var", "void",
        "while", "with", "yield",
    ],
    "types": [
        "int", "double", "num", "bool", "String", "List", "Set", "Map",
        "Object", "dynamic", "void", "Never", "Null", "Symbol",
        "Rune", "Future", "Stream", "Iterable",
    ],
    "builtins": [
        "print", "identityHashCode", "identical",
    ],
    "constants": ["true", "false", "null"],
    "single_comment": "//",
    "block_comment": ("/*", "*/"),
    "strings": ['"', "'"],
    "triple_strings": [],
    "extra_patterns": [
        (r"@\w+", "decorator"),
        (r"\b(this|super)\b", "variable"),
        (r"\$\w+", "variable"),
    ],
}

LUA = {
    "keywords": [
        "and", "break", "do", "else", "elseif", "end", "false", "for",
        "function", "goto", "if", "in", "local", "nil", "not", "or",
        "repeat", "return", "then", "true", "until", "while",
    ],
    "types": [],
    "builtins": [
        "print", "type", "pairs", "ipairs", "next", "tonumber",
        "tostring", "require", "dofile", "loadfile", "pcall", "xpcall",
        "select", "unpack", "rawget", "rawset", "setmetatable",
        "getmetatable", "rawequal", "error", "assert",
        "string", "table", "math", "io", "os", "coroutine", "utf8",
    ],
    "constants": ["true", "false", "nil"],
    "single_comment": "--",
    "block_comment": ("--[[", "]]"),
    "strings": ['"', "'"],
    "triple_strings": [],
    "extra_patterns": [
        (r"\[\[.*?\]\]", "string"),
    ],
}

SHELL = {
    "keywords": [
        "if", "then", "else", "elif", "fi", "for", "while", "until",
        "do", "done", "case", "esac", "in", "function", "return",
        "break", "continue", "exit", "source", "export", "local",
        "readonly", "shift", "select", "time",
    ],
    "types": [],
    "builtins": [
        "echo", "printf", "read", "cd", "pwd", "ls", "cat", "grep",
        "sed", "awk", "cut", "sort", "uniq", "head", "tail", "wc",
        "find", "xargs", "tee", "tr", "test", "eval", "exec",
        "kill", "sleep", "wait", "type", "which", "command",
    ],
    "constants": ["true", "false", "NULL", "null", "YES", "NO"],
    "single_comment": "#",
    "block_comment": None,
    "strings": ['"', "'"],
    "triple_strings": [],
    "extra_patterns": [
        (r"\$\w+", "variable"),
        (r"\$\{\w+\}", "variable"),
        (r"\$\d", "variable"),
        (r"\$[@*#?\-$!]", "variable"),
        (r"-\w+", "operator"),
    ],
}

POWERSHELL = {
    "keywords": [
        "begin", "break", "catch", "class", "continue", "data",
        "define", "do", "dynamicparam", "else", "elseif", "end",
        "exit", "filter", "finally", "for", "foreach", "from",
        "function", "if", "in", "param", "process", "return",
        "switch", "throw", "trap", "try", "until", "using",
        "var", "while", "workflow",
    ],
    "types": [],
    "builtins": [
        "Write-Host", "Write-Output", "Write-Error", "Write-Warning",
        "Write-Progress", "Read-Host", "Get-ChildItem", "Set-Location",
        "Get-Content", "Set-Content", "Add-Content", "Remove-Item",
        "New-Item", "Copy-Item", "Move-Item", "Rename-Item",
        "Test-Path", "Join-Path", "Split-Path", "Resolve-Path",
        "Select-Object", "Where-Object", "ForEach-Object",
        "Sort-Object", "Group-Object", "Measure-Object",
        "Format-Table", "Format-List", "Format-Wide",
        "Foreach-Object", "New-Object", "Invoke-Expression",
        "Invoke-Command", "Start-Process",
        "Select-String", "Compare-Object",
    ],
    "constants": ["true", "false", "null", "True", "False", "Null", "Enabled", "Disabled"],
    "single_comment": "#",
    "block_comment": ("<#", "#>"),
    "strings": ['"', "'"],
    "triple_strings": [],
    "extra_patterns": [
        (r"\$\w+", "variable"),
        (r"\$\{\w+\}", "variable"),
    ],
}

YAML = {
    "keywords": [],
    "strings": ['"', "'"],
    "single_comment": "#",
    "block_comment": None,
    "triple_strings": [],
    "builtins": [],
    "types": [],
    "constants": ["true", "false", "yes", "no", "on", "off", "null", "~"],
    "extra_patterns": [
        (r"^[\t ]*[\w._-]+(?=:)", "property"),
        (r"^[\t ]*- ", "list"),
        (r"\|\s*$|>\s*$", "operator"),
        (r"![\w/]+", "type"),
    ],
}

TOML = {
    "keywords": [],
    "strings": ['"', "'"],
    "single_comment": "#",
    "block_comment": None,
    "triple_strings": [],
    "builtins": [],
    "types": [],
    "constants": ["true", "false"],
    "extra_patterns": [
        (r"^\[.*?\]", "property"),
        (r"^\[\[.*?\]\]", "property"),
        (r"^[\w._-]+(?=\s*=)", "keyword"),
        (r"\d{4}-\d{2}-\d{2}", "number"),
    ],
}

JSON = {
    "keywords": [],
    "strings": ['"'],
    "single_comment": None,
    "block_comment": None,
    "triple_strings": [],
    "builtins": [],
    "types": [],
    "constants": ["true", "false", "null"],
    "extra_patterns": [
        (r'"[^"]*?"(?=\s*:)', "property"),
    ],
}

INI = {
    "keywords": [],
    "strings": ['"', "'"],
    "single_comment": ";",
    "block_comment": None,
    "triple_strings": [],
    "builtins": [],
    "types": [],
    "constants": ["true", "false", "yes", "no", "on", "off"],
    "extra_patterns": [
        (r"^\[.*?\]", "property"),
        (r"^[\w._-]+(?=\s*=)", "keyword"),
    ],
}

# ── Extension → language map ──

EXTENSION_MAP = {
    ".py": PYTHON,
    ".pyw": PYTHON,
    ".js": JAVASCRIPT,
    ".mjs": JAVASCRIPT,
    ".cjs": JAVASCRIPT,
    ".jsx": JAVASCRIPT,
    ".ts": TYPESCRIPT,
    ".tsx": TYPESCRIPT,
    ".html": HTML,
    ".htm": HTML,
    ".xhtml": HTML,
    ".css": CSS,
    ".scss": CSS,
    ".sass": CSS,
    ".less": CSS,
    ".java": JAVA,
    ".c": CPP,
    ".cpp": CPP,
    ".h": CPP,
    ".hpp": CPP,
    ".cc": CPP,
    ".cxx": CPP,
    ".cs": CSHARP,
    ".go": GO,
    ".rs": RUST,
    ".sql": SQL,
    ".rb": RUBY,
    ".php": PHP,
    ".swift": SWIFT,
    ".kt": KOTLIN,
    ".kts": KOTLIN,
    ".dart": DART,
    ".lua": LUA,
    ".sh": SHELL,
    ".bash": SHELL,
    ".zsh": SHELL,
    ".ps1": POWERSHELL,
    ".psm1": POWERSHELL,
    ".yaml": YAML,
    ".yml": YAML,
    ".toml": TOML,
    ".json": JSON,
    ".ini": INI,
    ".cfg": INI,
    ".conf": INI,
}


def get_highlighter_for_file(parent, filepath: str):
    ext = os.path.splitext(filepath)[1].lower()
    lang_def = EXTENSION_MAP.get(ext)
    if lang_def is None:
        return None
    return LanguageHighlighter(parent, lang_def)
