from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QSplitter, QLabel, QStatusBar,
    QFrame, QPushButton, QFileDialog, QMenu,
    QProgressBar, QLineEdit,
)
from PyQt6.QtCore import Qt, QPoint, QSize, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QAction
from PyQt6.QtWidgets import QCompleter
from PyQt6.QtCore import QStringListModel
import os

from assets.icons import icon
from zametka_dbs.core.event_bus import get_bus, Events
from zametka_dbs.core.config import get_config
from zametka_dbs.core.i18n import tr, set_language, current_language
from zametka_dbs.core.rust_bridge import HAS_RUST
from zametka_dbs.ui.code_editor import CodeEditor
from zametka_dbs.ui.file_tree_widget import FileTreeWidget
from zametka_dbs.ui.preview_widget import PreviewWidget
from zametka_dbs.ui.search_widget import SearchWidget
from zametka_dbs.ui.pinned_widget import PinnedWidget
from zametka_dbs.ui.activity_bar import ActivityBar
from zametka_dbs.ui.notes_browser import NotesBrowser
from zametka_dbs.ui.note_window import NoteWindow
from zametka_dbs.markdown.wikilinks import LinkResolver
from zametka_dbs.search.engine import SearchEngine
from zametka_dbs.ui.command_palette import CommandPalette
from zametka_dbs.ui.vault_manager import VaultManager
from zametka_dbs.ui.tab_manager import TabManager

try:
    from zametka_dbs.ui.html_browser import HtmlBrowser
except ImportError:
    HtmlBrowser = None


from zametka_dbs.ui.draggable_tab_bar import DraggableTabBar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bus = get_bus()

        # Wikilinks engine
        self._resolver = LinkResolver()
        # Search engine
        self._search_engine = SearchEngine()
        self._preview_visible = True

        # Command palette
        self._command_palette = CommandPalette()
        self._command_palette.command_triggered.connect(self._on_command)
        self._command_palette.set_commands(self._get_commands())

        # Drag & drop from OS
        self.setAcceptDrops(True)

        self._init_i18n()
        self._init_window()
        self._create_activity_bar()
        self._create_status_bar()
        self._create_editor_area()
        self._tab_manager = TabManager(
            self.editor, self.preview, self.status_saved, self.status_info,
            self._html_toggle_btn, self._main_stack, self._browser, self,
            tab_bar=self._tab_bar,
        )
        self._tab_manager.connect_signals()
        self._create_sidebar()

        self.editor._gutter.set_dark(get_config().get("theme", "dark") == "dark")
        self.editor2._gutter.set_dark(get_config().get("theme", "dark") == "dark")

        # Wikilink autocomplete (needs editor to exist)
        self._wikilink_model = QStringListModel()
        self._wikilink_completer = QCompleter(self._wikilink_model, self.editor)
        self._wikilink_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._wikilink_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._wikilink_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._wikilink_completer.setWidget(self.editor)
        self._wikilink_completer.activated.connect(self._on_wikilink_completed)
        self._wikilink_completer_visible = False

        self._setup_layout()
        self._vault_manager = VaultManager(
            self.file_tree, self._progress_bar, self.status_info,
            self.preview, self._resolver, self._search_engine, self,
        )
        self._create_menu_bar()

        self._connect_signals()
        self._setup_shortcuts()
        self.bus.emit(Events.APP_READY)
        QTimer.singleShot(2000, self._auto_check_updates)

    def _make_btn(self, icon_name, object_name, tooltip, slot, text="",
                  icon_size=QSize(14, 14), fixed_height=None, fixed_size=None,
                  checkable=False, visible=True):
        btn = QPushButton(text)
        if icon_name:
            btn.setIcon(icon(icon_name))
            btn.setIconSize(icon_size)
        btn.setObjectName(object_name)
        if fixed_height:
            btn.setFixedHeight(fixed_height)
        if fixed_size:
            btn.setFixedSize(fixed_size)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            btn.setToolTip(tooltip)
        if checkable:
            btn.setCheckable(True)
        if not visible:
            btn.setVisible(False)
        btn.clicked.connect(slot)
        return btn

    def _init_i18n(self):
        lang = get_config().get("language", "ru")
        set_language(lang)
        self.bus.subscribe(Events.LANGUAGE_CHANGED, self._on_language_changed)

    def _on_language_changed(self, **kwargs):
        lang = get_config().get("language", "ru")
        set_language(lang)
        self._retranslate_ui()

    def _init_window(self):
        self.setWindowTitle("Zametka")
        self.setMinimumSize(1000, 600)
        self.resize(1400, 850)
        config = get_config()
        theme = config.get("theme", "dark")
        self.setStyleSheet(self._load_stylesheet(theme))
        ico = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "app_icon.ico")
        if os.path.isfile(ico):
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(ico))
        else:
            self.setWindowIcon(icon("file-text", "#eeeeee", size=32))

    def _toggle_language(self):
        lang = "en" if current_language() == "ru" else "ru"
        get_config().set("language", lang)
        self.bus.emit(Events.LANGUAGE_CHANGED)

    def _retranslate_ui(self):
        config = get_config()
        current_theme = config.get("theme", "dark")
        self._lang_btn.setText(tr("status.lang"))
        self._lang_btn.setToolTip(tr("status.lang_tooltip"))
        self._activity_bar.set_button_tooltip(0, tr("activity.explorer"))
        self._activity_bar.set_button_tooltip(1, tr("activity.search"))
        self._activity_bar.set_button_tooltip(2, tr("activity.notes"))
        self._activity_bar.set_button_tooltip(3, tr("activity.history"))
        self._vault_menu.setToolTip(tr("editor.tooltip.vault_menu"))
        self._help_btn.setToolTip(tr("editor.tooltip.handbook"))
        self._save_btn.setText(tr("editor.save"))
        self._save_btn.setToolTip(tr("editor.tooltip.save"))
        self._save_as_btn.setText(tr("editor.save_as"))
        self._preview_toggle_btn.setToolTip(
            tr("editor.tooltip.show_preview") if self._preview_visible
            else tr("editor.tooltip.hide_preview")
        )
        self._split_btn.setToolTip(tr("editor.tooltip.split"))
        self._search_btn.setText(tr("editor.search"))
        self._file_search_edit.setPlaceholderText(tr("editor.search_placeholder"))
        self.status_saved.setText(tr("status.saved"))

        self._file_menu.setTitle(tr("menu.file"))
        self._act_open_file.setText(tr("menu.file.open_file"))
        self._act_open_folder.setText(tr("menu.file.open_folder"))
        self._act_close_folder.setText(tr("menu.file.close_folder"))
        self._act_save.setText(tr("menu.file.save"))
        self._act_save_as.setText(tr("menu.file.save_as"))
        self._act_quit.setText(tr("menu.file.quit"))
        self._view_menu.setTitle(tr("menu.view"))
        self._act_preview.setText(tr("menu.view.preview"))
        self._act_search.setText(tr("menu.view.search"))
        self._act_file_search.setText(tr("menu.view.file_search"))
        self._act_palette.setText(tr("menu.view.command_palette"))
        self._act_split.setText(tr("menu.view.split_editor"))
        self._act_theme.setText(
            tr("menu.view.dark_theme") if current_theme == "light" else tr("menu.view.light_theme")
        )
        self._ref_menu.setTitle(tr("menu.help"))
        self._act_handbook.setText(tr("menu.help.handbook"))
        self._act_about.setText(tr("menu.help.about_zametka"))
        self._act_update.setText(tr("menu.help.check_updates"))

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _create_activity_bar(self):
        self._activity_bar = ActivityBar()
        self._explorer_btn = self._activity_bar.add_button("folder", tr("activity.explorer"))
        self._explorer_btn.clicked.connect(lambda: self._switch_sidebar(0))
        self._search_btn_ab = self._activity_bar.add_button("search", tr("activity.search"))
        self._search_btn_ab.clicked.connect(lambda: self._switch_sidebar(1))
        self._notes_btn = self._activity_bar.add_button("layout", tr("activity.notes"))
        self._notes_btn.clicked.connect(lambda: self._switch_sidebar(2))
        self._git_btn = self._activity_bar.add_button("git-branch", tr("activity.history"))
        self._git_btn.clicked.connect(lambda: self._switch_sidebar(3))
        self._activity_bar.layout().addStretch()
        self._activity_bar.set_active(0)

    def _create_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self._sidebar_stack = QStackedWidget()
        self._sidebar_stack.addWidget(self._create_explorer_page())

        # Page 1: Search
        self.search_widget = SearchWidget(self._search_engine)
        self._sidebar_stack.addWidget(self.search_widget)

        # Page 2: Notes
        self.notes_browser = NotesBrowser()
        self.notes_browser.open_note.connect(self._on_notes_open)
        self._sidebar_stack.addWidget(self.notes_browser)

        # Page 3: Git history
        from zametka_dbs.ui.git_history import GitHistoryWidget
        self.git_history = GitHistoryWidget()
        self._sidebar_stack.addWidget(self.git_history)

        sidebar_layout.addWidget(self._sidebar_stack)
        self._sidebar_stack.setCurrentIndex(0)

    def _create_explorer_page(self):
        explorer_page = QWidget()
        explorer_layout = QVBoxLayout(explorer_page)
        explorer_layout.setContentsMargins(0, 0, 0, 0)
        explorer_layout.setSpacing(0)

        explorer_layout.addWidget(self._build_explorer_header())

        self._file_search_edit = QLineEdit()
        self._file_search_edit.setObjectName("file-search-edit")
        self._file_search_edit.setPlaceholderText(tr("editor.search_placeholder"))
        self._file_search_edit.setClearButtonEnabled(True)
        self._file_search_edit.setFixedHeight(28)
        self._file_search_edit.textChanged.connect(self._on_file_search_text_changed)
        self._file_search_edit.setVisible(False)
        explorer_layout.addWidget(self._file_search_edit)

        self.file_tree = FileTreeWidget()
        explorer_layout.addWidget(self.file_tree, 1)

        self.pinned_widget = PinnedWidget()
        self.pinned_widget.item_clicked.connect(self._on_pinned_item_clicked)
        explorer_layout.addWidget(self.pinned_widget)

        return explorer_page

    def _build_explorer_header(self):
        header = QWidget()
        header.setObjectName("sidebar-header")
        header.setFixedHeight(34)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 6, 0)
        header_layout.setSpacing(4)

        header_icon = QLabel()
        header_icon.setPixmap(icon("folder").pixmap(12, 12))
        header_icon.setFixedWidth(16)
        header_layout.addWidget(header_icon)
        header_label = QLabel(tr("sidebar.explorer"))
        header_label.setObjectName("vault-label")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        self._vault_menu = self._make_btn(
            "folder-open", "icon-btn", tr("editor.tooltip.vault_menu"),
            self._show_vault_menu, fixed_size=QSize(22, 22))
        header_layout.addWidget(self._vault_menu)

        self._help_btn = self._make_btn(
            "file-text", "icon-btn", tr("editor.tooltip.handbook"),
            self._tab_manager.open_handbook, fixed_size=QSize(22, 22))
        header_layout.addWidget(self._help_btn)

        return header

    def _create_editor_area(self):
        self._editor_container = QWidget()
        container_layout = QVBoxLayout(self._editor_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        self._create_tab_bar(container_layout)
        self._create_main_stack(container_layout)
        self.editor_area = self._editor_container

    def _create_tab_bar(self, container_layout):
        tab_row = QWidget()
        tab_row.setObjectName("tab-row")
        tab_row.setFixedHeight(34)
        tab_row_layout = QHBoxLayout(tab_row)
        tab_row_layout.setContentsMargins(0, 0, 0, 0)
        tab_row_layout.setSpacing(0)

        self._tab_bar = DraggableTabBar()
        self._tab_bar.setObjectName("editor-tabs")
        self._tab_bar.setTabsClosable(True)
        self._tab_bar.setDrawBase(False)
        self._tab_bar.setExpanding(False)
        self._tab_bar.setUsesScrollButtons(True)
        tab_row_layout.addWidget(self._tab_bar, 1)

        tab_row_layout.addSpacing(8)

        self._create_tab_buttons(tab_row_layout)

        container_layout.addWidget(tab_row)

    def _create_tab_buttons(self, layout):
        self._save_btn = self._make_btn(
            "save", "tab-btn", tr("editor.tooltip.save"),
            self._save_current_file, text=tr("editor.save"), fixed_height=24)
        layout.addWidget(self._save_btn)

        self._save_as_btn = self._make_btn(
            "save", "tab-btn", None, self._save_as,
            text=tr("editor.save_as"), fixed_height=24)
        layout.addWidget(self._save_as_btn)

        self._preview_toggle_btn = self._make_btn(
            "layout", "tab-btn", tr("editor.tooltip.show_preview"),
            self._toggle_preview, fixed_height=24)
        layout.addWidget(self._preview_toggle_btn)

        self._split_btn = self._make_btn(
            "columns", "tab-btn", tr("editor.tooltip.split"),
            self._toggle_split, fixed_height=24, checkable=True)
        layout.addWidget(self._split_btn)

        self._html_toggle_btn = self._make_btn(
            "eye", "tab-btn", tr("editor.tooltip.html"),
            self._toggle_html_view, fixed_height=24, visible=False)
        layout.addWidget(self._html_toggle_btn)

    def _create_main_stack(self, container_layout):
        self._main_stack = QStackedWidget()

        self._editor_page = QWidget()
        editor_layout = QVBoxLayout(self._editor_page)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)

        self._editor_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._editor_splitter.setObjectName("editor-splitter")
        self._editor_splitter.setHandleWidth(1)
        self._editor_splitter.setChildrenCollapsible(False)

        self.editor = CodeEditor()
        self.editor.setObjectName("editor-pane")
        self._editor_splitter.addWidget(self.editor)

        self.editor2 = CodeEditor()
        self.editor2.setObjectName("editor-pane")
        self.editor2.setVisible(False)
        self._editor_splitter.addWidget(self.editor2)

        self._editor_splitter.setSizes([700, 0])
        self.splitter.addWidget(self._editor_splitter)

        self.preview = PreviewWidget()
        self.splitter.addWidget(self.preview)
        self.splitter.setSizes([700, 500])

        editor_layout.addWidget(self.splitter)
        self._main_stack.addWidget(self._editor_page)

        self._browser = None

        container_layout.addWidget(self._main_stack, 1)
        self._main_stack.setCurrentIndex(0)

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("status-bar")
        self.status_bar.setFixedHeight(26)

        self.status_saved = QLabel(tr("status.saved"))
        self.status_cursor = QLabel(tr("status.ln_col", ln=1, col=1))
        self.status_words = QLabel(tr("status.words", count=0))
        self.status_font = QLabel(tr("status.ui_theme"))

        self._search_btn = self._make_btn(
            "search", "search-btn", None, self._toggle_search,
            text=tr("editor.search"), fixed_height=20)

        self.status_info = QLabel(tr("status.ready"))

        self._lang_btn = self._make_btn(
            None, "lang-btn", None, self._toggle_language,
            fixed_size=QSize(26, 20))

        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("status-progress")
        self._progress_bar.setFixedWidth(160)
        self._progress_bar.setFixedHeight(18)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.hide()

        self.status_bar.addWidget(self.status_saved)
        self.status_bar.addPermanentWidget(self._search_btn)
        self.status_bar.addPermanentWidget(self.status_cursor)
        self.status_bar.addPermanentWidget(self.status_words)
        self.status_bar.addPermanentWidget(self.status_font)
        self.status_bar.addPermanentWidget(self._lang_btn)
        self.status_bar.addPermanentWidget(self._progress_bar)
        self.status_bar.addPermanentWidget(self.status_info)

        self.setStatusBar(self.status_bar)

    def _switch_sidebar(self, index: int):
        self._sidebar_stack.setCurrentIndex(index)
        self._activity_bar.set_active(index)
        if index == 1:
            self.search_widget.focus()
        elif index == 2:
            self.notes_browser.refresh()
        elif index == 3:
            self.git_history.set_vault_path(self._resolver._vault_path)

    def _setup_layout(self):
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        top_layout.addWidget(self._activity_bar)
        top_layout.addWidget(self.sidebar)
        top_layout.addWidget(self.editor_area, 1)

        main_layout.addWidget(top_row, 1)

        self.setCentralWidget(central)

    def _create_menu_bar(self):
        mb = self.menuBar()
        self._build_file_menu(mb)
        self._build_view_menu(mb)
        self._build_help_menu(mb)

    def _build_file_menu(self, mb):
        self._file_menu = mb.addMenu(tr("menu.file"))
        self._act_open_file = QAction(tr("menu.file.open_file"), self)
        self._act_open_file.triggered.connect(self._open_file_dialog)
        self._file_menu.addAction(self._act_open_file)
        self._act_open_folder = QAction(tr("menu.file.open_folder"), self)
        self._act_open_folder.triggered.connect(self._vault_manager.open_dialog)
        self._file_menu.addAction(self._act_open_folder)
        self._act_close_folder = QAction(tr("menu.file.close_folder"), self)
        self._act_close_folder.triggered.connect(self._vault_manager.close_vault)
        self._file_menu.addAction(self._act_close_folder)
        self._file_menu.addSeparator()
        self._act_save = QAction(tr("menu.file.save"), self)
        self._act_save.triggered.connect(self._save_current_file)
        self._file_menu.addAction(self._act_save)
        self._act_save_as = QAction(tr("menu.file.save_as"), self)
        self._act_save_as.triggered.connect(self._save_as)
        self._file_menu.addAction(self._act_save_as)
        self._file_menu.addSeparator()
        self._act_quit = QAction(tr("menu.file.quit"), self)
        self._act_quit.triggered.connect(self.close)
        self._file_menu.addAction(self._act_quit)

    def _build_view_menu(self, mb):
        config = get_config()
        current_theme = config.get("theme", "dark")
        self._view_menu = mb.addMenu(tr("menu.view"))
        self._act_preview = QAction(tr("menu.view.preview"), self)
        self._act_preview.triggered.connect(self._toggle_preview)
        self._view_menu.addAction(self._act_preview)
        self._act_search = QAction(tr("menu.view.search"), self)
        self._act_search.triggered.connect(self._toggle_search)
        self._view_menu.addAction(self._act_search)
        self._act_file_search = QAction(tr("menu.view.file_search"), self)
        self._act_file_search.triggered.connect(self._toggle_file_search)
        self._view_menu.addAction(self._act_file_search)
        self._act_palette = QAction(tr("menu.view.command_palette"), self)
        self._act_palette.triggered.connect(self._toggle_command_palette)
        self._view_menu.addAction(self._act_palette)
        self._act_split = QAction(tr("menu.view.split_editor"), self)
        self._act_split.triggered.connect(self._toggle_split)
        self._view_menu.addAction(self._act_split)
        self._view_menu.addSeparator()
        self._act_theme = QAction(
            tr("menu.view.dark_theme") if current_theme == "light" else tr("menu.view.light_theme"),
            self
        )
        self._act_theme.triggered.connect(self._toggle_theme)
        self._view_menu.addAction(self._act_theme)

    def _build_help_menu(self, mb):
        self._ref_menu = mb.addMenu(tr("menu.help"))
        self._act_handbook = QAction(tr("menu.help.handbook"), self)
        self._act_handbook.triggered.connect(self._tab_manager.open_handbook)
        self._ref_menu.addAction(self._act_handbook)
        self._ref_menu.addSeparator()
        self._act_about = QAction(tr("menu.help.about_zametka"), self)
        self._act_about.triggered.connect(self._show_about)
        self._ref_menu.addAction(self._act_about)
        self._act_update = QAction(tr("menu.help.check_updates"), self)
        self._act_update.triggered.connect(self._check_updates)
        self._ref_menu.addAction(self._act_update)

    def _show_about(self):
        from PyQt6.QtWidgets import QMessageBox
        from zametka_dbs.core.version import __version__, __repo__
        engine = "zametka_core (Rust)" if HAS_RUST else "markdown-it-py (Python)"
        QMessageBox.about(self, tr("about.title"),
            tr("about.text", version=__version__, repo=__repo__, engine=engine)
        )

    def _check_updates(self):
        from zametka_dbs.core.updater import UpdateDialog
        dlg = UpdateDialog(self)
        dlg.exec()

    def _auto_check_updates(self):
        import threading

        def _check():
            try:
                from zametka_dbs.core.updater import check_for_updates
                result = check_for_updates()
                if result.available:
                    def update_ui():
                        self.status_info.setText(f"Доступно обновление {result.latest_version}")
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(0, update_ui)
            except Exception:
                pass
        threading.Thread(target=_check, daemon=True).start()

    def _setup_shortcuts(self):
        sc_save = QShortcut(QKeySequence.StandardKey.Save, self)
        sc_save.activated.connect(self._save_current_file)

        sc_new = QShortcut(QKeySequence("Ctrl+N"), self)
        sc_new.activated.connect(self._tab_manager.new_note)

        sc_open = QShortcut(QKeySequence("Ctrl+O"), self)
        sc_open.activated.connect(self._vault_manager.open_dialog)

        sc_search = QShortcut(QKeySequence("Ctrl+F"), self)
        sc_search.activated.connect(self._toggle_search)

        sc_preview = QShortcut(QKeySequence("Ctrl+P"), self)
        sc_preview.activated.connect(self._toggle_preview)

        sc_fs = QShortcut(QKeySequence("F11"), self)
        sc_fs.activated.connect(self._toggle_maximize)

        sc_file_search = QShortcut(QKeySequence("Ctrl+Shift+F"), self)
        sc_file_search.activated.connect(self._toggle_file_search)

        sc_palette = QShortcut(QKeySequence("Ctrl+Shift+P"), self)
        sc_palette.activated.connect(self._toggle_command_palette)

        sc_split = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        sc_split.activated.connect(self._toggle_split)

    def _toggle_split(self):
        is_split = not self.editor2.isVisible()
        self.editor2.setVisible(is_split)
        self._split_btn.setChecked(is_split)
        if is_split:
            total = self._editor_splitter.width()
            half = total // 2
            self._editor_splitter.setSizes([half, total - half])
        else:
            self._editor_splitter.setSizes([self._editor_splitter.width(), 0])

    def _toggle_command_palette(self):
        if self._command_palette.isVisible():
            self._command_palette.close()
        else:
            parent_rect = self.rect()
            x = (parent_rect.width() - self._command_palette.width()) // 2
            y = parent_rect.height() // 4
            self._command_palette.move(self.mapToGlobal(parent_rect.topLeft()) + QPoint(x, y))
            self._command_palette.show()

    def _get_commands(self) -> list[tuple[str, str]]:
        return [
            ("new_note", "New Note (Ctrl+N)"),
            ("save", "Save (Ctrl+S)"),
            ("save_as", "Save As..."),
            ("open_file", "Open File..."),
            ("open_vault", "Open Folder..."),
            ("toggle_preview", "Toggle Preview (Ctrl+P)"),
            ("toggle_search", "Toggle Search (Ctrl+F)"),
            ("toggle_file_search", "Search Files (Ctrl+Shift+F)"),
            ("toggle_theme", "Toggle Theme"),
            ("toggle_split", "Split Editor (Ctrl+Shift+S)"),
            ("toggle_maximize", "Toggle Fullscreen (F11)"),
            ("open_handbook", "Open Handbook"),
        ]

    def _on_command(self, cmd_id: str):
        method_map = {
            "new_note": self._tab_manager.new_note,
            "save": self._save_current_file,
            "save_as": self._save_as,
            "open_file": self._open_file_dialog,
            "open_vault": self._vault_manager.open_dialog,
            "toggle_preview": self._toggle_preview,
            "toggle_search": self._toggle_search,
            "toggle_file_search": self._toggle_file_search,
            "toggle_theme": self._toggle_theme,
            "toggle_split": self._toggle_split,
            "toggle_maximize": self._toggle_maximize,
            "open_handbook": self._tab_manager.open_handbook,
        }
        method = method_map.get(cmd_id)
        if method:
            method()

    def _toggle_file_search(self):
        visible = not self._file_search_edit.isVisible()
        self._file_search_edit.setVisible(visible)
        if visible:
            self._file_search_edit.setFocus()
            self._file_search_edit.selectAll()
        else:
            self._file_search_edit.clear()
            self.file_tree.set_filter_text("")

    def _on_file_search_text_changed(self, text: str):
        self.file_tree.set_filter_text(text)

    def _save_current_file(self):
        path = self._tab_manager.current_file
        if not path or path.startswith("__"):
            self._save_as()
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.status_saved.setText("Saved")
            self._tab_manager.update_tab_after_save(path)
        except Exception as e:
            self.status_info.setText(f"Save error: {e}")

    def _save_as(self):
        new_path, _ = QFileDialog.getSaveFileName(
            self, "Save Note As", "",
            "Markdown (*.md);;All Files (*)"
        )
        if not new_path:
            return
        old_path = self._tab_manager.current_file
        try:
            with open(new_path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
        except Exception as e:
            self.status_info.setText(f"Save error: {e}")
            return

        self._tab_manager.update_tab_after_save_as(old_path, new_path)
        self._tab_manager.current_file = new_path

    def _connect_signals(self):
        self.editor.cursorPositionChanged.connect(self._update_status_cursor)
        self.editor.textChanged.connect(self._on_editor_changed)
        self.editor2.cursorPositionChanged.connect(self._update_status_cursor)
        self.editor2.textChanged.connect(self._on_editor2_changed)
        self.file_tree.file_opened.connect(self._tab_manager.on_file_opened)
        self.preview.wikilink_clicked.connect(self._on_wikilink_clicked)
        self.preview.rendered.connect(self._on_preview_rendered)
        self.search_widget.result_clicked.connect(self._tab_manager.on_file_opened)

        self._tab_manager.save_requested.connect(self._save_current_file)
        self._tab_manager.save_as_requested.connect(self._save_as)

        self._syncing_scroll = False
        editor_scroll = self.editor.verticalScrollBar()
        editor_scroll.valueChanged.connect(self._sync_editor_scroll_to_preview)

        self._tab_manager.create_initial_tab()
        self._vault_manager.init_on_startup()

    def closeEvent(self, event):
        self._vault_manager.stop_watcher()
        self._vault_manager._cleanup_worker()
        super().closeEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.exists(path):
                self._tab_manager.on_file_opened(path)
        event.acceptProposedAction()

    def _on_wikilink_completed(self, text: str):
        cursor = self.editor.textCursor()
        cursor.insertText(text + "]]")
        self._wikilink_completer_visible = False

    def _update_wikilink_completer(self):
        text = self.editor.toPlainText()
        cursor = self.editor.textCursor()
        pos = cursor.position()
        before = text[:pos]
        idx = before.rfind("[[")
        if idx >= 0:
            partial = before[idx + 2:]
            if "]]" not in partial and "\n" not in partial:
                candidates = list(self._resolver.all_notes.keys())
                self._wikilink_model.setStringList(candidates)
                rect = self.editor.cursorRect()
                rect.setWidth(300)
                self._wikilink_completer.setWidget(self.editor)
                self._wikilink_completer.complete(rect)
                self._wikilink_completer_visible = True
                return
        if self._wikilink_completer_visible:
            self._wikilink_completer.popup().hide()
            self._wikilink_completer_visible = False

    def _on_pinned_item_clicked(self, path: str):
        if os.path.isfile(path):
            self._tab_manager.on_file_opened(path)
        elif os.path.isdir(path):
            self._vault_manager.init_from_pin(path)

    def _on_notes_open(self, filepath: str):
        w = NoteWindow(filepath)
        w.set_note_map(self._resolver.all_notes)
        w.show()
        w.raise_()

    def _show_vault_menu(self):
        menu = QMenu(self)
        config = get_config()
        current_theme = config.get("theme", "dark")

        self._add_file_actions(menu)
        menu.addSeparator()
        self._add_folder_actions(menu)
        menu.addSeparator()
        self._add_save_actions(menu)
        menu.addSeparator()
        self._add_theme_action(menu, current_theme)

        menu.exec(self._vault_menu.mapToGlobal(self._vault_menu.rect().bottomLeft()))

    def _add_file_actions(self, menu: QMenu):
        act_open_file = QAction(tr("vault_menu.open_file"), self)
        act_open_file.triggered.connect(self._open_file_dialog)
        menu.addAction(act_open_file)

        act_create_file = QAction(tr("vault_menu.create_file"), self)
        act_create_file.triggered.connect(self._tab_manager.new_note)
        menu.addAction(act_create_file)

    def _add_folder_actions(self, menu: QMenu):
        act_open_folder = QAction(tr("vault_menu.open_folder"), self)
        act_open_folder.triggered.connect(self._vault_manager.open_dialog)
        menu.addAction(act_open_folder)

        act_close_folder = QAction(tr("vault_menu.close_folder"), self)
        act_close_folder.triggered.connect(self._vault_manager.close_vault)
        menu.addAction(act_close_folder)

    def _add_save_actions(self, menu: QMenu):
        act_save = QAction(tr("vault_menu.save"), self)
        act_save.triggered.connect(self._save_current_file)
        menu.addAction(act_save)

        act_save_as = QAction(tr("vault_menu.save_as"), self)
        act_save_as.triggered.connect(self._save_as)
        menu.addAction(act_save_as)

    def _add_theme_action(self, menu: QMenu, current_theme: str):
        act_toggle_theme = QAction(
            tr("vault_menu.dark_theme") if current_theme == "light" else tr("vault_menu.light_theme"),
            self
        )
        act_toggle_theme.triggered.connect(self._toggle_theme)
        menu.addAction(act_toggle_theme)

    def _open_file_dialog(self):
        config = get_config()
        vault_path = config.get("vault_path", "")
        start_dir = vault_path if vault_path and os.path.isdir(vault_path) else ""

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", start_dir,
            "Markdown Files (*.md);;All Files (*)"
        )
        if file_path:
            self._tab_manager.on_file_opened(file_path)

    def _toggle_search(self):
        if self._sidebar_stack.currentIndex() == 1:
            self._switch_sidebar(0)
        else:
            self._switch_sidebar(1)

    def _ensure_browser(self):
        if self._browser is None:
            if HtmlBrowser is None:
                self.status_info.setText("HTML viewer not available (PyQt6-WebEngine not installed)")
                return
            self._browser = HtmlBrowser()
            self._main_stack.addWidget(self._browser)

    def _toggle_html_view(self):
        if self._main_stack.currentIndex() == 0:
            self._ensure_browser()
            path = self._tab_manager.current_file
            if path and os.path.isfile(path):
                self._browser.load_file(os.path.abspath(path))
            self._main_stack.setCurrentIndex(1)
            self._html_toggle_btn.setToolTip("Показать исходный код")
        else:
            self._main_stack.setCurrentIndex(0)
            self._html_toggle_btn.setToolTip("Просмотр HTML")

    def _toggle_preview(self):
        """Toggle preview pane visibility."""
        visible = self.preview.isVisible()
        self.preview.setVisible(not visible)
        self._preview_visible = not visible
        if visible:
            self._preview_toggle_btn.setToolTip(tr("editor.tooltip.show_preview"))
            self._preview_toggle_btn.setIcon(icon("eye-off"))
        else:
            self._preview_toggle_btn.setToolTip(tr("editor.tooltip.hide_preview"))
            self._preview_toggle_btn.setIcon(icon("eye"))


    def _on_wikilink_clicked(self, target: str):
        resolved = self._resolver.resolve(target)
        if resolved:
            self._tab_manager.on_file_opened(resolved)
        else:
            self.status_info.setText(f"Wikilink not found: {target}")

    def _update_status_cursor(self):
        line = self.editor.get_current_line()
        col = self.editor.get_current_column()
        self.status_cursor.setText(f"Ln {line}, Col {col}")

    def _on_preview_rendered(self, html: str):
        self._tab_manager.cache_html(html)
        self._sync_editor_scroll_to_preview(force=True)

    def _sync_editor_scroll_to_preview(self, value=None, force=False):
        editor_sb = self.editor.verticalScrollBar()
        preview_sb = self.preview.verticalScrollBar()
        if not editor_sb or not preview_sb:
            return

        if self._syncing_scroll:
            return

        self._syncing_scroll = True

        e_max = editor_sb.maximum() - editor_sb.minimum()
        p_max = preview_sb.maximum() - preview_sb.minimum()
        if e_max > 0 and p_max > 0:
            ratio = (editor_sb.value() - editor_sb.minimum()) / e_max
            target = preview_sb.minimum() + int(ratio * p_max)
            preview_sb.setValue(target)

        self._syncing_scroll = False

    def _on_editor_changed(self):
        count = self.editor.word_count()
        self.status_words.setText(f"Words: {count}")
        self._update_wikilink_completer()
        ext = os.path.splitext(self._tab_manager.current_file)[1].lower() if self._tab_manager.current_file else ""
        if ext in (".md", ".markdown", ".mdown", ".mdx"):
            self.preview.set_content(self.editor.toPlainText())
        else:
            self.preview.setHtml("<html><body style='color:#888;font-family:sans-serif;padding:2em'><p>Preview only available for Markdown files.</p></body></html>")
        if self._tab_manager.current_file:
            self.status_saved.setText("Unsaved")
            self._tab_manager.mark_modified()

    def _on_editor2_changed(self):
        self.status_words.setText(f"Words: {self.editor2.word_count()}")

    def _toggle_theme(self):
        config = get_config()
        current = config.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        config.set("theme", new_theme)
        self._apply_theme(new_theme)

    def _apply_theme(self, theme: str):
        self.setStyleSheet(self._load_stylesheet(theme))
        is_dark = theme == "dark"
        self.editor.update_theme(is_dark)
        self.editor2.update_theme(is_dark)
        ico_color = "#cccccc" if is_dark else "#555555"
        self._split_btn.setIcon(icon("columns", ico_color))
        self._preview_toggle_btn.setIcon(icon("layout", ico_color))
        self._html_toggle_btn.setIcon(icon("eye", ico_color))
        self._save_btn.setIcon(icon("save", ico_color))
        self._save_as_btn.setIcon(icon("save", ico_color))
        self.bus.emit(Events.THEME_CHANGED, theme=theme)

    def _load_stylesheet(self, theme: str = "dark") -> str:
        from zametka_dbs.ui.styles import the_stylesheet
        return the_stylesheet(theme)
