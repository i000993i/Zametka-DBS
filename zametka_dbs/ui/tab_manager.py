from __future__ import annotations

import os

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QStackedWidget, QLabel, QPushButton, QInputDialog,
    QApplication, QMessageBox, QWidget,
)

from zametka_dbs.ui.code_editor import CodeEditor
from zametka_dbs.ui.document_viewer import DocumentViewer
from zametka_dbs.ui.preview_widget import PreviewWidget
from zametka_dbs.ui.draggable_tab_bar import DraggableTabBar


class TabManager(QObject):
    save_requested = pyqtSignal(str)
    save_as_requested = pyqtSignal()

    def __init__(
        self,
        editor: CodeEditor,
        preview: PreviewWidget,
        status_saved: QLabel,
        status_info: QLabel,
        html_toggle_btn: QPushButton,
        main_stack: QStackedWidget,
        browser,
        window: QWidget,
        tab_bar: DraggableTabBar | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._editor = editor
        self._preview = preview
        self._status_saved = status_saved
        self._status_info = status_info
        self._html_toggle_btn = html_toggle_btn
        self._main_stack = main_stack
        self._browser = browser
        self._window = window

        self._open_tabs: list[str] = []
        self._tab_state: dict[str, dict] = {}
        self._current_file = ""
        self._untitled_counter = 0

        self.tab_bar = tab_bar

    @property
    def current_file(self) -> str:
        return self._current_file

    @current_file.setter
    def current_file(self, value: str) -> None:
        self._current_file = value

    def connect_signals(self) -> None:
        self.tab_bar.tabCloseRequested.connect(self.close_tab)
        self.tab_bar.currentChanged.connect(self._on_tab_switched)
        self.tab_bar.dragged_tab.connect(self._on_tab_dragged_out)
        self.tab_bar.tab_rename_requested.connect(self._on_tab_rename_requested)
        self.tab_bar.tab_close_others_requested.connect(self._on_tab_close_others)
        self.tab_bar.tab_close_all_requested.connect(self._on_tab_close_all)
        self.tab_bar.tab_copy_path_requested.connect(self._on_tab_copy_path)

    def create_initial_tab(self) -> None:
        content = (
            "# Welcome to Zametka\n\n"
            "Click the folder icon in the sidebar to open a vault folder,\n"
            "or start typing here to create a new note."
        )
        self._untitled_counter += 1
        path = f"__untitled_{self._untitled_counter}__"
        self._open_tabs.append(path)
        self._tab_state[path] = {
            "content": content,
            "cursor": (1, 1),
            "scroll": 0,
            "modified": False,
        }
        tidx = self.tab_bar.addTab("untitled.md")
        self.tab_bar.setTabData(tidx, path)
        self.tab_bar.setCurrentIndex(tidx)
        self._switch_to_tab(tidx)

    def new_note(self) -> None:
        self._untitled_counter += 1
        path = f"__untitled_{self._untitled_counter}__"
        self._open_tabs.append(path)
        self._tab_state[path] = {
            "content": "",
            "cursor": (1, 1),
            "scroll": 0,
            "modified": False,
        }
        tidx = self.tab_bar.addTab("untitled.md")
        self.tab_bar.setCurrentIndex(tidx)
        self.tab_bar.setTabData(tidx, path)
        self._switch_to_tab(tidx)

    def add_tab(self, path: str, content: str, viewer_path: str = "",
                viewer_type: str = "") -> int:
        name = os.path.basename(path)
        self.save_current_tab_state()
        state: dict = {
            "content": content,
            "cursor": (1, 1),
            "scroll": 0,
            "modified": False,
        }
        if viewer_type:
            state["viewer_path"] = viewer_path
            state["viewer_type"] = viewer_type
        self._open_tabs.append(path)
        self._tab_state[path] = state
        tidx = self.tab_bar.addTab(name)
        self.tab_bar.setTabData(tidx, path)
        self.tab_bar.setCurrentIndex(tidx)
        self._switch_to_tab(tidx)
        return tidx

    def close_tab(self, index: int) -> None:
        if index < 0 or index >= self.tab_bar.count():
            return
        path = self.tab_bar.tabData(index)
        self.save_current_tab_state()

        state = self._tab_state.get(path)
        if state and state.get("modified"):
            name = os.path.basename(path) if path and not path.startswith("__") else "Untitled"
            ret = QMessageBox.question(
                self._window, "Unsaved changes",
                f"Save changes to {name}?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if ret == QMessageBox.StandardButton.Cancel:
                return
            if ret == QMessageBox.StandardButton.Save:
                if path.startswith("__untitled"):
                    self.save_as_requested.emit()
                else:
                    self.save_requested.emit(path)

        self.tab_bar.removeTab(index)
        if path in self._open_tabs:
            self._open_tabs.remove(path)
        if path in self._tab_state:
            del self._tab_state[path]

        if self.tab_bar.count() == 0:
            self.new_note()

    def tab_index_of(self, path: str) -> int:
        try:
            return self._open_tabs.index(path)
        except ValueError:
            return -1

    def save_current_tab_state(self) -> None:
        path = self._current_file
        if path not in self._tab_state:
            return
        state = self._tab_state[path]
        state["content"] = self._editor.toPlainText()
        state["cursor"] = (
            self._editor.get_current_line(),
            self._editor.get_current_column(),
        )
        scroll = self._editor.verticalScrollBar().value() if self._editor.verticalScrollBar() else 0
        state["scroll"] = scroll

    def cache_html(self, html: str) -> None:
        if self._current_file in self._tab_state:
            self._tab_state[self._current_file]["html"] = html

    def mark_modified(self) -> None:
        if self._current_file and self._current_file in self._tab_state:
            self._tab_state[self._current_file]["modified"] = True
            self._tab_state[self._current_file].pop("html", None)

    def update_tab_after_save(self, path: str) -> None:
        if path in self._tab_state:
            self._tab_state[path]["modified"] = False
            tidx = self.tab_index_of(path)
            if tidx >= 0:
                name = os.path.basename(path)
                self.tab_bar.setTabText(tidx, name)

    def update_tab_after_save_as(self, old_path: str, new_path: str) -> None:
        self._current_file = new_path
        self._status_saved.setText("Saved")
        self._status_info.setText(new_path)
        name = os.path.basename(new_path)
        self._window.setWindowTitle(f"{name} \u2014 Zametka")

        tidx = self.tab_index_of(old_path)
        if tidx < 0:
            return
        self._open_tabs.remove(old_path)
        self._open_tabs.append(new_path)
        if old_path in self._tab_state:
            del self._tab_state[old_path]
        self._tab_state[new_path] = {
            "content": self._editor.toPlainText(),
            "cursor": (self._editor.get_current_line(), self._editor.get_current_column()),
            "scroll": self._editor.verticalScrollBar().value() if self._editor.verticalScrollBar() else 0,
            "modified": False,
        }
        self.tab_bar.setTabData(tidx, new_path)
        self.tab_bar.setTabText(tidx, name)

    def open_handbook(self) -> None:
        from zametka_dbs.markdown.md_handbook import get_handbook
        content = get_handbook()
        self._untitled_counter += 1
        path = f"__handbook_{self._untitled_counter}__"
        self._open_tabs.append(path)
        self._tab_state[path] = {
            "content": content,
            "cursor": (1, 1),
            "scroll": 0,
            "modified": False,
        }
        tidx = self.tab_bar.addTab("\U0001f4d6 Handbook.md")
        self.tab_bar.setCurrentIndex(tidx)
        self.tab_bar.setTabData(tidx, path)
        self._switch_to_tab(tidx)
        self._status_info.setText("Handbook opened")

    def on_file_opened(self, path: str) -> None:
        idx = self.tab_index_of(path)
        if idx >= 0:
            self.tab_bar.setCurrentIndex(idx)
            return

        ext = os.path.splitext(path)[1].lower()
        if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}:
            self.add_tab(path, "", viewer_path=path, viewer_type="image")
            self._preview.show_image(path)
            return

        if DocumentViewer.can_open(path):
            self.add_tab(path, "", viewer_path=path, viewer_type="document")
            self._preview.show_document(path)
            return

        from zametka_dbs.utils.file_size import is_file_too_large, format_size
        if is_file_too_large(path):
            reply = QMessageBox.question(
                self._window, "Large file",
                f"File is {format_size(path)}. Open anyway? "
                "Large files may cause performance issues.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.add_tab(path, content)
        except Exception as e:
            self._status_info.setText(f"Error: {e}")

    def _switch_to_tab(self, index: int) -> None:
        if index < 0 or index >= self.tab_bar.count():
            return
        path = self.tab_bar.tabData(index)
        if not path or path not in self._tab_state:
            return

        self._save_current_document_state()
        self._current_file = path
        state = self._tab_state[path]

        self._editor.blockSignals(True)
        self._apply_viewer_or_editor(state, path)
        self._editor.blockSignals(False)

        self._update_tab_meta(path, state)

    def _save_current_document_state(self) -> None:
        old_path = self._current_file
        if old_path and old_path in self._tab_state:
            self._tab_state[old_path]["content"] = self._editor.toPlainText()
            self._tab_state[old_path]["scroll"] = (
                self._editor.verticalScrollBar().value() if self._editor.verticalScrollBar() else 0
            )

    def _apply_viewer_or_editor(self, state: dict, path: str) -> None:
        viewer_path = state.get("viewer_path")
        viewer_type = state.get("viewer_type")
        if viewer_path and os.path.isfile(viewer_path):
            if viewer_type == "document":
                self._preview.show_document(viewer_path)
            else:
                self._preview.show_image(viewer_path)
            self._editor.setPlainText("")
            self._editor.setReadOnly(True)
            self._status_saved.setText("")
        else:
            self._editor.setReadOnly(False)
            self._editor.setPlainText(state["content"])
            if path:
                self._editor.set_language_for_file(path)
            if state["cursor"]:
                line, col = state["cursor"]
                self._editor.set_cursor_position(line, col)
            if state.get("scroll") is not None:
                sb = self._editor.verticalScrollBar()
                if sb:
                    sb.setValue(state["scroll"])
            modified = state.get("modified", False)
            self._status_saved.setText("Unsaved" if modified else "Saved")
            cached = state.get("html")
            if cached:
                self._preview.setHtml(cached)
            else:
                self._preview.set_content(state["content"])

    def _update_tab_meta(self, path: str, state: dict) -> None:
        is_untitled = path.startswith("__untitled_") if path else True
        if is_untitled:
            self._window.setWindowTitle("Zametka")
        else:
            name = os.path.basename(path)
            self._window.setWindowTitle(f"{name} \u2014 Zametka")
        viewer_path = state.get("viewer_path")
        if path and not is_untitled and not viewer_path:
            self._status_info.setText(path)
        is_html = path and not is_untitled and path.lower().endswith((".html", ".htm"))
        self._html_toggle_btn.setVisible(is_html)
        if self._main_stack.currentIndex() == 1:
            if is_html and path and os.path.isfile(path):
                self._browser.load_file(os.path.abspath(path))
            else:
                self._main_stack.setCurrentIndex(0)

    def _on_tab_switched(self, index: int) -> None:
        self.save_current_tab_state()
        self._switch_to_tab(index)

    def _on_tab_dragged_out(self, path: str) -> None:
        idx = self.tab_index_of(path)
        if idx >= 0:
            self.close_tab(idx)

    def _on_tab_rename_requested(self, index: int) -> None:
        path = self.tab_bar.tabData(index)
        if not path:
            return
        old_name = os.path.basename(path)
        name, ok = QInputDialog.getText(self._window, "Rename Tab", "New name:", text=old_name)
        if not ok or not name or name == old_name:
            return
        self.tab_bar.setTabText(index, name)

    def _on_tab_close_others(self, index: int) -> None:
        for i in range(self.tab_bar.count() - 1, -1, -1):
            if i != index:
                path = self.tab_bar.tabData(i)
                self.tab_bar.removeTab(i)
                if path in self._open_tabs:
                    self._open_tabs.remove(path)
                if path in self._tab_state:
                    del self._tab_state[path]

    def _on_tab_close_all(self) -> None:
        for i in range(self.tab_bar.count() - 1, -1, -1):
            path = self.tab_bar.tabData(i)
            self.tab_bar.removeTab(i)
            if path in self._open_tabs:
                self._open_tabs.remove(path)
            if path in self._tab_state:
                del self._tab_state[path]
        self.new_note()

    def _on_tab_copy_path(self, index: int) -> None:
        path = self.tab_bar.tabData(index)
        if path:
            QApplication.clipboard().setText(str(path))
