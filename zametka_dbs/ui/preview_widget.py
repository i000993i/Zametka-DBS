from PyQt6.QtWidgets import QTextBrowser, QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal, QSize

from assets.icons import icon
from zametka_dbs.preview.renderer import render_markdown
from zametka_dbs.core.config import get_config


class PreviewWidget(QWidget):
    """
    Markdown preview pane.

    Renders the editor's content as styled HTML.
    Handles wikilink:// navigation clicks.
    """

    wikilink_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("preview-widget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("preview-header")
        header.setFixedHeight(30)
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(10, 0, 14, 0)
        hdr_layout.setSpacing(4)
        hdr_icon = QLabel()
        hdr_icon.setPixmap(icon("eye").pixmap(14, 14))
        hdr_icon.setFixedWidth(18)
        hdr_layout.addWidget(hdr_icon)
        hdr_text = QLabel("Preview")
        hdr_text.setObjectName("preview-header-label")
        hdr_layout.addWidget(hdr_text)
        hdr_layout.addStretch()
        layout.addWidget(header)

        # Browser
        self._browser = QTextBrowser()
        self._browser.setObjectName("preview-browser")
        self._browser.setReadOnly(True)
        self._browser.setOpenExternalLinks(False)
        self._browser.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._browser.anchorClicked.connect(self._on_anchor_clicked)
        layout.addWidget(self._browser)

        # Debounce timer
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._do_render)

        self._source = ""
        self._pending = False

        self.setStyleSheet(self._styles())

    def update_content(self, text: str):
        """Called when editor content changes. Starts debounce."""
        self._source = text
        self._timer.stop()
        self._timer.start()

    def _do_render(self):
        html = render_markdown(self._source)
        self._browser.setHtml(html)

    def _on_anchor_clicked(self, url: QUrl):
        scheme = url.scheme()
        if scheme == "wikilink":
            target = url.path().lstrip("/")
            self.wikilink_clicked.emit(target)
        elif scheme in ("http", "https"):
            import webbrowser
            webbrowser.open(url.toString())

    def clear(self):
        self._source = ""
        self._browser.clear()
        self.update_content("")

    def _styles(self) -> str:
        return """
            QWidget#preview-widget {
                background-color: #0a0a0a;
                border-left: 1px solid #1a1a1a;
            }
            QWidget#preview-header {
                background-color: #0a0a0a;
                border-bottom: 1px solid #1a1a1a;
            }
            QLabel#preview-header-label {
                color: #808080;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
                text-transform: uppercase;
            }
            QTextBrowser#preview-browser {
                background-color: #0a0a0a;
                color: #eeeeee;
                border: none;
                padding: 0;
            }
            QTextBrowser#preview-browser QScrollBar:vertical {
                background-color: #0a0a0a;
                width: 6px;
                margin: 0;
            }
            QTextBrowser#preview-browser QScrollBar::handle:vertical {
                background-color: #1a1a1a;
                min-height: 30px;
                border-radius: 3px;
            }
            QTextBrowser#preview-browser QScrollBar::handle:vertical:hover {
                background-color: #2a2a2a;
            }
            QTextBrowser#preview-browser QScrollBar::add-line:vertical,
            QTextBrowser#preview-browser QScrollBar::sub-line:vertical {
                height: 0;
            }
            QTextBrowser#preview-browser QScrollBar::add-page:vertical,
            QTextBrowser#preview-browser QScrollBar::sub-page:vertical {
                background: none;
            }
        """
