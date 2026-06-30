import os
import subprocess

from PyQt6.QtWidgets import QTreeView, QHeaderView, QMenu
from PyQt6.QtGui import QFileSystemModel, QStandardItemModel, QAction
from PyQt6.QtCore import Qt, QDir, QModelIndex, pyqtSignal, QSortFilterProxyModel, QPoint

from zametka_dbs.core.event_bus import get_bus, Events


_HIDDEN_PATTERNS = {
    ".git", "node_modules", ".obsidian", ".trash",
    ".DS_Store", "thumbs.db", ".vscode", ".idea",
    "__pycache__", ".venv", ".env",
}


def _open_with_notepad(path: str):
    subprocess.Popen(["notepad.exe", path], shell=True)

def _open_with_default(path: str):
    os.startfile(path)

def _open_file_location(path: str):
    subprocess.Popen(["explorer.exe", "/select,", os.path.normpath(path)])


class _FileFilterProxy(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        if not index.isValid():
            return True
        name = model.fileName(index)
        if name in _HIDDEN_PATTERNS or name.startswith("."):
            return False
        if model.isDir(index):
            return True
        return True


class FileTreeWidget(QTreeView):
    file_opened = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bus = get_bus()
        self._vault_root_set = False

        # Use an empty placeholder model until vault is opened
        self._placeholder = QStandardItemModel()
        self.setModel(self._placeholder)

        self._source_model = QFileSystemModel()
        self._source_model.setFilter(
            QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot
        )
        self._source_model.setNameFilters([])
        self._source_model.setNameFilterDisables(False)

        self._proxy = _FileFilterProxy()
        self._proxy.setSourceModel(self._source_model)

        self.setAnimated(True)
        self.setIndentation(16)
        self.setHeaderHidden(True)
        self.setExpandsOnDoubleClick(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)

        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 4):
            self.header().hideSection(i)

        self.doubleClicked.connect(self._on_item_double_clicked)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self.setStyleSheet(self._styles())

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

        act_open = QAction(f"Open with Zametka", self)
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

        if is_file:
            act_move_to = QAction("Move to folder", self)
            act_move_to.triggered.connect(lambda: self._move_to_folder(path))
            menu.addAction(act_move_to)

        act_explorer = QAction("Open file location", self)
        act_explorer.triggered.connect(lambda: _open_file_location(path))
        menu.addAction(act_explorer)

        menu.exec(self.viewport().mapToGlobal(pos))

    def _move_to_folder(self, src_path: str):
        if not os.path.isfile(src_path):
            return
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
            self._rebuild_index(self._source_model.rootPath())
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to move file: {e}")

    def _styles(self) -> str:
        return """
            QTreeView {
                background-color: #0a0a0a;
                border: none;
                color: #b0b0b0;
                font-size: 13px;
                outline: none;
            }
            QTreeView::item {
                padding: 3px 8px 3px 4px;
                min-height: 24px;
            }
            QTreeView::item:hover {
                background-color: #1a1a1a;
                color: #eeeeee;
            }
            QTreeView::item:selected {
                background-color: #1a1a1a;
                color: #fab283;
                border-left: 2px solid #fab283;
            }
            QTreeView::branch {
                background-color: transparent;
            }
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                border-image: none;
                image: none;
            }
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                border-image: none;
                image: none;
            }
        """
