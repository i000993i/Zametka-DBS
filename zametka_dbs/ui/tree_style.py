from __future__ import annotations

from PyQt6.QtWidgets import QProxyStyle, QStyle, QStyleOption, QWidget
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QPointF

from zametka_dbs.ui.styles import _THEME_VARS


class TreeBranchStyle(QProxyStyle):
    def drawPrimitive(
        self,
        element: QStyle.PrimitiveElement,
        option: QStyleOption,
        painter: QPainter,
        widget: QWidget | None,
    ) -> None:
        if element == QStyle.PrimitiveElement.PE_IndicatorBranch:
            self._draw_branch(element, option, painter, widget)
            return
        super().drawPrimitive(element, option, painter, widget)

    def _draw_branch(
        self,
        element: QStyle.PrimitiveElement,
        option: QStyleOption,
        painter: QPainter,
        widget: QWidget | None,
    ) -> None:
        rect = option.rect
        x = rect.x() + rect.width() // 2
        y_top = rect.top()
        y_bot = rect.bottom()
        y_mid = rect.center().y()
        has_sibling = bool(option.state & QStyle.StateFlag.State_Sibling)
        has_children = bool(option.state & QStyle.StateFlag.State_Children)

        painter.save()
        from zametka_dbs.core.config import get_config
        dark = getattr(widget, "_dark", None)
        if dark is None:
            dark = get_config().get("theme", "dark") == "dark"
        v = _THEME_VARS["dark" if dark else "light"]
        painter.setPen(QPen(QColor(v["border2"]), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        self._draw_branch_lines(painter, x, y_top, y_mid, y_bot, rect.right(), has_sibling)

        if has_children:
            self._draw_expand_arrow(painter, x, y_mid, option, dark)

        painter.restore()

    @staticmethod
    def _draw_branch_lines(painter: QPainter, x: int, y_top: int, y_mid: int, y_bot: int, right: int, has_sibling: bool):
        if has_sibling:
            painter.drawLine(x, y_top, x, y_bot)
        else:
            painter.drawLine(x, y_top, x, y_mid)
        painter.drawLine(x, y_mid, right, y_mid)

    @staticmethod
    def _draw_expand_arrow(painter: QPainter, x: int, y_mid: int, option: QStyleOption, dark: bool):
        cx, cy = float(x), float(y_mid)
        h = 4.0
        w = 4.0
        if option.state & QStyle.StateFlag.State_Open:
            tri = [QPointF(cx, cy - h), QPointF(cx - w, cy + h), QPointF(cx + w, cy + h)]
        else:
            tri = [QPointF(cx - w, cy - h), QPointF(cx - w, cy + h), QPointF(cx + w, cy)]
        painter.setPen(Qt.PenStyle.NoPen)
        v = _THEME_VARS["dark" if dark else "light"]
        painter.setBrush(QColor(v["fg1"]))
        painter.drawPolygon(*tri)
