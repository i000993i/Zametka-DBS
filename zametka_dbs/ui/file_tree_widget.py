import os
import subprocess

from PyQt6.QtWidgets import QTreeView, QMenu, QStyle, QProxyStyle, QFileIconProvider
from PyQt6.QtGui import QFileSystemModel, QStandardItemModel, QAction, QPen, QColor, QIcon
from PyQt6.QtCore import Qt, QDir, QModelIndex, pyqtSignal, QSortFilterProxyModel, QPoint, QPointF, QSize

from zametka_dbs.core.event_bus import get_bus, Events
from assets.icons import icon

_HIDDEN_PATTERNS = {
    ".git", "node_modules", ".obsidian", ".trash",
    ".DS_Store", "thumbs.db", ".vscode", ".idea",
    "__pycache__", ".venv", ".env",
}

_FILE_ICONS = {
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
    ".md": ("Markdown", "#083fa1"),
    ".mdx": ("Markdown", "#083fa1"),
    ".txt": ("Text", "#808080"),
}

_TEXT_EXTS = {".md", ".mdx", ".txt"}


def _open_with_notepad(path: str):
    subprocess.Popen(["notepad.exe", path], shell=True)

def _open_with_default(path: str):
    os.startfile(path)

def _open_file_location(path: str):
    subprocess.Popen(["explorer.exe", "/select,", os.path.normpath(path)])


class _TreeBranchStyle(QProxyStyle):
    def drawPrimitive(self, element, option, painter, widget):
        if element == QStyle.PrimitiveElement.PE_IndicatorBranch:
            rect = option.rect
            x = rect.x() + rect.width() // 2
            y_top = rect.top()
            y_bot = rect.bottom()
            y_mid = rect.center().y()
            has_sibling = bool(option.state & QStyle.StateFlag.State_Sibling)
            has_children = bool(option.state & QStyle.StateFlag.State_Children)

            painter.save()
            v = _THEME_VARS["dark" if self._dark else "light"]
            painter.setPen(QPen(QColor(v["border2"]), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)

            if has_sibling:
                painter.drawLine(x, y_top, x, y_bot)
            else:
                painter.drawLine(x, y_top, x, y_mid)

            painter.drawLine(x, y_mid, rect.right(), y_mid)

            if has_children:
                cx, cy = float(x), float(y_mid)
                h = 4.0
                w = 4.0
                if option.state & QStyle.StateFlag.State_Open:
                    tri = [QPointF(cx, cy - h), QPointF(cx - w, cy + h), QPointF(cx + w, cy + h)]
                else:
                    tri = [QPointF(cx - w, cy - h), QPointF(cx - w, cy + h), QPointF(cx + w, cy)]
                painter.setPen(Qt.PenStyle.NoPen)
                v = _THEME_VARS["dark" if self._dark else "light"]
                painter.setBrush(QColor(v["fg1"]))
                painter.drawPolygon(*tri)

            painter.restore()
            return
        super().drawPrimitive(element, option, painter, widget)


class _FileFilterProxy(QSortFilterProxyModel):
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


class _NullIconProvider(QFileIconProvider):
    def icon(self, info_or_type):
        return QIcon()


class FileTreeWidget(QTreeView):
    file_opened = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bus = get_bus()
        self._vault_root_set = False
        self._filter_text = ""

        self._placeholder = QStandardItemModel()
        self.setModel(self._placeholder)

        self._source_model = QFileSystemModel()
        self._source_model.setIconProvider(_NullIconProvider())
        self._source_model.setFilter(
            QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot
        )
        self._source_model.setNameFilters([])
        self._source_model.setNameFilterDisables(False)

        self._proxy = _FileFilterProxy()
        self._proxy.setSourceModel(self._source_model)

        self.setStyle(_TreeBranchStyle())
        self.setAnimated(True)
        self.setIndentation(20)
        self.setHeaderHidden(True)
        self.setExpandsOnDoubleClick(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.setIconSize(QSize(16, 16))

        self.doubleClicked.connect(self._on_item_double_clicked)
        self.expanded.connect(self._on_branch_expanded)
        self.collapsed.connect(self._on_branch_collapsed)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _on_branch_expanded(self, index):
        src = self._proxy.mapToSource(index)
        path = self._source_model.filePath(src)
        self._proxy.set_expanded(path, True)
        self._proxy.dataChanged.emit(index, index, [Qt.ItemDataRole.DecorationRole])

    def _on_branch_collapsed(self, index):
        src = self._proxy.mapToSource(index)
        path = self._source_model.filePath(src)
        self._proxy.set_expanded(path, False)
        self._proxy.dataChanged.emit(index, index, [Qt.ItemDataRole.DecorationRole])

    def clear_vault(self):
        self.setModel(self._placeholder)
        self._vault_root_set = False

    def navigate_to_folder(self, folder_path: str):
        if not os.path.isdir(folder_path):
            return
        src_idx = self._source_model.index(folder_path)
        if not src_idx.isValid():
            return
        if not self._vault_root_set:
            self.setModel(self._proxy)
            self._vault_root_set = True
        self._source_model.setRootPath(folder_path)
        proxy_idx = self._proxy.mapFromSource(src_idx)
        self.setRootIndex(proxy_idx)
        self.setExpandsOnDoubleClick(True)
        self.expand(proxy_idx)

    def set_vault_path(self, vault_path: str):
        if not vault_path or not os.path.isdir(vault_path):
            return
        self._source_model.setRootPath(vault_path)
        src_idx = self._source_model.index(vault_path)
        if not src_idx.isValid():
            return

        if not self._vault_root_set:
            self.setModel(self._proxy)
            self._vault_root_set = True

        proxy_idx = self._proxy.mapFromSource(src_idx)
        self.setRootIndex(proxy_idx)
        self.setExpandsOnDoubleClick(True)
        self.expand(proxy_idx)
        self.bus.emit(Events.VAULT_OPENED, vault_path=vault_path)

    def set_filter_text(self, text: str):
        self._proxy.set_filter_text(text)

    def _file_path_at(self, pos: QPoint) -> tuple[str, bool]:
        index = self.indexAt(pos)
        if not index.isValid() or not self._vault_root_set:
            return "", False
        src = self._proxy.mapToSource(index)
        path = self._source_model.filePath(src)
        is_file = os.path.isfile(path)
        return path, is_file

    def _on_item_double_clicked(self, index: QModelIndex):
        if not self._vault_root_set:
            return
        src = self._proxy.mapToSource(index)
        path = self._source_model.filePath(src)
        if os.path.isfile(path):
            self.file_opened.emit(path)
            self.bus.emit(Events.FILE_OPENED, path=path)

    def _show_context_menu(self, pos: QPoint):
        path, is_file = self._file_path_at(pos)
        if not path:
            return

        menu = QMenu(self)

        if is_file:
            act_open = QAction("Open with Zametka", self)
            act_open.triggered.connect(lambda: self.file_opened.emit(path))
            menu.addAction(act_open)

            menu.addSeparator()

            act_notepad = QAction("Open with Notepad", self)
            act_notepad.triggered.connect(lambda: _open_with_notepad(path))
            menu.addAction(act_notepad)

            act_default = QAction("Open with system default", self)
            act_default.triggered.connect(lambda: _open_with_default(path))
            menu.addAction(act_default)

            menu.addSeparator()

        parent_dir = os.path.dirname(path) if is_file else path
        act_new_file = QAction("New File", self)
        act_new_file.triggered.connect(lambda: self._new_file(parent_dir))
        menu.addAction(act_new_file)

        act_new_folder = QAction("New Folder", self)
        act_new_folder.triggered.connect(lambda: self._new_folder(parent_dir))
        menu.addAction(act_new_folder)

        menu.addSeparator()

        act_rename = QAction("Rename", self)
        act_rename.triggered.connect(lambda: self._rename_item(path))
        menu.addAction(act_rename)

        act_delete = QAction("Delete", self)
        act_delete.triggered.connect(lambda: self._delete_item(path, is_file))
        menu.addAction(act_delete)

        menu.addSeparator()

        if is_file:
            act_move_to = QAction("Move to folder", self)
            act_move_to.triggered.connect(lambda: self._move_to_folder(path))
            menu.addAction(act_move_to)

        act_explorer = QAction("Open file location", self)
        act_explorer.triggered.connect(lambda: _open_file_location(path))
        menu.addAction(act_explorer)

        menu.exec(self.viewport().mapToGlobal(pos))

    def _new_file(self, parent_dir: str):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New File", "File name:", text="untitled.md")
        if not ok or not name:
            return
        fp = os.path.join(parent_dir, name)
        try:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(f"# {os.path.splitext(name)[0]}\n")
            self.file_opened.emit(fp)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to create file: {e}")

    def _new_folder(self, parent_dir: str):
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if not ok or not name:
            return
        fp = os.path.join(parent_dir, name)
        try:
            os.makedirs(fp, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create folder: {e}")

    def _rename_item(self, path: str):
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        old_name = os.path.basename(path)
        parent = os.path.dirname(path)
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=old_name)
        if not ok or not name or name == old_name:
            return
        try:
            os.rename(path, os.path.join(parent, name))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to rename: {e}")

    def _delete_item(self, path: str, is_file: bool):
        from PyQt6.QtWidgets import QMessageBox
        name = os.path.basename(path)
        label = "file" if is_file else "folder"
        reply = QMessageBox.question(
            self, "Delete",
            f"Delete {label} '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            if is_file:
                os.remove(path)
            else:
                import shutil
                shutil.rmtree(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

    def _move_to_folder(self, src_path: str):
        if not os.path.isfile(src_path):
            return
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        parent = QFileDialog.getExistingDirectory(
            self, "Select Target Folder", "",
            QFileDialog.Option.ShowDirsOnly
        )
        if not parent:
            return
        filename = os.path.basename(src_path)
        dst_path = os.path.join(parent, filename)
        try:
            os.rename(src_path, dst_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to move file: {e}")