from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import QWidget

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    _HAS_WEBENGINE: bool = True
except ImportError:
    QWebEngineView = object  # type: ignore[assignment,misc]
    _HAS_WEBENGINE: bool = False


class HtmlBrowser(QWebEngineView):  # type: ignore[misc]
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("html-browser")

    def load_file(self, path: str) -> None:
        if _HAS_WEBENGINE:
            self.setUrl(QUrl.fromLocalFile(path))
