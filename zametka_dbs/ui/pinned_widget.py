import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMenu, QFileDialog
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, pyqtSignal, QSize

from assets.icons import icon
from zametka_dbs.core.config import get_config

try:
    from zametka_core import detect_language as _rust_detect, scan_folder_languages as _rust_scan
    HAS_RUST_LANG = True
except ImportError:
    HAS_RUST_LANG = False

LANGUAGE_INFO = {
    ".py": ("Python", "#9d7cd8"),
    ".pyw": ("Python", "#9d7cd8"),
    ".js": ("JavaScript", "#f0db4f"),
    ".mjs": ("JavaScript", "#f0db4f"),
    ".cjs": ("JavaScript", "#f0db4f"),
    ".jsx": ("JavaScript", "#f0db4f"),
    ".ts": ("TypeScript", "#3178c6"),
    ".tsx": ("TypeScript", "#3178c6"),
    ".html": ("HTML", "#e34f26"),
    ".htm": ("HTML", "#e34f26"),
    ".css": ("CSS", "#1572b6"),
    ".scss": ("CSS", "#1572b6"),
    ".sass": ("CSS", "#1572b6"),
    ".less": ("CSS", "#1572b6"),
    ".java": ("Java", "#b07219"),
    ".c": ("C", "#555555"),
    ".cpp": ("C++", "#f34b7d"),
    ".h": ("C", "#555555"),
    ".hpp": ("C++", "#f34b7d"),
    ".cc": ("C++", "#f34b7d"),
    ".cxx": ("C++", "#f34b7d"),
    ".cs": ("C#", "#178600"),
    ".go": ("Go", "#00add8"),
    ".rs": ("Rust", "#dea584"),
    ".sql": ("SQL", "#e38c00"),
    ".rb": ("Ruby", "#701516"),
    ".php": ("PHP", "#4f5d95"),
    ".swift": ("Swift", "#f05138"),
    ".kt": ("Kotlin", "#7f52ff"),
    ".kts": ("Kotlin", "#7f52ff"),
    ".dart": ("Dart", "#00d2b8"),
    ".lua": ("Lua", "#000080"),
    ".sh": ("Shell", "#4eaa25"),
    ".bash": ("Shell", "#4eaa25"),
    ".zsh": ("Shell", "#4eaa25"),
    ".ps1": ("PowerShell", "#012456"),
    ".psm1": ("PowerShell", "#012456"),
    ".yaml": ("YAML", "#cb171e"),
    ".yml": ("YAML", "#cb171e"),
    ".toml": ("TOML", "#9c4221"),
    ".json": ("JSON", "#292929"),
    ".ini": ("INI", "#808080"),
    ".cfg": ("INI", "#808080"),
    ".conf": ("INI", "#808080"),
    ".md": ("Markdown", "#083fa1"),
    ".txt": ("Text", "#808080"),
}


def _detect_folder_languages(folder_path: str, max_depth: int = 2):
    if HAS_RUST_LANG:
        return _rust_scan(folder_path, max_depth)
    import collections
    ext_counter = collections.Counter()
    base_depth = folder_path.rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(folder_path):
        depth = root.count(os.sep) - base_depth
        if depth > max_depth:
            dirs.clear()
            continue
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in LANGUAGE_INFO:
                ext_counter[ext] += 1
    lang_set = {}
    for ext, _ in ext_counter.most_common():
        name, color = LANGUAGE_INFO[ext]
        if name not in lang_set:
            lang_set[name] = color
        if len(lang_set) >= 5:
            break
    return list(lang_set.items())


class PinnedWidget(QWidget):
    item_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pinned-widget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("pinned-header")
        header.setFixedHeight(24)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 6, 0)
        header_layout.setSpacing(4)

        header_icon = QLabel()
        header_icon.setPixmap(icon("link").pixmap(12, 12))
        header_icon.setFixedWidth(16)
        header_layout.addWidget(header_icon)

        header_label = QLabel("PINNED")
        header_label.setObjectName("pinned-label")
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        self._pin_btn = QPushButton()
        self._pin_btn.setIcon(icon("circle"))
        self._pin_btn.setIconSize(QSize(12, 12))
        self._pin_btn.setObjectName("pinned-add-btn")
        self._pin_btn.setFixedSize(18, 18)
        self._pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pin_btn.setToolTip("Pin a file or folder")
        self._pin_btn.clicked.connect(self._show_pin_menu)
        header_layout.addWidget(self._pin_btn)

        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setObjectName("pinned-list")
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

        self.setStyleSheet(self._styles())
        self._load_pins()

    def _show_pin_menu(self):
        menu = QMenu(self)

        act_file = QAction("Pin file...", self)
        act_file.triggered.connect(self._pin_file_dialog)
        menu.addAction(act_file)

        act_folder = QAction("Pin folder...", self)
        act_folder.triggered.connect(self._pin_folder_dialog)
        menu.addAction(act_folder)

        menu.exec(self._pin_btn.mapToGlobal(self._pin_btn.rect().bottomLeft()))

    def _pin_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pin file", "",
            "All Files (*.*)"
        )
        if path:
            self._add_pin(path)

    def _pin_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Pin folder", "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self._add_pin(folder)

    def _add_pin(self, path: str):
        config = get_config()
        pinned = config.get("pinned.items", [])
        if path not in pinned:
            pinned.append(path)
            config.set("pinned.items", pinned)
        self._load_pins()

    def _remove_pin(self, path: str):
        config = get_config()
        pinned = config.get("pinned.items", [])
        if path in pinned:
            pinned.remove(path)
            config.set("pinned.items", pinned)
        self._load_pins()

    def _load_pins(self):
        self._list.clear()
        config = get_config()
        pinned = config.get("pinned.items", [])
        has_items = False
        for path in pinned:
            if not os.path.exists(path):
                continue
            self._add_item(path)
            has_items = True
        self._list.setVisible(has_items)

    def _add_item(self, path: str):
        name = os.path.basename(path) or path
        is_dir = os.path.isdir(path)

        badges = []
        if is_dir:
            langs = _detect_folder_languages(path)
            for lang_name, color in langs:
                badges.append((lang_name, color))
        else:
            if HAS_RUST_LANG:
                result = _rust_detect(path)
                if result:
                    badges.append(result)
            else:
                ext = os.path.splitext(path)[1].lower()
                info = LANGUAGE_INFO.get(ext)
                if info:
                    badges.append(info)

        widget = QWidget()
        widget.setObjectName("pinned-item")
        row = QHBoxLayout(widget)
        row.setContentsMargins(8, 2, 8, 2)
        row.setSpacing(6)

        ico_label = QLabel()
        if is_dir:
            ico_label.setPixmap(icon("folder").pixmap(14, 14))
        else:
            ico_label.setPixmap(icon("file").pixmap(14, 14))
        ico_label.setFixedWidth(18)
        row.addWidget(ico_label)

        name_label = QLabel(name)
        name_label.setObjectName("pinned-name")
        name_label.setStyleSheet("color: #eeeeee; font-size: 12px;")
        row.addWidget(name_label, 1)

        for lang_name, color in badges:
            badge = QLabel(lang_name)
            badge.setStyleSheet(
                f"background-color: {color}; color: #ffffff; "
                f"font-size: 9px; font-weight: 600; padding: 1px 5px; "
                f"border-radius: 3px;"
            )
            row.addWidget(badge)

        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setSizeHint(widget.sizeHint())
        self._list.addItem(item)
        self._list.setItemWidget(item, widget)

    def _on_item_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.item_clicked.emit(path)

    def _show_context_menu(self, pos):
        item = self._list.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        act_unpin = QAction("Unpin", self)
        act_unpin.triggered.connect(lambda: self._remove_pin(path))
        menu.addAction(act_unpin)

        act_clean = QAction("Remove missing paths", self)
        act_clean.triggered.connect(self._clean_missing)
        menu.addAction(act_clean)

        menu.exec(self._list.viewport().mapToGlobal(pos))

    def _clean_missing(self):
        config = get_config()
        pinned = config.get("pinned.items", [])
        pinned = [p for p in pinned if os.path.exists(p)]
        config.set("pinned.items", pinned)
        self._load_pins()

    def _styles(self) -> str:
        return """
            QWidget#pinned-header {
                border-bottom: 1px solid #1a1a1a;
                background-color: #0a0a0a;
            }
            QLabel#pinned-label {
                color: #808080;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
            }
            QPushButton#pinned-add-btn {
                background-color: transparent;
                color: #808080;
                border: none;
                border-radius: 2px;
                font-size: 11px;
            }
            QPushButton#pinned-add-btn:hover {
                background-color: #1a1a1a;
                color: #eeeeee;
            }
            QWidget#pinned-item {
                background-color: transparent;
            }
            QListWidget#pinned-list {
                background-color: #0a0a0a;
                border: none;
                color: #eeeeee;
                font-size: 12px;
                outline: none;
                max-height: 200px;
            }
            QListWidget#pinned-list::item {
                padding: 0;
                border: none;
            }
            QListWidget#pinned-list::item:hover {
                background-color: #1a1a1a;
            }
            QListWidget#pinned-list::item:selected {
                background-color: #1a1a1a;
            }
            QListWidget#pinned-list QScrollBar:vertical {
                background-color: #0a0a0a;
                width: 6px;
                margin: 0;
            }
            QListWidget#pinned-list QScrollBar::handle:vertical {
                background-color: #1a1a1a;
                min-height: 20px;
                border-radius: 3px;
            }
            QListWidget#pinned-list QScrollBar::handle:vertical:hover {
                background-color: #2a2a2a;
            }
            QListWidget#pinned-list QScrollBar::add-line:vertical,
            QListWidget#pinned-list QScrollBar::sub-line:vertical {
                height: 0;
            }
            QListWidget#pinned-list QScrollBar::add-page:vertical,
            QListWidget#pinned-list QScrollBar::sub-page:vertical {
                background: none;
            }
        """
