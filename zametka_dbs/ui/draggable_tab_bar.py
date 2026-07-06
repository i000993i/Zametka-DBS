from PyQt6.QtWidgets import QTabBar, QApplication, QMenu
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal
from PyQt6.QtGui import QDrag, QAction


class DraggableTabBar(QTabBar):
    dragged_tab = pyqtSignal(str)
    tab_rename_requested = pyqtSignal(int)
    tab_close_others_requested = pyqtSignal(int)
    tab_close_all_requested = pyqtSignal()
    tab_copy_path_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMovable(True)
        self._drag_start_pos = None
        self._drag_tab_index = -1

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self._drag_tab_index = self.tabAt(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton and
                self._drag_start_pos is not None and
                self._drag_tab_index >= 0):
            delta = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
            if delta > QApplication.startDragDistance():
                path = self.tabData(self._drag_tab_index)
                if path:
                    drag = QDrag(self)
                    mime = QMimeData()
                    mime.setText(str(path))
                    drag.setMimeData(mime)
                    pix = self._grab_tab_pixmap(self._drag_tab_index)
                    if pix:
                        drag.setPixmap(pix)
                    result = drag.exec(Qt.DropAction.MoveAction)
                    self._drag_start_pos = None
                    self._drag_tab_index = -1
                    if result == Qt.DropAction.MoveAction:
                        self.dragged_tab.emit(str(path))
                    return
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        path = event.mimeData().text()
        if path:
            from zametka_dbs.ui.note_window import NoteWindow
            nw = NoteWindow(path)
            nw.show()
            nw.raise_()
        event.acceptProposedAction()

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        self._drag_tab_index = -1
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        pos = event.pos()
        index = self.tabAt(pos)
        if index < 0:
            return
        path = self.tabData(index)
        is_untitled = str(path).startswith("__untitled_") if path else True

        menu = QMenu(self)

        act_rename = QAction("Rename Tab", self)
        act_rename.triggered.connect(lambda: self.tab_rename_requested.emit(index))
        menu.addAction(act_rename)
        menu.addSeparator()

        act_close = QAction("Close", self)
        act_close.triggered.connect(lambda: self.tabCloseRequested.emit(index))
        menu.addAction(act_close)

        act_close_others = QAction("Close Others", self)
        act_close_others.triggered.connect(lambda: self.tab_close_others_requested.emit(index))
        menu.addAction(act_close_others)

        act_close_all = QAction("Close All", self)
        act_close_all.triggered.connect(lambda: self.tab_close_all_requested.emit())
        menu.addAction(act_close_all)

        if not is_untitled:
            menu.addSeparator()
            act_copy = QAction("Copy Path", self)
            act_copy.triggered.connect(lambda: self.tab_copy_path_requested.emit(index))
            menu.addAction(act_copy)

        menu.exec(self.mapToGlobal(pos))

    def _grab_tab_pixmap(self, index):
        rect = self.tabRect(index)
        if rect.isValid():
            return self.grab(rect)
        return None
