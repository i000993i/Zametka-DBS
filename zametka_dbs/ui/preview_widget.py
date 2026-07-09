from __future__ import annotations

from PyQt6.QtWidgets import QTextBrowser, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QScrollArea
from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QResizeEvent

from assets.icons import icon
from zametka_dbs.preview.renderer import render_markdown
from zametka_dbs.core.config import get_config
from zametka_dbs.core.event_bus import get_bus, Events
from zametka_dbs.ui.document_viewer import DocumentViewer


class PreviewWidget(QTextBrowser):
    wikilink_clicked = pyqtSignal(str)
    rendered = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dark: bool = True
        self._rendering: bool = False
        self._content: str = ""
        self._note_map: dict[str, str] | None = None
        self._pending: str | None = None

        self.setObjectName("preview-browser")
        self.setOpenExternalLinks(True)
        self.setOpenLinks(False)
        self.anchorClicked.connect(self._on_anchor_clicked)

        self._render_timer: QTimer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._do_render)

        get_bus().subscribe(Events.THEME_CHANGED, self._on_theme_changed)

    def _on_theme_changed(self, theme: str, **kwargs: object) -> None:
        self._dark = theme == "dark"
        if self._pending:
            self.set_content(self._pending, self._note_map)

    def set_note_map(self, note_map: dict[str, str] | None) -> None:
        self._note_map = note_map

    def set_content(self, text: str, note_map: dict[str, str] | None = None) -> None:
        self._pending = text
        self._note_map = note_map or self._note_map
        self._render_timer.start(80)

    def _do_render(self) -> None:
        if not self._pending:
            return
        self._rendering = True
        html: str = render_markdown(self._pending, self._note_map, self._dark)
        self.setHtml(html)
        self.rendered.emit(html)
        self._pending = None
        self._rendering = False

    def _on_anchor_clicked(self, url: QUrl) -> None:
        path: str = url.toLocalFile()
        if path:
            self.wikilink_clicked.emit(path)
        else:
            href: str = url.toString()
            if href.startswith("http"):
                import webbrowser
                webbrowser.open(href)

    def scroll_to_line(self, line: int) -> None:
        pass

    def update_theme(self, dark: bool) -> None:
        self._dark = dark
