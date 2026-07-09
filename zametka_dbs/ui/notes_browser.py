from __future__ import annotations

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QLabel, QMenu, QFileDialog,
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, pyqtSignal, QPoint

from assets.icons import icon
from zametka_dbs.core.event_bus import get_bus, Events
from zametka_dbs.core.config import get_config
from zametka_dbs.core.i18n import tr
from zametka_dbs.core.badges import (
    get_notes_list, add_note, remove_note,
    add_assigned_badge, remove_assigned_badge, get_assigned_badges,
)
from zametka_dbs.ui.styles import _THEME_VARS
from zametka_dbs.ui.badge_dialog import BadgeSelectDialog
from zametka_dbs.ui.note_card import NoteCard


class NotesBrowser(QWidget):
    open_note = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dark: bool = get_config().get("theme", "dark") == "dark"
        self.setObjectName("notes-browser")
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        scroll, card_container, card_layout = self._build_scroll_area()
        self._scroll = scroll
        self._card_container = card_container
        self._card_layout = card_layout
        layout.addWidget(self._scroll)

        get_bus().subscribe(Events.THEME_CHANGED, lambda **_: self._rebuild())
        self._rebuild()

    def _build_header(self) -> QWidget:
        header: QWidget = QWidget()
        header.setObjectName("notes-header")
        header.setFixedHeight(34)
        header_layout: QHBoxLayout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 6, 0)
        header_layout.setSpacing(4)

        header_icon: QLabel = QLabel()
        header_icon.setPixmap(icon("layout").pixmap(12, 12))
        header_icon.setFixedWidth(16)
        header_layout.addWidget(header_icon)

        header_label: QLabel = QLabel(tr("notes.header"))
        header_label.setObjectName("notes-label")
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        self._add_file_btn: QPushButton = QPushButton(icon("file"), tr("notes.add_btn"))
        self._add_file_btn.setObjectName("notes-add-btn")
        self._add_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_file_btn.setToolTip(tr("notes.add_tooltip"))
        self._add_file_btn.clicked.connect(self._add_file_dialog)
        header_layout.addWidget(self._add_file_btn)

        return header

    @staticmethod
    def _build_scroll_area() -> tuple[QScrollArea, QWidget, QVBoxLayout]:
        scroll: QScrollArea = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("notes-scroll")

        card_container: QWidget = QWidget()
        card_container.setObjectName("card-container")
        card_layout: QVBoxLayout = QVBoxLayout(card_container)
        card_layout.setContentsMargins(6, 6, 6, 6)
        card_layout.setSpacing(6)
        card_layout.addStretch()

        scroll.setWidget(card_container)
        return scroll, card_container, card_layout

    def _add_file_dialog(self) -> None:
        path: str
        path, _ = QFileDialog.getOpenFileName(
            self, tr("notes.dialog.add_title"), "", tr("notes.dialog.add_filter")
        )
        if path:
            add_note(path)
            self._rebuild()

    def _rebuild(self) -> None:
        while self._card_layout.count() > 1:
            item = self._card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        notes = get_notes_list()
        if not notes:
            empty: QLabel = QLabel(tr("notes.empty"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _v: dict = _THEME_VARS["dark" if self._dark else "light"]
            empty.setStyleSheet(f"color: {_v['fg2']}; font-size: 11px; padding: 20px; background: transparent;")
            self._card_layout.insertWidget(0, empty)
            return
        for fp in notes:
            card: NoteCard = NoteCard(fp)
            card.clicked.connect(self._on_card_clicked)
            card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            card.customContextMenuRequested.connect(
                lambda pos, p=fp: self._show_card_menu(pos, p)
            )
            self._card_layout.insertWidget(self._card_layout.count() - 1, card)

    def _on_card_clicked(self, filepath: str) -> None:
        self.open_note.emit(filepath)

    def _show_card_menu(self, pos: QPoint, filepath: str) -> None:
        menu: QMenu = QMenu(self)

        act_add_badge: QAction = QAction(tr("notes.context.add_badge"), self)
        act_add_badge.triggered.connect(lambda: self._add_badge_dialog(filepath))
        menu.addAction(act_add_badge)

        act_remove_badge: QMenu = QMenu(tr("notes.context.remove_badge"), self)
        assigned = get_assigned_badges(filepath)
        if assigned:
            for b in assigned:
                act: QAction = QAction(b["label"], self)
                act.triggered.connect(lambda _, l=b["label"]: self._remove_badge(filepath, l))
                act_remove_badge.addAction(act)
        else:
            act_remove_badge.setEnabled(False)
        menu.addMenu(act_remove_badge)

        menu.addSeparator()

        act_remove: QAction = QAction(tr("notes.context.remove_from_notes"), self)
        act_remove.triggered.connect(lambda: self._remove_note(filepath))
        menu.addAction(act_remove)

        menu.exec(self._card_container.mapToGlobal(pos))

    def _add_badge_dialog(self, filepath: str) -> None:
        dlg: BadgeSelectDialog = BadgeSelectDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            badge: dict | None = dlg.selected_badge()
            if badge:
                add_assigned_badge(filepath, badge)
                self._rebuild()

    def _remove_badge(self, filepath: str, label: str) -> None:
        remove_assigned_badge(filepath, label)
        self._rebuild()

    def _remove_note(self, filepath: str) -> None:
        remove_note(filepath)
        self._rebuild()

    def refresh(self) -> None:
        self._rebuild()
