from PyQt6.QtCore import Qt, QUrl

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    _HAS_WEBENGINE = True
except ImportError:
    QWebEngineView = object
    _HAS_WEBENGINE = False


class HtmlBrowser(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.setObjectName("html-browser")

    def load_file(self, path: str):
        if _HAS_WEBENGINE:
            self.setUrl(QUrl.fromLocalFile(path))

    def reload_page(self):
        if _HAS_WEBENGINE:
            self.reload()
