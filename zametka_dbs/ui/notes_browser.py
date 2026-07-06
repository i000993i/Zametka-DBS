import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QLabel, QMenu, QFileDialog, QDialog,
    QListWidget, QListWidgetItem, QDialogButtonBox, QLineEdit,
    QFrame
)
from PyQt6.QtGui import QAction, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF

from assets.icons import icon
from zametka_dbs.core.badges import (
    BADGE_CATEGORIES, get_notes_list, add_note, remove_note,
    detect_file_badges, get_assigned_badges, add_assigned_badge,
    remove_assigned_badge, ALL_BADGES, badge_style, badge_stylesheet
)


class _BadgeItemWidget(QWidget):
    def __init__(self, badge: dict):
        super().__init__()
        self._badge = badge
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(8)

        cat = QLabel(badge["category"])
        cat.setStyleSheet("color: #484f58; font-size: 9px; font-weight: 600;")
        cat.setFixedWidth(90)
        layout.addWidget(cat)

        bl = QLabel(badge["label"])
        bl.setStyleSheet(badge_stylesheet(badge, font_size="10px"))
        layout.addWidget(bl)
        if badge_style(badge) == "pill":
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {badge['color']}; font-size: 6px;")
            layout.insertWidget(1, dot)
        layout.addStretch()

    def badge(self) -> dict:
        return self._badge


class _BadgeSelectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Badge")
        self.setMinimumSize(420, 480)
        self.resize(480, 560)
        self.setStyleSheet("background-color: #0d1117; color: #c9d1d9;")
        layout = QVBoxLayout(self)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search badges by name or category...")
        self._search.textChanged.connect(self._filter)
        self._search.setStyleSheet(
            "background: #161b22; border: 1px solid #30363d; "
            "border-radius: 4px; padding: 5px 8px; color: #c9d1d9; font-size: 12px;"
        )
        layout.addWidget(self._search)

        count_lbl = QLabel(f"{len(ALL_BADGES)} badges in {len(BADGE_CATEGORIES)} categories")
        count_lbl.setStyleSheet("color: #484f58; font-size: 10px; padding: 2px 0;")
        layout.addWidget(count_lbl)

        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { background: #0d1117; border: none; color: #c9d1d9; }"
            "QListWidget::item { border-bottom: 1px solid #161b22; }"
            "QListWidget::item:selected { background: #1c2128; }"
            "QListWidget::item:hover { background: #161b22; }"
        )
        self._list.setSpacing(1)
        layout.addWidget(self._list)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.setStyleSheet("color: #c9d1d9; padding: 4px;")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._load_all()
        self._selected_label: str | None = None

    def _load_all(self, filter_text: str = ""):
        self._list.clear()
        ft = filter_text.lower()
        for b in ALL_BADGES:
            if ft and ft not in b["label"].lower() and ft not in b.get("category", "").lower():
                continue
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, b["label"])
            widget = _BadgeItemWidget(b)
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _filter(self, text: str):
        self._load_all(text)

    def selected_badge(self) -> dict | None:
        item = self._list.currentItem()
        if not item:
            return None
        label = item.data(Qt.ItemDataRole.UserRole)
        for b in ALL_BADGES:
            if b["label"] == label:
                return b
        return None


class _NoteCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self._filepath = filepath
        self.setObjectName("note-card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QFrame#note-card {
                background-color: #161b22;
                border: 1px solid #21262d;
                border-radius: 6px;
            }
            QFrame#note-card:hover {
                border-color: #30363d;
                background-color: #1c2128;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        name = os.path.basename(filepath) or filepath
        is_dir = os.path.isdir(filepath)

        row1 = QHBoxLayout()
        row1.setSpacing(6)

        ico_label = QLabel()
        if is_dir:
            pix = icon("folder").pixmap(14, 14)
        else:
            ext = os.path.splitext(filepath)[1].lower()
            if ext in (".md", ".mdx", ".txt"):
                pix = icon("file-text").pixmap(14, 14)
            else:
                pix = icon("file").pixmap(14, 14)
        ico_label.setPixmap(pix)
        ico_label.setFixedWidth(18)
        row1.addWidget(ico_label)

        name_label = QLabel(name)
        name_label.setStyleSheet("color: #f0f6fc; font-size: 12px; font-weight: 600;")
        name_label.setWordWrap(False)
        row1.addWidget(name_label, 1)
        layout.addLayout(row1)

        badges = []
        badges.extend(detect_file_badges(filepath))
        badges.extend(get_assigned_badges(filepath))

        if badges:
            row2 = QHBoxLayout()
            row2.setSpacing(4)
            row2.setContentsMargins(0, 0, 0, 0)
            for b in badges[:6]:
                bl = QLabel(b["label"])
                bl.setStyleSheet(badge_stylesheet(b, font_size="9px"))
                row2.addWidget(bl)
            if len(badges) > 6:
                more = QLabel(f"+{len(badges) - 6}")
                more.setStyleSheet("color: #8b949e; font-size: 9px;")
                row2.addWidget(more)
            row2.addStretch()
            layout.addLayout(row2)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._filepath)
        super().mousePressEvent(event)

    def filepath(self) -> str:
        return self._filepath


class NotesBrowser(QWidget):
    open_note = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("notes-browser")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("notes-header")
        header.setFixedHeight(34)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 6, 0)
        header_layout.setSpacing(4)

        header_icon = QLabel()
        header_icon.setPixmap(icon("layout").pixmap(12, 12))
        header_icon.setFixedWidth(16)
        header_layout.addWidget(header_icon)

        header_label = QLabel("NOTES")
        header_label.setObjectName("notes-label")
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        self._add_file_btn = QPushButton(icon("file"), " Add")
        self._add_file_btn.setObjectName("notes-add-btn")
        self._add_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_file_btn.setToolTip("Add file to Notes")
        self._add_file_btn.clicked.connect(self._add_file_dialog)
        header_layout.addWidget(self._add_file_btn)



        layout.addWidget(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("notes-scroll")


        self._card_container = QWidget()
        self._card_container.setObjectName("card-container")
        self._card_layout = QVBoxLayout(self._card_container)
        self._card_layout.setContentsMargins(6, 6, 6, 6)
        self._card_layout.setSpacing(6)
        self._card_layout.addStretch()

        self._scroll.setWidget(self._card_container)
        layout.addWidget(self._scroll)

        self._rebuild()

    def _add_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Add note", "", "All Files (*.*)"
        )
        if path:
            add_note(path)
            self._rebuild()

    def _rebuild(self):
        while self._card_layout.count() > 1:
            item = self._card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        notes = get_notes_list()
        if not notes:
            empty = QLabel("No notes yet.\nClick + to add files.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #484f58; font-size: 11px; padding: 20px; background: transparent;")
            self._card_layout.insertWidget(0, empty)
            return
        for fp in notes:
            card = _NoteCard(fp)
            card.clicked.connect(self._on_card_clicked)
            card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            card.customContextMenuRequested.connect(
                lambda pos, p=fp: self._show_card_menu(pos, p)
            )
            self._card_layout.insertWidget(self._card_layout.count() - 1, card)

    def _on_card_clicked(self, filepath: str):
        self.open_note.emit(filepath)

    def _show_card_menu(self, pos, filepath: str):
        menu = QMenu(self)

        act_add_badge = QAction("Add badge...", self)
        act_add_badge.triggered.connect(lambda: self._add_badge_dialog(filepath))
        menu.addAction(act_add_badge)

        act_remove_badge = QMenu("Remove badge", self)
        assigned = get_assigned_badges(filepath)
        if assigned:
            for b in assigned:
                act = QAction(b["label"], self)
                act.triggered.connect(lambda _, l=b["label"]: self._remove_badge(filepath, l))
                act_remove_badge.addAction(act)
        else:
            act_remove_badge.setEnabled(False)
        menu.addMenu(act_remove_badge)

        menu.addSeparator()

        act_remove = QAction("Remove from Notes", self)
        act_remove.triggered.connect(lambda: self._remove_note(filepath))
        menu.addAction(act_remove)

        menu.exec(self._card_container.mapToGlobal(pos))

    def _add_badge_dialog(self, filepath: str):
        dlg = _BadgeSelectDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            badge = dlg.selected_badge()
            if badge:
                add_assigned_badge(filepath, badge)
                self._rebuild()

    def _remove_badge(self, filepath: str, label: str):
        remove_assigned_badge(filepath, label)
        self._rebuild()

    def _remove_note(self, filepath: str):
        remove_note(filepath)
        self._rebuild()

    def refresh(self):
        self._rebuild()

    def _styles(self) -> str:
        return """
            QWidget#notes-header {
                border-bottom: 1px solid #1a1a1a;
                background-color: #0a0a0a;
            }
            QLabel#notes-label {
                color: #808080;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
            }
            QPushButton#notes-add-btn {
                background-color: #161b22;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 3px;
                font-size: 10px;
                font-weight: 600;
                padding: 2px 6px;
            }
            QPushButton#notes-add-btn:hover {
                background-color: #1c2128;
                border-color: #8b949e;
                color: #f0f6fc;
            }
        """
