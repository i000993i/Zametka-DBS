from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from zametka_dbs.core.event_bus import get_bus, Events
from zametka_dbs.ui.styles import _THEME_VARS
from zametka_dbs.core.event_bus import get_bus, Events
from zametka_dbs.ui.styles import _THEME_VARS
from PyQt6.QtGui import QKeySequence


class CommandPalette(QWidget):
    command_triggered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("command-palette")
        self.setFixedWidth(420)
        self.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._search = QLineEdit()
        self._search.setObjectName("palette-search")
        self._search.setPlaceholderText("Type a command...")
        self._search.setClearButtonEnabled(True)
        self._search.setFixedHeight(36)
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        self._list = QListWidget()
        self._list.setObjectName("palette-list")
        self._list.itemClicked.connect(self._execute)
        layout.addWidget(self._list, 1)

        self._commands = []
        self._all_items = []

        self._dark = True
        self.setStyleSheet(self._styles())
        get_bus().subscribe(Events.THEME_CHANGED, self._on_theme_changed)

    def _on_theme_changed(self, theme: str, **kwargs):
        self._dark = theme == 'dark'
        self._dark = True
        self.setStyleSheet(self._styles())
        get_bus().subscribe(Events.THEME_CHANGED, self._on_theme_changed)

    def _on_theme_changed(self, theme: str, **kwargs):
        self._dark = theme == 'dark'
        self.setStyleSheet(self._styles())

    def set_commands(self, commands: list[tuple[str, str]]):
        self._commands = commands
        self._all_items.clear()
        self._list.clear()
        for cmd_id, label in commands:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, cmd_id)
            self._all_items.append(item)
            self._list.addItem(item)

    def showEvent(self, event):
        super().showEvent(event)
        self._search.setFocus()
        self._search.selectAll()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Down:
            idx = self._list.currentRow()
            if idx < self._list.count() - 1:
                self._list.setCurrentRow(idx + 1)
        elif event.key() == Qt.Key.Key_Up:
            idx = self._list.currentRow()
            if idx > 0:
                self._list.setCurrentRow(idx - 1)
        elif event.key() == Qt.Key.Key_Return:
            item = self._list.currentItem()
            if item:
                self._execute(item)
        else:
            super().keyPressEvent(event)

    def _filter(self, text: str):
        text_lower = text.lower()
        self._list.clear()
        for item in self._all_items:
            if text_lower in item.text().lower():
                self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _execute(self, item):
        cmd_id = item.data(Qt.ItemDataRole.UserRole)
        self.command_triggered.emit(cmd_id)
        self.close()

    def _styles(self):
        v = _THEME_VARS["dark" if self._dark else "light"]
        return f"""
            QWidget#command-palette {
                background-color: {v["bg2"]};
                border: 1px solid {v["border2"]};
                border-radius: 6px;
            }
            QLineEdit#palette-search {
                background-color: {v["bg0"]};
                color: {v["fg0"]};
                border: none;
                border-bottom: 1px solid {v["border2"]};
                border-radius: 0;
                padding: 8px 14px;
                font-size: 14px;
            }
            QListWidget#palette-list {
                background-color: transparent;
                border: none;
                color: {v["fg1"]};
                font-size: 13px;
                outline: none;
                padding: 4px;
            }
            QListWidget#palette-list::item {
                padding: 6px 14px;
                border-radius: 3px;
            }
            QListWidget#palette-list::item:hover,
            QListWidget#palette-list::item:selected {
                background-color: {v["sel_bg"]};
                color: {v["fg0"]};
            }
        """
