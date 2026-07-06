import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QSplitter, QLabel, QPushButton, QTextEdit,
    QToolBar
)
from PyQt6.QtGui import QAction, QFont, QIcon
from PyQt6.QtCore import Qt, QSize

from assets.icons import icon
from zametka_dbs.ui.code_editor import CodeEditor
from zametka_dbs.preview.renderer import render_markdown
from zametka_dbs.core.badges import detect_file_badges, get_assigned_badges, badge_stylesheet
from zametka_dbs.preview.styles import PREVIEW_CSS
from zametka_dbs.core.event_bus import get_bus, Events
from zametka_dbs.ui.styles import _THEME_VARS


class NoteWindow(QMainWindow):
    _open_windows: list["NoteWindow"] = []

    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self._filepath = filepath
        self._note_map: dict | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        NoteWindow._open_windows.append(self)

        name = os.path.basename(filepath)
        self.setWindowTitle(f"{name} — Zametka")
        self.setMinimumSize(700, 500)
        self.resize(950, 650)

        # set in _update_styles

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._setup_toolbar(filepath)
        self._setup_content(layout, filepath)
        self._load_file(filepath)
        self._update_styles()

    def _on_theme_changed(self, theme: str, **kwargs):
        self._dark = theme == 'dark'
        self._update_styles()

    def _update_styles(self):
        v = _THEME_VARS['dark' if self._dark else 'light']
        self.setStyleSheet(f'background-color: {v["bg0"]}; color: {v["fg0"]};')
        self._toolbar.setStyleSheet(f'background: {v["bg1"]}; border-bottom: 1px solid {v["border"]};')
        self._title_label.setStyleSheet(f'color: {v["fg0"]}; font-weight: 600; font-size: 12px;')
        if hasattr(self, '_browser') and self._browser:
            self._browser.setStyleSheet(f'background-color: {v["bg0"]}; color: {v["fg0"]}; border: none; font-size: 14px; padding: 12px;')
        if hasattr(self, '_text') and self._text:
            self._text.setStyleSheet(f'background-color: {v["bg0"]}; color: {v["fg0"]}; border: none; font-family: "Cascadia Code", Consolas, monospace; font-size: 14px; padding: 12px;')

    def set_note_map(self, note_map: dict):
        self._note_map = note_map

    def _setup_toolbar(self, filepath: str):
        tb = QToolBar("Note")
        tb.setMovable(False)
        tb.setIconSize(QSize(14, 14))
        self._toolbar = tb
        self.addToolBar(tb)

        name = os.path.basename(filepath)
        lbl = QLabel(f"  {name}  ")
        self._title_label = lbl
        # set in _update_styles
        tb.addWidget(lbl)

        tb.addSeparator()

        act_reload = QAction(icon("circle-check"), "Reload", self)
        act_reload.triggered.connect(lambda: self._load_file(self._filepath))
        tb.addAction(act_reload)

        badges = detect_file_badges(filepath)
        badges.extend(get_assigned_badges(filepath))
        if badges:
            tb.addSeparator()
            for b in badges[:8]:
                bl = QLabel(b["label"])
                bl.setStyleSheet(badge_stylesheet(b, font_size="9px") + " margin: 2px 0;")
                tb.addWidget(bl)

    def _setup_content(self, layout: QVBoxLayout, filepath: str):
        ext = os.path.splitext(filepath)[1].lower()

        if ext in (".md", ".mdx", ".txt", ".markdown"):
            self._browser = QTextBrowser()
            self._browser.setReadOnly(True)
            self._browser.setOpenExternalLinks(True)
            layout.addWidget(self._browser)
        else:
            self._text = QTextEdit()
            self._text.setReadOnly(True)
            mono = QFont("Consolas", 12)
            mono.setStyleHint(QFont.StyleHint.Monospace)
            self._text.setFont(mono)
            layout.addWidget(self._text)

    def _load_file(self, filepath: str):
        if not os.path.isfile(filepath):
            return
        from zametka_dbs.utils.file_size import is_file_too_large, format_size
        if is_file_too_large(filepath):
            from PyQt6.QtWidgets import QPushButton,  QMessageBox
            reply = QMessageBox.question(
                self, "Large file",
                f"File is {format_size(filepath)}. Open anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return

        ext = os.path.splitext(filepath)[1].lower()
        if ext in (".md", ".mdx", ".txt", ".markdown"):
            html = render_markdown(content, note_map=self._note_map)
            self._browser.setHtml(html)
        else:
            self._text.setPlainText(content)

    def closeEvent(self, event):
        if self in NoteWindow._open_windows:
            NoteWindow._open_windows.remove(self)
        super().closeEvent(event)

    @classmethod
    def close_all(cls):
        for w in list(cls._open_windows):
            w.close()
