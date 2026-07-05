import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSpinBox,
)
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QPixmap

try:
    from PyQt6.QtPdf import QPdfDocument, QPdfDocumentRenderOptions
except ImportError:
    QPdfDocument = None
    QPdfDocumentRenderOptions = None

from assets.icons import icon


class PdfViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._document = QPdfDocument(self)
        self._document.statusChanged.connect(self._on_status_changed)
        self._current_page = 0
        self._scale = 1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QWidget()
        toolbar.setObjectName("pdf-toolbar")
        toolbar.setFixedHeight(36)
        tbar = QHBoxLayout(toolbar)
        tbar.setContentsMargins(8, 0, 8, 0)
        tbar.setSpacing(4)

        self._page_display = QLabel("0 / 0")
        self._page_display.setObjectName("pdf-page-label")
        tbar.addWidget(self._page_display)

        self._page_spinner = QSpinBox()
        self._page_spinner.setObjectName("pdf-page-spinner")
        self._page_spinner.setMinimum(1)
        self._page_spinner.setMaximum(1)
        self._page_spinner.setFixedWidth(60)
        self._page_spinner.setFixedHeight(24)
        self._page_spinner.valueChanged.connect(self._go_to_page)
        tbar.addWidget(self._page_spinner)

        tbar.addStretch()

        self._zoom_out = QPushButton()
        self._zoom_out.setIcon(icon("search"))
        self._zoom_out.setIconSize(QSize(14, 14))
        self._zoom_out.setObjectName("icon-btn")
        self._zoom_out.setFixedSize(22, 22)
        self._zoom_out.setToolTip("Zoom Out")
        self._zoom_out.clicked.connect(lambda: self._zoom(-0.1))
        tbar.addWidget(self._zoom_out)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setObjectName("pdf-zoom-label")
        tbar.addWidget(self._zoom_label)

        self._zoom_in = QPushButton()
        self._zoom_in.setIcon(icon("search"))
        self._zoom_in.setIconSize(QSize(14, 14))
        self._zoom_in.setObjectName("icon-btn")
        self._zoom_in.setFixedSize(22, 22)
        self._zoom_in.setToolTip("Zoom In")
        self._zoom_in.clicked.connect(lambda: self._zoom(0.1))
        tbar.addWidget(self._zoom_in)

        layout.addWidget(toolbar)

        # Scroll area with page labels
        self._scroll = QScrollArea()
        self._scroll.setObjectName("pdf-scroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._container = QWidget()
        self._container.setObjectName("pdf-container")
        self._page_layout = QVBoxLayout(self._container)
        self._page_layout.setContentsMargins(20, 10, 20, 10)
        self._page_layout.setSpacing(8)
        self._page_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._page_labels: list[QLabel] = []
        self._no_pdf_label = QLabel("No PDF loaded")
        self._no_pdf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_pdf_label.setStyleSheet("font-size: 14px; padding: 40px;")
        self._page_layout.addWidget(self._no_pdf_label)

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll, 1)

    def load(self, filepath: str):
        if not os.path.isfile(filepath):
            return
        self._document.close()
        self._document.load(filepath)
        self._current_page = 0
        self._scale = 1.0

    def clear(self):
        self._document.close()
        self._no_pdf_label.setVisible(True)
        self._page_display.setText("0 / 0")
        self._page_spinner.blockSignals(True)
        self._page_spinner.setMaximum(1)
        self._page_spinner.setValue(1)
        self._page_spinner.blockSignals(False)
        self._clear_pages()

    def _on_status_changed(self, status):
        if status == QPdfDocument.Status.Ready:
            self._render_all_pages()
        elif status == QPdfDocument.Status.Error:
            self._no_pdf_label.setText("Error loading PDF")
            self._no_pdf_label.setVisible(True)

    def _clear_pages(self):
        for lbl in self._page_labels:
            self._page_layout.removeWidget(lbl)
            lbl.deleteLater()
        self._page_labels.clear()

    def _render_all_pages(self):
        count = self._document.pageCount()
        if count == 0:
            return

        self._no_pdf_label.setVisible(False)
        self._clear_pages()

        self._page_display.setText(f"1 / {count}")
        self._page_spinner.blockSignals(True)
        self._page_spinner.setMaximum(count)
        self._page_spinner.setValue(1)
        self._page_spinner.blockSignals(False)

        for i in range(count):
            page_point = self._document.pagePointSize(i)
            dpr = self.devicePixelRatio()
            target_w = int(page_point.width() * self._scale * dpr)
            target_h = int(page_point.height() * self._scale * dpr)
            opts = QPdfDocumentRenderOptions()
            img = self._document.render(i, QSize(target_w, target_h), opts)

            pix = QPixmap.fromImage(img)

            page_widget = QWidget()
            page_widget.setObjectName("pdf-page-widget")
            pw_layout = QVBoxLayout(page_widget)
            pw_layout.setContentsMargins(0, 0, 0, 0)
            pw_layout.setSpacing(0)

            label = QLabel()
            label.setPixmap(pix)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            page_num = QLabel(f"Page {i + 1}")
            page_num.setObjectName("pdf-page-number")
            page_num.setAlignment(Qt.AlignmentFlag.AlignCenter)

            pw_layout.addWidget(label)
            pw_layout.addWidget(page_num)
            self._page_layout.addWidget(page_widget, 0, Qt.AlignmentFlag.AlignCenter)
            self._page_labels.append(label)

        self._scroll.verticalScrollBar().setValue(0)

    def _go_to_page(self, page: int):
        idx = page - 1
        if 0 <= idx < len(self._page_labels):
            self._current_page = idx
            self._page_display.setText(f"{page} / {len(self._page_labels)}")

    def _zoom(self, delta: float):
        self._scale = max(0.3, min(3.0, self._scale + delta))
        self._zoom_label.setText(f"{int(self._scale * 100)}%")
        self._render_all_pages()

    def _styles(self):
        return """
            QWidget#pdf-toolbar {
                background-color: #121212;
                border-bottom: 1px solid #2a2a2a;
            }
            QLabel#pdf-page-label, QLabel#pdf-zoom-label {
                color: #a0a0a0;
                font-size: 11px;
                padding: 0 6px;
            }
            QSpinBox#pdf-page-spinner {
                background-color: #1a1a1a;
                color: #eeeeee;
                border: 1px solid #2a2a2a;
                border-radius: 3px;
                font-size: 11px;
                padding: 0 4px;
            }
            QScrollArea#pdf-scroll {
                background-color: #0a0a0a;
                border: none;
            }
            QWidget#pdf-container {
                background-color: #0a0a0a;
            }
            QWidget#pdf-page-widget {
                background-color: #ffffff;
                border: 1px solid #2a2a2a;
                border-radius: 2px;
            }
            QLabel#pdf-page-number {
                color: #808080;
                font-size: 10px;
                padding: 4px 0 8px 0;
                background-color: transparent;
            }
        """
