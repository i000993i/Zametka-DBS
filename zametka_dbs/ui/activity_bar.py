from PyQt6.QtWidgets import QFrame, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QSize
from assets.icons import icon


class ActivityBar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("activity-bar")
        self.setFixedWidth(48)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(2)

        self._buttons = []
        self._current = None

    def add_button(self, icon_name: str, tooltip: str) -> QPushButton:
        btn = QPushButton()
        btn.setIcon(icon(icon_name))
        btn.setIconSize(QSize(20, 20))
        btn.setObjectName("activity-btn")
        btn.setFixedSize(48, 44)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        self.layout().addWidget(btn)
        self._buttons.append(btn)
        return btn

    def set_active(self, index: int):
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)

    def set_button_tooltip(self, index: int, tooltip: str):
        if 0 <= index < len(self._buttons):
            self._buttons[index].setToolTip(tooltip)

    def select(self, button: QPushButton):
        for b in self._buttons:
            b.setChecked(b is button)
