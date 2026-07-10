from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDialog,
    QListWidget, QListWidgetItem, QDialogButtonBox, QLineEdit,
)
from PyQt6.QtCore import Qt

from zametka_dbs.core.config import get_config
from zametka_dbs.core.i18n import tr
from zametka_dbs.ui.styles import _THEME_VARS
from zametka_dbs.core.badges import (
    BADGE_CATEGORIES, ALL_BADGES, badge_stylesheet, badge_style,
)


class BadgeItemWidget(QWidget):
    def __init__(self, badge: dict, fg2: str = "#808080") -> None:
        super().__init__()
        self._badge: dict = badge
        layout: QHBoxLayout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(8)

        cat: QLabel = QLabel(badge["category"])
        cat.setStyleSheet(f"color: {fg2}; font-size: 9px; font-weight: 600;")
        cat.setFixedWidth(90)
        layout.addWidget(cat)

        bl: QLabel = QLabel(badge["label"])
        bl.setStyleSheet(badge_stylesheet(badge, font_size="10px"))
        layout.addWidget(bl)
        if badge_style(badge) == "pill":
            dot: QLabel = QLabel("\u25cf")
            dot.setStyleSheet(f"color: {badge['color']}; font-size: 6px;")
            layout.insertWidget(1, dot)
        layout.addStretch()

    def badge(self) -> dict:
        return self._badge


class BadgeSelectDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("notes.dialog.add_badge_title"))
        self.setMinimumSize(420, 480)
        self.resize(480, 560)
        _current_theme: str = get_config().get("theme", "dark")
        _v: dict = _THEME_VARS[_current_theme]
        self.setStyleSheet(f'background-color: {_v["bg1"]}; color: {_v["fg0"]};')
        layout: QVBoxLayout = QVBoxLayout(self)

        self._search = self._build_search(_v)
        layout.addWidget(self._search)

        count_lbl: QLabel = QLabel(f"{len(ALL_BADGES)} badges in {len(BADGE_CATEGORIES)} categories")
        count_lbl.setStyleSheet(f"color: {_v['fg2']}; font-size: 10px; padding: 2px 0;")
        layout.addWidget(count_lbl)

        self._list = self._build_list(_v)
        layout.addWidget(self._list)

        btn_box: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.setStyleSheet(f"color: {_v['fg0']}; padding: 4px;")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._load_all()
        self._selected_label: str | None = None

    def _build_search(self, v: dict) -> QLineEdit:
        search: QLineEdit = QLineEdit()
        search.setPlaceholderText(tr("notes.search_badges_placeholder"))
        search.textChanged.connect(self._filter)
        search.setStyleSheet(
            f"background: {v['bg2']}; border: 1px solid {v['border']}; "
            f"border-radius: 4px; padding: 5px 8px; color: {v['fg0']}; font-size: 12px;"
        )
        return search

    def _build_list(self, v: dict) -> QListWidget:
        lst: QListWidget = QListWidget()
        lst.setStyleSheet(
            f"QListWidget {{ background: {v['bg0']}; border: none; color: {v['fg0']}; }}"
            f"QListWidget::item {{ border-bottom: 1px solid {v['border']}; }}"
            f"QListWidget::item:selected {{ background: {v['sel_bg']}; }}"
            f"QListWidget::item:hover {{ background: {v['bg2']}; }}"
        )
        lst.setSpacing(1)
        return lst

    def _load_all(self, filter_text: str = "") -> None:
        self._list.clear()
        ft: str = filter_text.lower()
        for b in ALL_BADGES:
            if ft and ft not in b["label"].lower() and ft not in b.get("category", "").lower():
                continue
            item: QListWidgetItem = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, b["label"])
            _v = _THEME_VARS[get_config().get("theme", "dark")]
            widget: BadgeItemWidget = BadgeItemWidget(b, fg2=_v["fg2"])
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _filter(self, text: str) -> None:
        self._load_all(text)

    def selected_badge(self) -> dict | None:
        item: QListWidgetItem | None = self._list.currentItem()
        if not item:
            return None
        label: str = item.data(Qt.ItemDataRole.UserRole)
        for b in ALL_BADGES:
            if b["label"] == label:
                return b
        return None
