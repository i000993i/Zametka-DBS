from __future__ import annotations

from PyQt6.QtWidgets import QTabBar, QApplication, QMenu, QWidget
from PyQt6.QtCore import Qt, QMimeData, QPoint, pyqtSignal
from PyQt6.QtGui import (
    QDrag,
    QAction,
    QMouseEvent,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QContextMenuEvent,
    QPixmap,
)


class DraggableTabBar(QTabBar):
    dragged_tab = pyqtSignal(str)
    tab_rename_requested = pyqtSignal(int)
    tab_close_others_requested = pyqtSignal(int)
    tab_close_all_requested = pyqtSignal()
    tab_copy_path_requested = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMovable(True)
        self._drag_start_pos: QPoint | None = None
        self._drag_tab_index: int = -1

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self._drag_tab_index = self.tabAt(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        if (
            event is not None
            and (event.buttons() & Qt.MouseButton.LeftButton)
            and self._drag_start_pos is not None
            and self._drag_tab_index >= 0
        ):
            delta = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
            if delta > QApplication.startDragDistance():
                path = self.tabData(self._drag_tab_index)
                if path:
                    drag: QDrag = QDrag(self)
                    mime: QMimeData = QMimeData()
                    mime.setText(str(path))
                    drag.setMimeData(mime)
                    pix: QPixmap | None = self._grab_tab_pixmap(self._drag_tab_index)
                    if pix:
                        drag.setPixmap(pix)
                    result = drag.exec(Qt.DropAction.MoveAction)
                    self._drag_start_pos = None
                    self._drag_tab_index = -1
                    if result == Qt.DropAction.MoveAction:
                        self.dragged_tab.emit(str(path))
                    return
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent | None) -> None:
        if event is not None and event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent | None) -> None:
        if event is not None:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent | None) -> None:
        if event is not None:
            path = event.mimeData().text()
            if path:
                from zametka_dbs.ui.note_window import NoteWindow
                nw: NoteWindow = NoteWindow(path)
                nw.show()
                nw.raise_()
            event.acceptProposedAction()

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        self._drag_start_pos = None
        self._drag_tab_index = -1
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent | None) -> None:
        if event is None:
            return
        pos: QPoint = event.pos()
        index: int = self.tabAt(pos)
        if index < 0:
            return
        path = self.tabData(index)
        is_untitled: bool = str(path).startswith("__untitled_") if path else True

        menu: QMenu = QMenu(self)

        self._add_tab_actions(menu, index)
        menu.addSeparator()

        self._add_close_actions(menu, index)

        if not is_untitled:
            menu.addSeparator()
            self._add_copy_path_action(menu, index)

        menu.exec(self.mapToGlobal(pos))

    def _add_tab_actions(self, menu: QMenu, index: int):
        act_rename: QAction = QAction("Rename Tab", self)
        act_rename.triggered.connect(lambda: self.tab_rename_requested.emit(index))
        menu.addAction(act_rename)

    def _add_close_actions(self, menu: QMenu, index: int):
        act_close: QAction = QAction("Close", self)
        act_close.triggered.connect(lambda: self.tabCloseRequested.emit(index))
        menu.addAction(act_close)

        act_close_others: QAction = QAction("Close Others", self)
        act_close_others.triggered.connect(
            lambda: self.tab_close_others_requested.emit(index)
        )
        menu.addAction(act_close_others)

        act_close_all: QAction = QAction("Close All", self)
        act_close_all.triggered.connect(lambda: self.tab_close_all_requested.emit())
        menu.addAction(act_close_all)

    def _add_copy_path_action(self, menu: QMenu, index: int):
        act_copy: QAction = QAction("Copy Path", self)
        act_copy.triggered.connect(lambda: self.tab_copy_path_requested.emit(index))
        menu.addAction(act_copy)

    def _grab_tab_pixmap(self, index: int) -> QPixmap | None:
        rect = self.tabRect(index)
        if rect.isValid():
            return self.grab(rect)
        return None
