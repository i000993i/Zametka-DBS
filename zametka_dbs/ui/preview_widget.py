from PyQt6.QtWidgets import QTextBrowser, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QScrollArea
from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal, QSize

from assets.icons import icon
from zametka_dbs.preview.renderer import render_markdown
from zametka_dbs.core.config import get_config
from zametka_dbs.core.event_bus import get_bus, Events
from zametka_dbs.ui.document_viewer import DocumentViewer


_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}


class PreviewWidget(QWidget):
    """
    Markdown preview pane with image viewer.

    Renders the editor's content as styled HTML.
    Handles wikilink:// navigation clicks.
    Shows images when a supported image file path is provided.
    """

    wikilink_clicked = pyqtSignal(str)
    rendered = pyqtSignal(str)

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

        # Browser (markdown)
        self._browser = QTextBrowser()
        self._browser.setObjectName("preview-browser")
        self._browser.setReadOnly(True)
        self._browser.setOpenExternalLinks(False)
        self._browser.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._browser.anchorClicked.connect(self._on_anchor_clicked)
        layout.addWidget(self._browser)

        # Image viewer (hidden by default)
        self._image_scroll = QScrollArea()
        self._image_scroll.setObjectName("preview-image-scroll")
        self._image_scroll.setWidgetResizable(True)
        self._image_scroll.setVisible(False)
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setObjectName("preview-image-label")
        self._image_scroll.setWidget(self._image_label)
        layout.addWidget(self._image_scroll)

        # Document viewer (hidden by default)
        self._doc_viewer = DocumentViewer()
        self._doc_viewer.setObjectName("preview-doc")
        self._doc_viewer.setVisible(False)
        layout.addWidget(self._doc_viewer)

        # Debounce timer
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._do_render)

        self._source = ""
        self._pending = False
        self._note_map: dict | None = None
        self._dark = True
        get_bus().subscribe(Events.THEME_CHANGED, self._on_theme_changed)

    def set_note_map(self, note_map: dict | None):
        self._note_map = note_map

    def update_content(self, text: str):
        self._source = text
        self._timer.stop()
        self._timer.start()

    def show_image(self, filepath: str):
        self._timer.stop()
        self._browser.setVisible(False)
        self._doc_viewer.setVisible(False)
        self._image_scroll.setVisible(True)
        from PyQt6.QtGui import QPixmap
        pix = QPixmap(filepath)
        if pix.isNull():
            self._image_label.setText("Cannot load image")
            return
        max_w = self._image_scroll.viewport().width() - 20
        max_h = self._image_scroll.viewport().height() - 20
        if pix.width() > max_w or pix.height() > max_h:
            pix = pix.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        self._image_label.setPixmap(pix)

    def show_document(self, filepath: str):
        self._timer.stop()
        self._browser.setVisible(False)
        self._image_scroll.setVisible(False)
        self._doc_viewer.setVisible(True)
        self._doc_viewer.load(filepath)

    def set_html(self, html: str):
        self._timer.stop()
        self._image_scroll.setVisible(False)
        self._doc_viewer.setVisible(False)
        self._browser.setVisible(True)
        try:
            self._browser.setHtml(html)
        except Exception:
            self._browser.clear()

    def _on_theme_changed(self, theme: str, **kwargs):
        self._dark = theme == "dark"
        if self._source:
            self._do_render()

    def _do_render(self):
        html = render_markdown(self._source, note_map=self._note_map, dark=self._dark)
        self._browser.setHtml(html)
        self.rendered.emit(html)

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
        self._image_scroll.setVisible(False)
        self._doc_viewer.setVisible(False)
        self._doc_viewer.clear()
        self._browser.setVisible(True)
        self._image_label.clear()
        self.update_content("")


