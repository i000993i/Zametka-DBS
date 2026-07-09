from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtWidgets import QFileIconProvider
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QModelIndex, QSortFilterProxyModel

from assets.icons import icon


_HIDDEN_PATTERNS: set[str] = {
    ".git", "node_modules", ".obsidian", ".trash",
    ".DS_Store", "thumbs.db", ".vscode", ".idea",
    "__pycache__", ".venv", ".env",
}

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
with open(_DATA_DIR / "file_icons.json", encoding="utf-8") as _f:
    _FILE_ICONS: dict[str, list[str]] = json.load(_f)

_TEXT_EXTS: set[str] = {".md", ".mdx", ".txt"}


class FileFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = set()
        self._filter_text = ""

    def set_filter_text(self, text: str):
        self._filter_text = text.lower()
        self.invalidateFilter()

    def set_expanded(self, path, state):
        if state:
            self._expanded.add(path)
        else:
            self._expanded.discard(path)

    def columnCount(self, parent=None):
        return 1

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        if not index.isValid():
            return True
        name = model.fileName(index)
        if name in _HIDDEN_PATTERNS or name.startswith("."):
            return False
        if self._filter_text:
            if self._filter_text not in name.lower():
                if model.isDir(index):
                    for i in range(model.rowCount(index)):
                        if self._filter_children_recursive(model, i, index):
                            return True
                return False
        return True

    def _filter_children_recursive(self, model, row, parent) -> bool:
        idx = model.index(row, 0, parent)
        if not idx.isValid():
            return False
        name = model.fileName(idx)
        if self._filter_text in name.lower():
            return True
        if model.isDir(idx):
            for i in range(model.rowCount(idx)):
                if self._filter_children_recursive(model, i, idx):
                    return True
        return False

    def data(self, index, role):
        if role == Qt.ItemDataRole.DecorationRole:
            src = self.mapToSource(index)
            path = self.sourceModel().filePath(src)
            if os.path.isdir(path):
                ico = "folder-open" if path in self._expanded else "folder"
                return icon(ico, "#888888", hover_color="#bbbbbb")
            ext = os.path.splitext(path)[1].lower()
            info = _FILE_ICONS.get(ext)
            if info:
                _, color = info
                base = "file-text" if ext in _TEXT_EXTS else "file"
                return icon(base, color, hover_color="#eeeeee")
            return icon("file", "#808080")
        return super().data(index, role)


class NullIconProvider(QFileIconProvider):
    def icon(self, info_or_type):
        return QIcon()
