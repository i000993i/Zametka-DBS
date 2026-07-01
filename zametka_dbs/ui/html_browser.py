from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView


class HtmlBrowser(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.setObjectName("html-browser")

    def load_file(self, path: str):
        self.setUrl(QUrl.fromLocalFile(path))

    def reload_page(self):
        self.reload()
