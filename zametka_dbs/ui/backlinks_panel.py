import os

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont

from assets.icons import icon


class BacklinksPanel(QWidget):
    """
    Панель обратных связей: показывает какие заметки ссылаются
    на текущую через [[wikilinks]].

    Сигнал:
      backlink_clicked(path) — пользователь кликнул на backlink
    """

    backlink_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("backlinks-panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self._header = QWidget()
        self._header.setObjectName("backlinks-header")
        self._header.setFixedHeight(28)
        hdr_layout = QHBoxLayout(self._header)
        hdr_layout.setContentsMargins(10, 0, 14, 0)
        hdr_layout.setSpacing(4)
        hdr_icon = QLabel()
        hdr_icon.setPixmap(icon("link").pixmap(12, 12))
        hdr_icon.setFixedWidth(16)
        hdr_layout.addWidget(hdr_icon)
        hdr_text = QLabel("Backlinks")
        hdr_text.setObjectName("backlinks-header-label")
        hdr_layout.addWidget(hdr_text)
        hdr_layout.addStretch()
        layout.addWidget(self._header)

        # List
        self._list = QListWidget()
        self._list.setObjectName("backlinks-list")
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

        self.setStyleSheet(self._styles())

    def update_backlinks(self, links: list[str]):
        self._list.clear()
        if not links:
            item = QListWidgetItem("  No backlinks")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._list.addItem(item)
            return

        for link in links:
            display = os.path.basename(link).replace(".md", "")
            item = QListWidgetItem(f"  {display}")
            item.setData(Qt.ItemDataRole.UserRole, link)
            self._list.addItem(item)

    def clear(self):
        self._list.clear()

    def _on_item_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.backlink_clicked.emit(path)

    def _styles(self) -> str:
        return """
            QWidget#backlinks-panel {
                background-color: #0a0a0a;
                border-top: 1px solid #1a1a1a;
            }
            QWidget#backlinks-header {
                background-color: #0a0a0a;
            }
            QLabel#backlinks-header-label {
                color: #808080;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
                text-transform: uppercase;
            }
            QListWidget#backlinks-list {
                background-color: #0a0a0a;
                color: #808080;
                font-size: 12px;
                border: none;
                outline: none;
                padding: 2px 0;
            }
            QListWidget#backlinks-list::item {
                padding: 3px 14px;
                min-height: 22px;
            }
            QListWidget#backlinks-list::item:hover {
                background-color: #1a1a1a;
                color: #eeeeee;
            }
            QListWidget#backlinks-list::item:selected {
                background-color: #1a1a1a;
                color: #fab283;
            }
        """
