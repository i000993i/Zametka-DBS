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
from zametka_dbs.core.i18n import tr, current_language
from zametka_dbs.core.event_bus import get_bus, Events


class SearchWidget(QWidget):
    result_clicked = pyqtSignal(str)

    def __init__(self, engine: object, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._timer: QTimer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._do_search)

        self._header_label: QLabel | None = None
        self._no_results_item: QListWidgetItem | None = None

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_inputs())
        layout.addWidget(self._build_buttons())

        self._results: QListWidget = QListWidget()
        self._results.setObjectName("search-results")
        self._results.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._results, 1)

        get_bus().subscribe(Events.LANGUAGE_CHANGED, self._retranslate)

    def _retranslate(self, **kwargs) -> None:
        if self._header_label:
            self._header_label.setText(tr("sidebar.search"))
        self._input.setPlaceholderText(tr("search.placeholder"))

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
        self._header_label = QLabel(tr("sidebar.search"))
        self._header_label.setObjectName("vault-label")
        hdr.addWidget(self._header_label)
        hdr.addStretch()
        return header

    def _build_inputs(self) -> QWidget:
        container: QWidget = QWidget()
        cl: QVBoxLayout = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        self._input: QLineEdit = QLineEdit()
        self._input.setObjectName("search-input")
        self._input.setPlaceholderText(tr("search.placeholder"))
        self._input.setClearButtonEnabled(True)
        self._input.setFixedHeight(28)
        self._input.textChanged.connect(self._on_text_changed)
        cl.addWidget(self._input)

        return container

    def _build_buttons(self) -> QWidget:
        container: QWidget = QWidget()
        btn_row: QHBoxLayout = QHBoxLayout(container)
        btn_row.setContentsMargins(4, 2, 4, 2)
        btn_row.setSpacing(4)
        btn_row.addStretch()
        return container

    def _on_text_changed(self, text: str) -> None:
        if text:
            self._timer.start(200)
        else:
            self._results.clear()

    def _do_search(self) -> None:
        query: str = self._input.text()
        if not query or not hasattr(self._engine, "search"):
            return
        results = self._engine.search(query)
        self._display_results(results)

    def _display_results(self, results: list) -> None:
        self._results.clear()
        self._no_results_item = None
        if not results:
            item: QListWidgetItem = QListWidgetItem(tr("search.no_results"))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._results.addItem(item)
            self._no_results_item = item
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

    def clear(self) -> None:
        self._input.clear()
        self._results.clear()

    def focus(self) -> None:
        self._input.setFocus()
