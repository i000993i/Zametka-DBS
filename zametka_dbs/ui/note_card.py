from __future__ import annotations

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)
from PyQt6.QtGui import QPixmap, QMouseEvent
from PyQt6.QtCore import Qt, pyqtSignal

from assets.icons import icon
from zametka_dbs.core.config import get_config
from zametka_dbs.core.event_bus import get_bus, Events
from zametka_dbs.ui.styles import _THEME_VARS
from zametka_dbs.core.badges import (
    detect_file_badges, get_assigned_badges, badge_stylesheet,
)


class NoteCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, filepath: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._filepath: str = filepath
        self.setObjectName("note-card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._dark: bool = get_config().get("theme", "dark") == "dark"
        _v: dict = _THEME_VARS["dark" if self._dark else "light"]
        self.setStyleSheet(
            f"background-color: {_v['bg2']}; "
            f"border: 1px solid {_v['border2']}; "
            f"border-radius: 4px;"
        )
        get_bus().subscribe(Events.THEME_CHANGED, self._on_theme_changed)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        name: str = os.path.basename(filepath) or filepath
        is_dir: bool = os.path.isdir(filepath)

        layout.addLayout(self._build_name_row(filepath, name, is_dir))
        badge_row = self._build_badge_row(filepath)
        if badge_row:
            layout.addLayout(badge_row)

    def _build_name_row(self, filepath: str, name: str, is_dir: bool) -> QHBoxLayout:
        row1: QHBoxLayout = QHBoxLayout()
        row1.setSpacing(6)

        ico_label: QLabel = QLabel()
        if is_dir:
            pix: QPixmap = icon("folder").pixmap(14, 14)
        else:
            ext: str = os.path.splitext(filepath)[1].lower()
            if ext in (".md", ".mdx", ".txt"):
                pix = icon("file-text").pixmap(14, 14)
            else:
                pix = icon("file").pixmap(14, 14)
        ico_label.setPixmap(pix)
        ico_label.setFixedWidth(18)
        row1.addWidget(ico_label)

        name_label: QLabel = QLabel(name)
        _v = _THEME_VARS["dark" if self._dark else "light"]
        name_label.setStyleSheet(f"color: {_v['fg0']}; font-size: 12px; font-weight: 600;")
        name_label.setWordWrap(False)
        row1.addWidget(name_label, 1)
        return row1

    def _build_badge_row(self, filepath: str) -> QHBoxLayout | None:
        badges = list(detect_file_badges(filepath))
        badges.extend(get_assigned_badges(filepath))
        if not badges:
            return None

        row2: QHBoxLayout = QHBoxLayout()
        row2.setSpacing(4)
        row2.setContentsMargins(0, 0, 0, 0)
        for b in badges[:6]:
            bl: QLabel = QLabel(b["label"])
            bl.setStyleSheet(badge_stylesheet(b, font_size="9px"))
            row2.addWidget(bl)
        if len(badges) > 6:
            more: QLabel = QLabel(f"+{len(badges) - 6}")
            _v = _THEME_VARS["dark" if self._dark else "light"]
            more.setStyleSheet(f"color: {_v['fg2']}; font-size: 9px;")
            row2.addWidget(more)
        row2.addStretch()
        return row2

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._filepath)
        super().mousePressEvent(event)

    def _on_theme_changed(self, **kwargs) -> None:
        self._dark = get_config().get("theme", "dark") == "dark"
        _v = _THEME_VARS["dark" if self._dark else "light"]
        self.setStyleSheet(
            f"background-color: {_v['bg2']}; "
            f"border: 1px solid {_v['border2']}; "
            f"border-radius: 4px;"
        )

    def filepath(self) -> str:
        return self._filepath
