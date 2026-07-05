from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from assets.icons import icon
from zametka_dbs.search.engine import SearchEngine


class SearchWidget(QWidget):
    """
    Search panel with input field, replace field, and results list.

    - Debounced search (300ms after typing stops)
    - Shows filename, title, snippet, score
    - Click result → emits file path
    - Replace button → emits (find, replace) for current file
    """

    result_clicked = pyqtSignal(str)
    search_requested = pyqtSignal(str)
    replace_requested = pyqtSignal(str, str)

    def __init__(self, engine: SearchEngine, parent=None):
        super().__init__(parent)
        self.setObjectName("search-widget")
        self._engine = engine

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("search-header")
        header.setFixedHeight(28)
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(10, 0, 14, 0)
        hdr_layout.setSpacing(4)
        hdr_icon = QLabel()
        hdr_icon.setPixmap(icon("search").pixmap(12, 12))
        hdr_icon.setFixedWidth(16)
        hdr_layout.addWidget(hdr_icon)
        hdr_text = QLabel("Search")
        hdr_text.setObjectName("search-header-label")
        hdr_layout.addWidget(hdr_text)
        hdr_layout.addStretch()
        layout.addWidget(header)

        # Search input
        self._input = QLineEdit()
        self._input.setObjectName("search-input")
        self._input.setPlaceholderText("Search notes...")
        self._input.setClearButtonEnabled(True)
        layout.addWidget(self._input)

        # Replace input + button
        replace_row = QWidget()
        replace_row.setObjectName("replace-row")
        replace_layout = QHBoxLayout(replace_row)
        replace_layout.setContentsMargins(8, 2, 8, 2)
        replace_layout.setSpacing(4)

        self._replace_input = QLineEdit()
        self._replace_input.setObjectName("replace-input")
        self._replace_input.setPlaceholderText("Replace with...")
        replace_layout.addWidget(self._replace_input, 1)

        self._replace_btn = QPushButton("Replace All")
        self._replace_btn.setObjectName("replace-btn")
        self._replace_btn.setFixedHeight(24)
        self._replace_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._replace_btn.clicked.connect(self._on_replace)
        replace_layout.addWidget(self._replace_btn)

        layout.addWidget(replace_row)

        # Results
        self._results = QListWidget()
        self._results.setObjectName("search-results")
        self._results.setFrameShape(QListWidget.Shape.NoFrame)
        self._results.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._results)

        # Debounce
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._do_search)

        self._input.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text: str):
        self._timer.stop()
        self._timer.start()

    def _do_search(self):
        query = self._input.text().strip()
        if not query:
            self._results.clear()
            return

        results = self._engine.search(query)
        self._display_results(results)
        self.search_requested.emit(query)

    def _display_results(self, results: list):
        self._results.clear()

        if not results:
            item = QListWidgetItem("  No results found")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._results.addItem(item)
            return

        self._results.addItem(
            QListWidgetItem(f"  {len(results)} results")
        )

        for r in results:
            text = (
                f"  {r.filename}\n"
                f"  {r.snippet[:80]}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, r.path)
            item.setData(Qt.ItemDataRole.UserRole + 1, r.score)
            self._results.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.result_clicked.emit(path)

    def _on_replace(self):
        find_text = self._input.text().strip()
        replace_text = self._replace_input.text()
        if find_text:
            self.replace_requested.emit(find_text, replace_text)

    def clear(self):
        self._input.clear()
        self._replace_input.clear()
        self._results.clear()

    def focus(self):
        self._input.setFocus()
        self._input.selectAll()

    def _styles(self) -> str:
        return """
            QWidget#search-widget {
                background-color: #0a0a0a;
                border-top: 1px solid #1a1a1a;
            }
            QWidget#search-header {
                background-color: #0a0a0a;
            }
            QLabel#search-header-label {
                color: #808080;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
                text-transform: uppercase;
            }
            QLineEdit#search-input, QLineEdit#replace-input {
                background-color: #1a1a1a;
                color: #eeeeee;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                margin: 4px 8px;
                font-size: 13px;
                selection-background-color: #333333;
            }
            QLineEdit#search-input:focus, QLineEdit#replace-input:focus {
                border: 1px solid #fab283;
            }
            QPushButton#replace-btn {
                background-color: #1a1a1a;
                color: #c9d1d9;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 11px;
                margin: 4px 0;
            }
            QPushButton#replace-btn:hover {
                background-color: #2a2a2a;
                border: 1px solid #fab283;
                color: #fab283;
            }
            QListWidget#search-results {
                background-color: #0a0a0a;
                color: #808080;
                font-size: 12px;
                border: none;
                outline: none;
                padding: 2px 0;
            }
            QListWidget#search-results::item {
                padding: 4px 14px;
                min-height: 32px;
                border-bottom: 1px solid #1a1a1a;
            }
            QListWidget#search-results::item:hover {
                background-color: #1a1a1a;
                color: #eeeeee;
            }
            QListWidget#search-results::item:selected {
                background-color: #1a1a1a;
                color: #fab283;
            }
        """
