from __future__ import annotations

import os
import subprocess

from PyQt6.QtWidgets import QTreeView, QMenu, QWidget
from PyQt6.QtGui import QFileSystemModel, QStandardItemModel, QAction
from PyQt6.QtCore import Qt, QDir, QModelIndex, pyqtSignal, QPoint, QSize

from zametka_dbs.core.event_bus import get_bus, Events
from zametka_dbs.ui.tree_style import TreeBranchStyle
from zametka_dbs.ui.file_filter_proxy import FileFilterProxy, NullIconProvider


def _open_with_notepad(path: str):
    subprocess.Popen(["notepad.exe", path], shell=True)

def _open_with_default(path: str):
    os.startfile(path)

def _open_file_location(path: str):
    subprocess.Popen(["explorer.exe", "/select,", os.path.normpath(path)])


class FileTreeWidget(QTreeView):
    file_opened: pyqtSignal = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus = get_bus()
        self._vault_root_set = False
        self._filter_text = ""

        self._placeholder = QStandardItemModel()
        self.setModel(self._placeholder)

        self._source_model = QFileSystemModel()
        self._source_model.setIconProvider(NullIconProvider())
        self._source_model.setFilter(
            QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot
        )
        self._source_model.setNameFilters([])
        self._source_model.setNameFilterDisables(False)

        self._proxy = FileFilterProxy()
        self._proxy.setSourceModel(self._source_model)

        self.setStyle(TreeBranchStyle())
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

    def navigate_to_folder(self, folder_path: str) -> None:
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

    def set_vault_path(self, vault_path: str) -> None:
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
            self._add_open_actions(menu, path)
            menu.addSeparator()

        self._add_new_actions(menu, path, is_file)
        menu.addSeparator()

        self._add_file_actions(menu, path, is_file)
        menu.addSeparator()

        self._add_location_actions(menu, path, is_file)

        menu.exec(self.viewport().mapToGlobal(pos))

    def _add_open_actions(self, menu: QMenu, path: str):
        act_open = QAction("Open with Zametka", self)
        act_open.triggered.connect(lambda: self.file_opened.emit(path))
        menu.addAction(act_open)

        act_notepad = QAction("Open with Notepad", self)
        act_notepad.triggered.connect(lambda: _open_with_notepad(path))
        menu.addAction(act_notepad)

        act_default = QAction("Open with system default", self)
        act_default.triggered.connect(lambda: _open_with_default(path))
        menu.addAction(act_default)

    def _add_new_actions(self, menu: QMenu, path: str, is_file: bool):
        parent_dir = os.path.dirname(path) if is_file else path
        act_new_file = QAction("New File", self)
        act_new_file.triggered.connect(lambda: self._new_file(parent_dir))
        menu.addAction(act_new_file)

        act_new_folder = QAction("New Folder", self)
        act_new_folder.triggered.connect(lambda: self._new_folder(parent_dir))
        menu.addAction(act_new_folder)

    def _add_file_actions(self, menu: QMenu, path: str, is_file: bool):
        act_rename = QAction("Rename", self)
        act_rename.triggered.connect(lambda: self._rename_item(path))
        menu.addAction(act_rename)

        act_delete = QAction("Delete", self)
        act_delete.triggered.connect(lambda: self._delete_item(path, is_file))
        menu.addAction(act_delete)

    def _add_location_actions(self, menu: QMenu, path: str, is_file: bool):
        if is_file:
            act_move_to = QAction("Move to folder", self)
            act_move_to.triggered.connect(lambda: self._move_to_folder(path))
            menu.addAction(act_move_to)

        act_explorer = QAction("Open file location", self)
        act_explorer.triggered.connect(lambda: _open_file_location(path))
        menu.addAction(act_explorer)

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