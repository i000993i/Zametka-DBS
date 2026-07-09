from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QPushButton,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from assets.icons import icon


class SearchWidget(QWidget):
    result_clicked = pyqtSignal(str)
    replace_requested = pyqtSignal(str, str)

    def __init__(self, engine: object, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._timer: QTimer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._do_search)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_inputs())
        layout.addLayout(self._build_buttons())

        self._results: QListWidget = QListWidget()
        self._results.setObjectName("search-results")
        self._results.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._results, 1)

    def _build_header(self) -> QWidget:
        header: QWidget = QWidget()
        header.setObjectName("sidebar-header")
        header.setFixedHeight(30)
        hdr: QHBoxLayout = QHBoxLayout(header)
        hdr.setContentsMargins(10, 0, 10, 0)
        hdr_icon: QLabel = QLabel()
        hdr_icon.setPixmap(icon("search").pixmap(14, 14))
        hdr_icon.setFixedWidth(18)
        hdr.addWidget(hdr_icon)
        hdr_label: QLabel = QLabel("SEARCH")
        hdr_label.setObjectName("vault-label")
        hdr.addWidget(hdr_label)
        hdr.addStretch()
        return header

    def _build_inputs(self) -> QWidget:
        container: QWidget = QWidget()
        cl: QVBoxLayout = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        self._input: QLineEdit = QLineEdit()
        self._input.setObjectName("search-input")
        self._input.setPlaceholderText("Search files...")
        self._input.setClearButtonEnabled(True)
        self._input.setFixedHeight(28)
        self._input.textChanged.connect(self._on_text_changed)
        cl.addWidget(self._input)

        self._replace_input: QLineEdit = QLineEdit()
        self._replace_input.setObjectName("search-input")
        self._replace_input.setPlaceholderText("Replace with...")
        self._replace_input.setFixedHeight(28)
        self._replace_input.setVisible(False)
        cl.addWidget(self._replace_input)

        return container

    def _build_buttons(self) -> QHBoxLayout:
        btn_row: QHBoxLayout = QHBoxLayout()
        btn_row.setContentsMargins(4, 2, 4, 2)
        btn_row.setSpacing(4)

        self._replace_btn: QPushButton = QPushButton(icon("circle"), "Replace All")
        self._replace_btn.setObjectName("replace-btn")
        self._replace_btn.setVisible(False)
        self._replace_btn.clicked.connect(self._on_replace)
        btn_row.addWidget(self._replace_btn)

        toggle_btn: QPushButton = QPushButton(icon("circle"), "R")
        toggle_btn.setObjectName("toggle-replace-btn")
        toggle_btn.setFixedWidth(24)
        toggle_btn.setToolTip("Toggle replace")
        toggle_btn.clicked.connect(self._toggle_replace)
        btn_row.addWidget(toggle_btn)

        btn_row.addStretch()
        return btn_row

    def _on_text_changed(self, text: str) -> None:
        self._timer.start(200)

    def _do_search(self) -> None:
        query: str = self._input.text()
        if not query or not hasattr(self._engine, "search"):
            return
        results = self._engine.search(query)
        self._display_results(results)

    def _display_results(self, results: list) -> None:
        self._results.clear()
        if not results:
            item: QListWidgetItem = QListWidgetItem("No results found")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._results.addItem(item)
            return
        for r in results:
            label: str = f"{r.get('file', '?')}  —  {r.get('snippet', '')}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, r.get("path", ""))
            self._results.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        path: str = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.result_clicked.emit(path)

    def _toggle_replace(self) -> None:
        visible: bool = not self._replace_input.isVisible()
        self._replace_input.setVisible(visible)
        self._replace_btn.setVisible(visible)

    def _on_replace(self) -> None:
        find_text: str = self._input.text()
        replace_text: str = self._replace_input.text()
        if find_text and replace_text:
            self.replace_requested.emit(find_text, replace_text)

    def clear(self) -> None:
        self._input.clear()
        self._results.clear()

    def focus(self) -> None:
        self._input.setFocus()
