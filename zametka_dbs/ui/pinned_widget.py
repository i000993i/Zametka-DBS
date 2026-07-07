import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMenu, QFileDialog
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, pyqtSignal, QSize

from assets.icons import icon
from zametka_dbs.core.config import get_config

from zametka_dbs.core.rust_bridge import HAS_RUST
from zametka_dbs.core.rust_bridge import rust_detect_language as _rust_detect
from zametka_dbs.core.rust_bridge import rust_scan_folder_languages as _rust_scan

_LANG_MAP = {
    ".py": ("Python", "#9d7cd8"), ".pyw": ("Python", "#9d7cd8"),
    ".js": ("JavaScript", "#f0db4f"), ".mjs": ("JavaScript", "#f0db4f"),
    ".jsx": ("JavaScript", "#f0db4f"), ".ts": ("TypeScript", "#3178c6"),
    ".tsx": ("TypeScript", "#3178c6"), ".html": ("HTML", "#e34f26"),
    ".htm": ("HTML", "#e34f26"), ".css": ("CSS", "#1572b6"),
    ".java": ("Java", "#b07219"), ".c": ("C", "#555555"),
    ".cpp": ("C++", "#f34b7d"), ".h": ("C", "#555555"),
    ".hpp": ("C++", "#f34b7d"), ".cs": ("C#", "#178600"),
    ".go": ("Go", "#00add8"), ".rs": ("Rust", "#dea584"),
    ".sql": ("SQL", "#e38c00"), ".rb": ("Ruby", "#701516"),
    ".php": ("PHP", "#4f5d95"), ".swift": ("Swift", "#f05138"),
    ".kt": ("Kotlin", "#7f52ff"), ".dart": ("Dart", "#00d2b8"),
    ".lua": ("Lua", "#000080"), ".sh": ("Shell", "#4eaa25"),
    ".bash": ("Shell", "#4eaa25"), ".ps1": ("PowerShell", "#012456"),
    ".yaml": ("YAML", "#cb171e"), ".yml": ("YAML", "#cb171e"),
    ".toml": ("TOML", "#9c4221"), ".json": ("JSON", "#292929"),
    ".md": ("Markdown", "#083fa1"), ".txt": ("Text", "#808080"),
}


def _detect_language_py(filepath: str):
    import os
    _, ext = os.path.splitext(filepath)
    return _LANG_MAP.get(ext.lower())


def _scan_folder_languages_py(folder_path: str, max_depth: int = 2):
    import os
    from collections import Counter
    ext_count: Counter = Counter()
    for root, dirs, files in os.walk(folder_path):
        depth = root.replace(folder_path, "").count(os.sep)
        if depth > max_depth:
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__")]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext:
                ext_count[ext.lower()] += 1
    lang_count: Counter = Counter()
    for ext, count in ext_count.items():
        info = _LANG_MAP.get(ext)
        if info:
            lang_count[info[0]] += count
    top5 = [lang for lang, _ in lang_count.most_common(5)]
    result = []
    for lang in top5:
        for ext, info in _LANG_MAP.items():
            if info[0] == lang:
                result.append(info)
                break
    return result


def _detect_folder_languages(folder_path: str, max_depth: int = 2):
    if HAS_RUST:
        return _rust_scan(folder_path, max_depth)
    return _scan_folder_languages_py(folder_path, max_depth)


def _detect_language(filepath: str):
    if HAS_RUST:
        return _rust_detect(filepath)
    return _detect_language_py(filepath)


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
        self._list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.model().rowsMoved.connect(self._sync_list_to_config)
        layout.addWidget(self._list)

        self._clean_missing()
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

    @staticmethod
    def _ensure_list(val):
        if isinstance(val, str):
            import json
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return []
        return val if isinstance(val, list) else []

    def _add_pin(self, path: str):
        config = get_config()
        pinned = self._ensure_list(config.get("pinned.items", []))
        if path not in pinned:
            pinned.append(path)
            config.set("pinned.items", pinned)
        self._load_pins()

    def _remove_pin(self, path: str):
        config = get_config()
        pinned = self._ensure_list(config.get("pinned.items", []))
        if path in pinned:
            pinned.remove(path)
            config.set("pinned.items", pinned)
        self._load_pins()

    def _load_pins(self):
        self._list.clear()
        config = get_config()
        pinned = self._ensure_list(config.get("pinned.items", []))
        has_items = False
        max_items = 20
        shown = 0
        for path in pinned:
            if not os.path.exists(path):
                continue
            if shown >= max_items:
                break
            self._add_item(path)
            shown += 1
            has_items = True
        remaining = len(pinned) - shown
        if remaining > 0:
            item = QListWidgetItem()
            item.setText(f"... и ещё {remaining}")
            item.setData(Qt.ItemDataRole.UserRole, "")
            item.setFlags(Qt.ItemFlag.ItemIsSelectable)
            from PyQt6.QtGui import QFont
            f = QFont()
            f.setItalic(True)
            item.setFont(f)
            self._list.addItem(item)
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
            result = _detect_language(path)
            if result:
                badges.append(result)

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
        name_label.setStyleSheet("font-size: 12px;")
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
        row = self._list.row(item)
        menu = QMenu(self)

        act_unpin = QAction("Unpin", self)
        act_unpin.triggered.connect(lambda: self._remove_pin(path))
        menu.addAction(act_unpin)

        menu.addSeparator()

        act_move_up = QAction("Move Up", self)
        act_move_up.setEnabled(row > 0)
        act_move_up.triggered.connect(lambda: self._move_item(row, -1))
        menu.addAction(act_move_up)

        act_move_down = QAction("Move Down", self)
        act_move_down.setEnabled(row < self._list.count() - 1)
        act_move_down.triggered.connect(lambda: self._move_item(row, 1))
        menu.addAction(act_move_down)

        menu.addSeparator()

        act_clean = QAction("Remove missing paths", self)
        act_clean.triggered.connect(self._clean_missing)
        menu.addAction(act_clean)

        menu.exec(self._list.viewport().mapToGlobal(pos))

    def _move_item(self, row: int, direction: int):
        target = row + direction
        if target < 0 or target >= self._list.count():
            return
        item = self._list.takeItem(row)
        self._list.insertItem(target, item)
        self._list.setCurrentRow(target)
        self._sync_list_to_config()

    def _sync_list_to_config(self):
        config = get_config()
        paths = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            p = item.data(Qt.ItemDataRole.UserRole)
            if p:
                paths.append(p)
        config.set("pinned.items", paths)

    def _clean_missing(self):
        config = get_config()
        pinned = self._ensure_list(config.get("pinned.items", []))
        pinned = [p for p in pinned if os.path.exists(p)]
        config.set("pinned.items", pinned)
        self._load_pins()