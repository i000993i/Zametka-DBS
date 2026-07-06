from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QStackedWidget, QWidget, QLabel, QPushButton, QLineEdit
from PyQt6.QtCore import Qt, QSize
from assets.icons import icon


class SidebarBuilder:
    def __init__(self, mw):
        self.mw = mw
        self.sidebar = None

    def build(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self.mw._sidebar_stack = QStackedWidget()
        self.mw._sidebar_stack.addWidget(self._build_explorer_page())
        self.mw._sidebar_stack.addWidget(self.mw.search_widget)
        self.mw._sidebar_stack.addWidget(self.mw.notes_browser)
        self.mw._sidebar_stack.addWidget(self.mw.git_history)
        sidebar_layout.addWidget(self.mw._sidebar_stack)
        self.mw._sidebar_stack.setCurrentIndex(0)
        return self.sidebar

    def _build_explorer_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("sidebar-header")
        header.setFixedHeight(34)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 6, 0)
        header_layout.setSpacing(4)

        hi = QLabel()
        hi.setPixmap(icon("folder").pixmap(12, 12))
        hi.setFixedWidth(16)
        header_layout.addWidget(hi)
        hl = QLabel("EXPLORER")
        hl.setObjectName("vault-label")
        header_layout.addWidget(hl)
        header_layout.addStretch()

        self.mw._vault_menu = QPushButton()
        self.mw._vault_menu.setIcon(icon("folder-open"))
        self.mw._vault_menu.setIconSize(QSize(14, 14))
        self.mw._vault_menu.setObjectName("icon-btn")
        self.mw._vault_menu.setFixedSize(22, 22)
        self.mw._vault_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw._vault_menu.setToolTip("Vault menu")
        self.mw._vault_menu.clicked.connect(self.mw._show_vault_menu)
        header_layout.addWidget(self.mw._vault_menu)

        self.mw._help_btn = QPushButton()
        self.mw._help_btn.setIcon(icon("file-text"))
        self.mw._help_btn.setIconSize(QSize(14, 14))
        self.mw._help_btn.setObjectName("icon-btn")
        self.mw._help_btn.setFixedSize(22, 22)
        self.mw._help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mw._help_btn.setToolTip("Open Handbook")
        self.mw._help_btn.clicked.connect(self.mw._open_handbook)
        header_layout.addWidget(self.mw._help_btn)

        layout.addWidget(header)

        self.mw._file_search_edit = QLineEdit()
        self.mw._file_search_edit.setObjectName("file-search-edit")
        self.mw._file_search_edit.setPlaceholderText("Search files...")
        self.mw._file_search_edit.setClearButtonEnabled(True)
        self.mw._file_search_edit.setFixedHeight(28)
        self.mw._file_search_edit.textChanged.connect(self.mw._on_file_search_text_changed)
        self.mw._file_search_edit.setVisible(False)
        layout.addWidget(self.mw._file_search_edit)

        layout.addWidget(self.mw.file_tree, 1)
        layout.addWidget(self.mw.pinned_widget)
        layout.addWidget(self.mw.backlinks_panel)
        return page
