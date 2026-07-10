from __future__ import annotations

import os

from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSpinBox, QSlider, QComboBox, QSizePolicy, QMenu,
    QApplication,
)
from PyQt6.QtCore import Qt, QSize, QTimer, QObject, QEvent, QPoint
from PyQt6.QtGui import QPixmap, QKeyEvent, QImage, QAction, QResizeEvent
from assets.icons import icon
from zametka_dbs.core.config import get_config
from zametka_dbs.ui.styles import _THEME_VARS


_FITZ = None

def _get_fitz() -> Any | None:
    global _FITZ
    if _FITZ is None:
        try:
            import fitz as _fitz_mod
            _FITZ = _fitz_mod
        except ImportError:
            _FITZ = False
    return _FITZ if _FITZ else None


ZOOM_PRESETS: list[float] = [0.25, 0.33, 0.5, 0.67, 0.75, 0.9, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
BASE_DPI: int = 72
RENDER_DPI: int = 150
VISIBLE_BUFFER: int = 3

VIEWER_EXTS: set[str] = {
    ".pdf", ".xps", ".epub", ".cbz", ".cbr", ".fb2",
}


class DocumentViewer(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._doc = None
        self._filepath = ""
        self._current_page = 0
        self._scale = 1.0
        self._page_count = 0
        self._page_rects: list = []
        self._loaded = False

        self._cache: dict[int, QPixmap] = {}
        self._error_pages: dict[int, str] = {}
        self._render_queue: list[int] = []
        self._render_pending = set()
        self._rebuild_queued = False

        self._batch_timer = QTimer()
        self._batch_timer.setSingleShot(True)
        self._batch_timer.timeout.connect(self._render_next_batch)

        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._flush_rebuild)

        self._init_ui()

    @staticmethod
    def can_open(path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in VIEWER_EXTS

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = self._build_toolbar()
        layout.addWidget(toolbar)

        self._build_scroll_area(layout)

        self._page_widgets: list[_PageWidget] = []
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._scroll.verticalScrollBar().valueChanged.connect(self._on_scrolled)

    def _build_toolbar(self) -> QWidget:
        toolbar = QWidget()
        toolbar.setObjectName("pdf-toolbar")
        toolbar.setFixedHeight(40)
        tbar = QHBoxLayout(toolbar)
        tbar.setContentsMargins(8, 0, 8, 0)
        tbar.setSpacing(4)

        self._page_spinner = QSpinBox()
        self._page_spinner.setObjectName("pdf-page-spinner")
        self._page_spinner.setMinimum(1)
        self._page_spinner.setMaximum(1)
        self._page_spinner.setFixedWidth(60)
        self._page_spinner.setFixedHeight(24)
        self._page_spinner.valueChanged.connect(self._go_to_page)
        tbar.addWidget(self._page_spinner)

        self._page_count_label = QLabel("of 1")
        self._page_count_label.setObjectName("pdf-page-count")
        tbar.addWidget(self._page_count_label)

        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setObjectName("pdf-copy-btn")
        self._copy_btn.setFixedHeight(24)
        self._copy_btn.setToolTip("Copy page text")
        self._copy_btn.clicked.connect(lambda: self._copy_page_text(self._current_page))
        tbar.addWidget(self._copy_btn)

        tbar.addStretch()

        self._fit_width_btn = QPushButton("Fit Width")
        self._fit_width_btn.setObjectName("pdf-fit-btn")
        self._fit_width_btn.setFixedHeight(24)
        self._fit_width_btn.setToolTip("Fit to page width (Ctrl+W)")
        self._fit_width_btn.clicked.connect(self._fit_to_width)
        tbar.addWidget(self._fit_width_btn)

        self._fit_page_btn = QPushButton("Fit Page")
        self._fit_page_btn.setObjectName("pdf-fit-btn")
        self._fit_page_btn.setFixedHeight(24)
        self._fit_page_btn.setToolTip("Fit entire page (Ctrl+P)")
        self._fit_page_btn.clicked.connect(self._fit_to_page)
        tbar.addWidget(self._fit_page_btn)

        tbar.addWidget(QLabel("|"))

        self._zoom_out_btn = QPushButton()
        self._zoom_out_btn.setIcon(icon("search"))
        self._zoom_out_btn.setIconSize(QSize(14, 14))
        self._zoom_out_btn.setObjectName("icon-btn")
        self._zoom_out_btn.setFixedSize(22, 22)
        self._zoom_out_btn.setToolTip("Zoom Out (Ctrl+-)")
        self._zoom_out_btn.clicked.connect(self._zoom_out)
        tbar.addWidget(self._zoom_out_btn)

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setObjectName("pdf-zoom-slider")
        self._zoom_slider.setRange(10, 500)
        self._zoom_slider.setValue(100)
        self._zoom_slider.setFixedWidth(120)
        self._zoom_slider.setToolTip("Zoom level")
        self._zoom_slider.valueChanged.connect(self._on_slider_zoom)
        tbar.addWidget(self._zoom_slider)

        self._zoom_combo = QComboBox()
        self._zoom_combo.setObjectName("pdf-zoom-combo")
        self._zoom_combo.setEditable(True)
        self._zoom_combo.setFixedWidth(70)
        self._zoom_combo.setFixedHeight(24)
        for p in ZOOM_PRESETS:
            self._zoom_combo.addItem(f"{int(p * 100)}%")
        self._zoom_combo.setCurrentText("100%")
        self._zoom_combo.currentTextChanged.connect(self._on_combo_zoom)
        tbar.addWidget(self._zoom_combo)

        self._zoom_in_btn = QPushButton()
        self._zoom_in_btn.setIcon(icon("search"))
        self._zoom_in_btn.setIconSize(QSize(14, 14))
        self._zoom_in_btn.setObjectName("icon-btn")
        self._zoom_in_btn.setFixedSize(22, 22)
        self._zoom_in_btn.setToolTip("Zoom In (Ctrl++)")
        self._zoom_in_btn.clicked.connect(self._zoom_in)
        tbar.addWidget(self._zoom_in_btn)

        return toolbar

    def _build_scroll_area(self, layout: QVBoxLayout) -> None:
        self._scroll = QScrollArea()
        self._scroll.setObjectName("pdf-scroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        theme = get_config().get("theme", "dark")
        _v = _THEME_VARS[theme]
        self._scroll.setStyleSheet(f"QScrollArea {{ background-color: {_v['bg1']}; border: none; }}")

        self._container = QWidget()
        self._container.setObjectName("pdf-container")
        self._container.setStyleSheet(f"background-color: {_v['bg1']};")
        self._page_layout = QVBoxLayout(self._container)
        self._page_layout.setContentsMargins(20, 10, 20, 10)
        self._page_layout.setSpacing(12)
        self._page_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._no_doc_label = QLabel(
            "Document viewer not available (install PyMuPDF)" if _get_fitz() is None
            else "Open a PDF or document file"
        )
        self._no_doc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_doc_label.setStyleSheet("font-size: 14px; padding: 40px;")
        self._page_layout.addWidget(self._no_doc_label)

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll, 1)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._scroll.viewport() and event.type() == event.Type.Wheel:
            we = event
            if we.modifiers() == Qt.KeyboardModifier.ControlModifier:
                if we.angleDelta().y() > 0:
                    self._zoom_in()
                else:
                    self._zoom_out()
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_PageDown:
            self._next_page()
        elif key == Qt.Key.Key_PageUp:
            self._prev_page()
        elif key == Qt.Key.Key_Home:
            self._go_to_page_val(1)
        elif key == Qt.Key.Key_End:
            self._go_to_page_val(self._page_count)
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            self._prev_page()
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_Down):
            self._next_page()
        elif key == Qt.Key.Key_Equal and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._zoom_in()
        elif key == Qt.Key.Key_Minus and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._zoom_out()
        elif key == Qt.Key.Key_0 and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._scale = 1.0
            self._update_zoom_controls()
            self._rebuild()
        elif key == Qt.Key.Key_W and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._fit_to_width()
        elif key == Qt.Key.Key_P and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._fit_to_page()
        else:
            super().keyPressEvent(event)

    def load(self, filepath: str) -> None:
        if _get_fitz() is None:
            self._show_error("PyMuPDF not installed")
            return
        if not os.path.isfile(filepath):
            self._show_error(f"File not found: {filepath}")
            return
        self._close_doc()
        self._filepath = filepath
        self._current_page = 0
        self._scale = 1.0
        self._loaded = False
        self._cache.clear()
        self._error_pages.clear()
        self._render_pending.clear()
        self._render_queue.clear()
        self._rebuild_queued = False
        self._update_zoom_controls()
        self._no_doc_label.setText("Loading...")
        self._no_doc_label.setVisible(True)
        self._clear_pages()

        try:
            self._doc = _get_fitz().open(filepath)
            self._page_count = self._doc.page_count
            self._page_rects = [self._doc[i].rect for i in range(self._page_count)]
            self._loaded = True
            self._build_placeholders()
            self._queue_rebuild()
        except Exception as e:
            self._show_error(f"Open failed: {e}")

    def clear(self) -> None:
        self._close_doc()
        self._show_error("No document loaded")

    def _close_doc(self) -> None:
        self._filepath = ""
        self._loaded = False
        self._cache.clear()
        self._error_pages.clear()
        self._render_pending.clear()
        self._render_queue.clear()
        if self._doc:
            try:
                self._doc.close()
            except Exception:
                pass
            self._doc = None

    def _show_error(self, msg: str) -> None:
        self._page_count_label.setText("of 0")
        self._page_spinner.blockSignals(True)
        self._page_spinner.setMaximum(1)
        self._page_spinner.setValue(1)
        self._page_spinner.blockSignals(False)
        self._clear_pages()
        self._no_doc_label.setText(msg)
        self._no_doc_label.setVisible(True)

    def _clear_pages(self) -> None:
        for w in self._page_widgets:
            self._page_layout.removeWidget(w)
            w.deleteLater()
        self._page_widgets.clear()

    def _build_placeholders(self) -> None:
        if self._page_count == 0:
            return
        self._no_doc_label.setVisible(False)
        self._clear_pages()

        self._page_count_label.setText(f"of {self._page_count}")
        self._page_spinner.blockSignals(True)
        self._page_spinner.setMaximum(self._page_count)
        self._page_spinner.setValue(1)
        self._page_spinner.blockSignals(False)

        for i in range(self._page_count):
            pw = _PageWidget(i + 1, doc_viewer=self)
            self._page_layout.addWidget(pw, 0, Qt.AlignmentFlag.AlignCenter)
            self._page_widgets.append(pw)

        self._scroll.verticalScrollBar().setValue(0)

    def _update_widget(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._page_widgets):
            return
        pw = self._page_widgets[idx]
        if idx in self._cache:
            pw.set_pixmap(self._cache[idx])
        elif idx in self._error_pages:
            pw.show_error(self._error_pages[idx])
        else:
            pw.show_loading()

    def _render_page(self, idx: int) -> None:
        if idx in self._cache or idx in self._error_pages:
            return
        if idx < 0 or idx >= self._page_count:
            return

        self._render_page_local(idx)

    def _render_page_local(self, idx: int) -> None:
        if not self._doc:
            self._error_pages[idx] = "no document"
            self._update_widget(idx)
            return
        rect = self._page_rects[idx]
        if rect.width <= 0 or rect.height <= 0:
            self._error_pages[idx] = "empty page"
            self._update_widget(idx)
            return

        dpi = int(RENDER_DPI * self._scale)
        zoom = dpi / BASE_DPI

        for attempt in (1.0, 0.5, 0.25):
            try:
                mat2 = _get_fitz().Matrix(zoom * attempt, zoom * attempt)
                pix = self._doc[idx].get_pixmap(matrix=mat2)
                if pix is None or pix.samples is None or len(pix.samples) == 0:
                    continue
                img = QImage(
                    pix.samples, pix.width, pix.height,
                    pix.stride, QImage.Format.Format_RGB888
                )
                if img.isNull():
                    continue
                qp = QPixmap.fromImage(img)
                if qp.isNull():
                    continue
                self._cache[idx] = qp
                self._error_pages.pop(idx, None)
                self._update_widget(idx)
                return
            except Exception:
                continue

        self._error_pages[idx] = "render error"
        self._update_widget(idx)

    def _copy_page_text(self, idx: int) -> None:
        if self._doc is None:
            return
        try:
            text = self._doc[idx].get_text("text")
            if text:
                QApplication.clipboard().setText(text)
                self._page_widgets[idx]._page_label.setText("Page text copied")
                QTimer.singleShot(2000, lambda i=idx: self._page_widgets[i]._page_label.setText(f"Page {i + 1}"))
        except Exception:
            pass

    def _copy_all_text(self) -> None:
        if self._doc is None or self._page_count == 0:
            return
        try:
            parts = []
            for i in range(self._page_count):
                text = self._doc[i].get_text("text")
                if text:
                    parts.append(f"--- Page {i + 1} ---\n{text}")
            if parts:
                QApplication.clipboard().setText("\n\n".join(parts))
        except Exception:
            pass

    def _get_visible_range(self) -> tuple[int, int]:
        if not self._page_widgets:
            return (0, 0)
        sb = self._scroll.verticalScrollBar()
        scroll_top = sb.value()
        vp_height = self._scroll.viewport().height()
        visible_bot = scroll_top + vp_height

        first = 0
        for i, pw in enumerate(self._page_widgets):
            if pw.y() + pw.height() >= scroll_top:
                first = i
                break
        last = len(self._page_widgets) - 1
        for i in range(len(self._page_widgets) - 1, -1, -1):
            if self._page_widgets[i].y() <= visible_bot:
                last = i
                break
        return (max(0, first - VISIBLE_BUFFER),
                min(len(self._page_widgets) - 1, last + VISIBLE_BUFFER))

    def _build_render_queue(self) -> list[int]:
        visible = self._get_visible_range()
        needed = set(range(visible[0], visible[1] + 1))
        for i in range(max(0, visible[0] - 6), visible[0]):
            needed.add(i)
        for i in range(visible[1] + 1, min(self._page_count, visible[1] + 6)):
            needed.add(i)
        return sorted(
            i for i in needed
            if i not in self._cache and i not in self._error_pages and i not in self._render_pending
        )

    def _queue_rebuild(self) -> None:
        if not self._loaded or self._page_count == 0:
            return
        self._rebuild_queued = True
        if not self._batch_timer.isActive():
            self._batch_timer.start(5)

    def _flush_rebuild(self) -> None:
        self._rebuild_queued = False
        self._queue_rebuild()

    def _render_next_batch(self) -> None:
        if self._rebuild_queued:
            self._render_queue = self._build_render_queue()
            self._rebuild_queued = False
            self._evict_cache()

        if not self._render_queue:
            return

        idx = self._render_queue.pop(0)
        self._render_pending.add(idx)
        self._render_page(idx)
        self._render_pending.discard(idx)

        if self._render_queue:
            self._batch_timer.start(5)

    def _evict_cache(self) -> None:
        visible = self._get_visible_range()
        keep = set(range(max(0, visible[0] - 8), min(self._page_count, visible[1] + 8)))
        for k in list(self._cache):
            if k not in keep:
                del self._cache[k]

    def _rebuild(self) -> None:
        self._cache.clear()
        self._error_pages.clear()
        self._render_pending.clear()
        self._render_queue.clear()
        for pw in self._page_widgets:
            pw.show_loading()
        self._queue_rebuild()

    def _on_scrolled(self, _value: int = 0) -> None:
        if self._loaded and self._page_widgets:
            self._queue_rebuild()

    def _go_to_page(self, page: int) -> None:
        idx = page - 1
        if 0 <= idx < len(self._page_widgets):
            self._current_page = idx
            sb = self._scroll.verticalScrollBar()
            sb.setValue(max(0, self._page_widgets[idx].y() - 10))
            self._queue_rebuild()

    def _go_to_page_val(self, page: int) -> None:
        page = max(1, min(page, self._page_count))
        self._page_spinner.blockSignals(True)
        self._page_spinner.setValue(page)
        self._page_spinner.blockSignals(False)
        self._go_to_page(page)

    def _next_page(self) -> None:
        self._go_to_page_val(self._page_spinner.value() + 1)

    def _prev_page(self) -> None:
        self._go_to_page_val(self._page_spinner.value() - 1)

    def _zoom_in(self) -> None:
        idx = self._closest_zoom_index()
        idx = min(idx + 1, len(ZOOM_PRESETS) - 1)
        self._scale = ZOOM_PRESETS[idx]
        self._apply_zoom()

    def _zoom_out(self) -> None:
        idx = self._closest_zoom_index()
        idx = max(idx - 1, 0)
        self._scale = ZOOM_PRESETS[idx]
        self._apply_zoom()

    def _closest_zoom_index(self) -> int:
        best = 0
        for i, p in enumerate(ZOOM_PRESETS):
            if abs(p - self._scale) < abs(ZOOM_PRESETS[best] - self._scale):
                best = i
        return best

    def _on_slider_zoom(self, val: int) -> None:
        self._scale = val / 100.0
        self._zoom_combo.blockSignals(True)
        self._zoom_combo.setCurrentText(f"{val}%")
        self._zoom_combo.blockSignals(False)
        self._apply_zoom()

    def _on_combo_zoom(self, text: str) -> None:
        try:
            pct = int(text.replace("%", "").strip())
            pct = max(10, min(500, pct))
            self._scale = pct / 100.0
            self._zoom_slider.blockSignals(True)
            self._zoom_slider.setValue(pct)
            self._zoom_slider.blockSignals(False)
            self._apply_zoom()
        except ValueError:
            pass

    def _apply_zoom(self) -> None:
        self._update_zoom_controls()
        self._rebuild()

    def _update_zoom_controls(self) -> None:
        pct = int(self._scale * 100)
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(pct)
        self._zoom_slider.blockSignals(False)
        self._zoom_combo.blockSignals(True)
        self._zoom_combo.setCurrentText(f"{pct}%")
        self._zoom_combo.blockSignals(False)

    def _fit_to_width(self) -> None:
        if self._page_count == 0 or not self._page_rects:
            return
        sw = self._scroll.viewport().width() - 40
        pw = self._page_rects[0].width
        if pw > 0:
            self._scale = max(0.1, sw / pw)
            self._apply_zoom()

    def _fit_to_page(self) -> None:
        if self._page_count == 0 or not self._page_rects:
            return
        sw = self._scroll.viewport().width() - 40
        sh = self._scroll.viewport().height() - 60
        pp = self._page_rects[0]
        if pp.width > 0 and pp.height > 0:
            scale_w = sw / pp.width
            scale_h = sh / pp.height
            self._scale = max(0.1, min(scale_w, scale_h))
            self._apply_zoom()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._loaded and self._page_widgets:
            self._queue_rebuild()


class _PageWidget(QWidget):
    _page_num: int
    _doc_viewer: DocumentViewer | None
    def __init__(self, page_num: int, doc_viewer: DocumentViewer | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page_num = page_num
        self._doc_viewer = doc_viewer
        self.setObjectName("pdf-page-widget")
        self.setStyleSheet(
            "background-color: white;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._label = QLabel()
        self._label.setObjectName("pdf-page-label")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setCursor(Qt.CursorShape.OpenHandCursor)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._label.setMinimumSize(QSize(100, 40))
        self._label.setStyleSheet("background-color: white;")
        self._label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._label.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._label)

        self._page_label = QLabel(f"Page {page_num}")
        self._page_label.setObjectName("pdf-page-number")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setStyleSheet("background: transparent; color: #666;")
        layout.addWidget(self._page_label)

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self._label)
        act_copy = QAction("Copy page text", self._label)
        act_copy.triggered.connect(self._copy_text)
        menu.addAction(act_copy)
        act_copy_all = QAction("Copy all text", self._label)
        act_copy_all.triggered.connect(self._copy_all_text)
        menu.addAction(act_copy_all)
        menu.exec(self._label.mapToGlobal(pos))

    def _copy_text(self) -> None:
        if self._doc_viewer:
            self._doc_viewer._copy_page_text(self._page_num - 1)

    def _copy_all_text(self) -> None:
        if self._doc_viewer:
            self._doc_viewer._copy_all_text()

    def set_pixmap(self, pix: QPixmap) -> None:
        self._label.setText("")
        self._label.setPixmap(pix)
        self._label.setMinimumSize(QSize(0, 0))

    def show_loading(self) -> None:
        self._label.setText("Loading...")
        self._label.setPixmap(QPixmap())

    def show_error(self, msg: str) -> None:
        self._label.setText(f"[{msg}]")
        self._label.setPixmap(QPixmap())
