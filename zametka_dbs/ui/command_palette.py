from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QShowEvent
from zametka_dbs.core.event_bus import get_bus, Events
from zametka_dbs.ui.styles import _THEME_VARS


class CommandPalette(QWidget):
    command_triggered = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("command-palette")
        self.setFixedWidth(420)
        self.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._search: QLineEdit = QLineEdit()
        self._search.setObjectName("palette-search")
        self._search.setPlaceholderText("Type a command...")
        self._search.setClearButtonEnabled(True)
        self._search.setFixedHeight(36)
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        self._list: QListWidget = QListWidget()
        self._list.setObjectName("palette-list")
        self._list.itemClicked.connect(self._execute)
        layout.addWidget(self._list, 1)

        self._commands: list[tuple[str, str]] = []
        self._all_items: list[QListWidgetItem] = []

        self._dark: bool = True
        self.setStyleSheet(self._styles())
        get_bus().subscribe(Events.THEME_CHANGED, self._on_theme_changed)

    def _on_theme_changed(self, theme: str, **kwargs: object) -> None:
        self._dark = theme == "dark"
        self.setStyleSheet(self._styles())

    def set_commands(self, commands: list[tuple[str, str]]) -> None:
        self._commands = commands
        self._all_items.clear()
        self._list.clear()
        for cmd_id, label in commands:
            item: QListWidgetItem = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, cmd_id)
            self._all_items.append(item)
            self._list.addItem(item)

    def showEvent(self, event: QShowEvent | None) -> None:
        super().showEvent(event)
        self._search.setFocus()
        self._search.selectAll()

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if event is not None and event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event is not None and event.key() == Qt.Key.Key_Down:
            idx: int = self._list.currentRow()
            if idx < self._list.count() - 1:
                self._list.setCurrentRow(idx + 1)
        elif event is not None and event.key() == Qt.Key.Key_Up:
            idx: int = self._list.currentRow()
            if idx > 0:
                self._list.setCurrentRow(idx - 1)
        elif event is not None and event.key() == Qt.Key.Key_Return:
            item: QListWidgetItem | None = self._list.currentItem()
            if item:
                self._execute(item)
        else:
            super().keyPressEvent(event)

    def _filter(self, text: str) -> None:
        text_lower: str = text.lower()
        self._list.clear()
        for item in self._all_items:
            if text_lower in item.text().lower():
                self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _execute(self, item: QListWidgetItem) -> None:
        cmd_id: str = item.data(Qt.ItemDataRole.UserRole)
        self.command_triggered.emit(cmd_id)
        self.close()

    def _styles(self) -> str:
        v = _THEME_VARS["dark" if self._dark else "light"]
        return f"""
            QWidget#command-palette {{
                background-color: {v["bg2"]};
                border: 1px solid {v["border2"]};
                border-radius: 6px;
            }}
            QLineEdit#palette-search {{
                background-color: {v["bg0"]};
                color: {v["fg0"]};
                border: none;
                border-bottom: 1px solid {v["border2"]};
                border-radius: 0;
                padding: 8px 14px;
                font-size: 14px;
            }}
            QListWidget#palette-list {{
                background-color: transparent;
                border: none;
                color: {v["fg1"]};
                font-size: 13px;
                outline: none;
                padding: 4px;
            }}
            QListWidget#palette-list::item {{
                padding: 6px 14px;
                border-radius: 3px;
            }}
            QListWidget#palette-list::item:hover,
            QListWidget#palette-list::item:selected {{
                background-color: {v["sel_bg"]};
                color: {v["fg0"]};
            }}
        """
