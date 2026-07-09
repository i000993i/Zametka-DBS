from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMenu, QFileDialog,
)
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint

from assets.icons import icon
from zametka_dbs.core.config import get_config
from zametka_dbs.core.event_bus import get_bus, Events

from zametka_dbs.core.rust_bridge import HAS_RUST
from zametka_dbs.core.rust_bridge import rust_detect_language as _rust_detect
from zametka_dbs.core.rust_bridge import rust_scan_folder_languages as _rust_scan

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
with open(_DATA_DIR / "file_icons.json", encoding="utf-8") as _f:
    _LANG_MAP: dict[str, list[str]] = json.load(_f)


def _detect_language_py(filepath: str) -> tuple[str, str] | None:
    _, ext = os.path.splitext(filepath)
    return _LANG_MAP.get(ext.lower())


def _scan_folder_languages_py(folder_path: str, max_depth: int = 2) -> list[tuple[str, str]]:
    ext_count: Counter[str] = Counter()
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
    lang_count: Counter[str] = Counter()
    for ext, count in ext_count.items():
        info = _LANG_MAP.get(ext)
        if info:
            lang_count[info[0]] += count
    top5 = [lang for lang, _ in lang_count.most_common(5)]
    result: list[tuple[str, str]] = []
    for lang in top5:
        for ext, info in _LANG_MAP.items():
            if info[0] == lang:
                result.append(info)
                break
    return result


def _detect_folder_languages(folder_path: str, max_depth: int = 2) -> list[tuple[str, str]]:
    if HAS_RUST:
        return _rust_scan(folder_path, max_depth)
    return _scan_folder_languages_py(folder_path, max_depth)


def _detect_language(filepath: str) -> tuple[str, str] | None:
    if HAS_RUST:
        return _rust_detect(filepath)
    return _detect_language_py(filepath)


class PinnedWidget(QWidget):
    item_clicked = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pinned-widget")

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_list())

        self._clean_missing()
        self._load_pins()
        get_bus().subscribe(Events.THEME_CHANGED, lambda **_: self._load_pins())

    def _build_header(self) -> QWidget:
        header: QWidget = QWidget()
        header.setObjectName("pinned-header")
        header.setFixedHeight(24)
        header_layout: QHBoxLayout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 6, 0)
        header_layout.setSpacing(4)

        header_icon: QLabel = QLabel()
        header_icon.setPixmap(icon("link").pixmap(12, 12))
        header_icon.setFixedWidth(16)
        header_layout.addWidget(header_icon)

        header_label: QLabel = QLabel("PINNED")
        header_label.setObjectName("pinned-label")
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        self._pin_btn: QPushButton = QPushButton()
        self._pin_btn.setIcon(icon("circle"))
        self._pin_btn.setIconSize(QSize(12, 12))
        self._pin_btn.setObjectName("pinned-add-btn")
        self._pin_btn.setFixedSize(18, 18)
        self._pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pin_btn.setToolTip("Pin a file or folder")
        self._pin_btn.clicked.connect(self._show_pin_menu)
        header_layout.addWidget(self._pin_btn)

        return header

    def _build_list(self) -> QListWidget:
        lst: QListWidget = QListWidget()
        lst.setObjectName("pinned-list")
        lst.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        lst.customContextMenuRequested.connect(self._show_context_menu)
        lst.itemClicked.connect(self._on_item_clicked)
        lst.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        lst.setDefaultDropAction(Qt.DropAction.MoveAction)
        lst.model().rowsMoved.connect(self._sync_list_to_config)
        return lst

    def _show_pin_menu(self) -> None:
        menu: QMenu = QMenu(self)

        act_file: QAction = QAction("Pin file...", self)
        act_file.triggered.connect(self._pin_file_dialog)
        menu.addAction(act_file)

        act_folder: QAction = QAction("Pin folder...", self)
        act_folder.triggered.connect(self._pin_folder_dialog)
        menu.addAction(act_folder)

        menu.exec(self._pin_btn.mapToGlobal(self._pin_btn.rect().bottomLeft()))

    def _pin_file_dialog(self) -> None:
        path: str
        path, _ = QFileDialog.getOpenFileName(
            self, "Pin file", "",
            "All Files (*.*)"
        )
        if path:
            self._add_pin(path)

    def _pin_folder_dialog(self) -> None:
        folder: str = QFileDialog.getExistingDirectory(
            self, "Pin folder", "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self._add_pin(folder)

    @staticmethod
    def _ensure_list(val: Any) -> list:
        if isinstance(val, str):
            import json
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return []
        return val if isinstance(val, list) else []

    def _add_pin(self, path: str) -> None:
        config = get_config()
        pinned = self._ensure_list(config.get("pinned.items", []))
        if path not in pinned:
            pinned.append(path)
            config.set("pinned.items", pinned)
        self._load_pins()

    def _remove_pin(self, path: str) -> None:
        config = get_config()
        pinned = self._ensure_list(config.get("pinned.items", []))
        if path in pinned:
            pinned.remove(path)
            config.set("pinned.items", pinned)
        self._load_pins()

    def _load_pins(self) -> None:
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
        remaining: int = len(pinned) - shown
        if remaining > 0:
            item: QListWidgetItem = QListWidgetItem()
            item.setText(f"... \u0438 \u0435\u0449\u0451 {remaining}")
            item.setData(Qt.ItemDataRole.UserRole, "")
            item.setFlags(Qt.ItemFlag.ItemIsSelectable)
            f: QFont = QFont()
            f.setItalic(True)
            item.setFont(f)
            self._list.addItem(item)
        self._list.setVisible(has_items)

    def _add_item(self, path: str) -> None:
        name: str = os.path.basename(path) or path
        is_dir: bool = os.path.isdir(path)
        badges = self._detect_badges(path, is_dir)
        widget = self._build_item_widget(name, is_dir, badges)

        item: QListWidgetItem = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setSizeHint(widget.sizeHint())
        self._list.addItem(item)
        self._list.setItemWidget(item, widget)

    @staticmethod
    def _detect_badges(path: str, is_dir: bool) -> list[tuple[str, str]]:
        badges: list[tuple[str, str]] = []
        if is_dir:
            langs = _detect_folder_languages(path)
            for lang_name, color in langs:
                badges.append((lang_name, color))
        else:
            result = _detect_language(path)
            if result:
                badges.append(result)
        return badges

    @staticmethod
    def _build_item_widget(name: str, is_dir: bool, badges: list[tuple[str, str]]) -> QWidget:
        widget: QWidget = QWidget()
        widget.setObjectName("pinned-item")
        row: QHBoxLayout = QHBoxLayout(widget)
        row.setContentsMargins(8, 2, 8, 2)
        row.setSpacing(6)

        ico_label: QLabel = QLabel()
        if is_dir:
            ico_label.setPixmap(icon("folder").pixmap(14, 14))
        else:
            ico_label.setPixmap(icon("file").pixmap(14, 14))
        ico_label.setFixedWidth(18)
        row.addWidget(ico_label)

        name_label: QLabel = QLabel(name)
        name_label.setObjectName("pinned-name")
        name_label.setStyleSheet("font-size: 12px;")
        row.addWidget(name_label, 1)

        for lang_name, color in badges:
            badge: QLabel = QLabel(lang_name)
            badge.setStyleSheet(
                f"background-color: {color}; color: #ffffff; "
                f"font-size: 9px; font-weight: 600; padding: 1px 5px; "
                f"border-radius: 3px;"
            )
            row.addWidget(badge)

        return widget

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        path: str = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.item_clicked.emit(path)

    def _show_context_menu(self, pos: QPoint) -> None:
        item: QListWidgetItem | None = self._list.itemAt(pos)
        if not item:
            return
        path: str = item.data(Qt.ItemDataRole.UserRole)
        row: int = self._list.row(item)
        menu: QMenu = QMenu(self)

        act_unpin: QAction = QAction("Unpin", self)
        act_unpin.triggered.connect(lambda: self._remove_pin(path))
        menu.addAction(act_unpin)

        menu.addSeparator()

        act_move_up: QAction = QAction("Move Up", self)
        act_move_up.setEnabled(row > 0)
        act_move_up.triggered.connect(lambda: self._move_item(row, -1))
        menu.addAction(act_move_up)

        act_move_down: QAction = QAction("Move Down", self)
        act_move_down.setEnabled(row < self._list.count() - 1)
        act_move_down.triggered.connect(lambda: self._move_item(row, 1))
        menu.addAction(act_move_down)

        menu.addSeparator()

        act_clean: QAction = QAction("Remove missing paths", self)
        act_clean.triggered.connect(self._clean_missing)
        menu.addAction(act_clean)

        menu.exec(self._list.viewport().mapToGlobal(pos))

    def _move_item(self, row: int, direction: int) -> None:
        target: int = row + direction
        if target < 0 or target >= self._list.count():
            return
        item = self._list.takeItem(row)
        self._list.insertItem(target, item)
        self._list.setCurrentRow(target)
        self._sync_list_to_config()

    def _sync_list_to_config(self) -> None:
        config = get_config()
        paths: list[str] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            p: str = item.data(Qt.ItemDataRole.UserRole)
            if p:
                paths.append(p)
        config.set("pinned.items", paths)

    def _clean_missing(self) -> None:
        config = get_config()
        pinned = self._ensure_list(config.get("pinned.items", []))
        pinned = [p for p in pinned if os.path.exists(p)]
        config.set("pinned.items", pinned)
        self._load_pins()
