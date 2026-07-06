from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QSplitter, QLabel, QStatusBar,
    QScrollArea, QFrame, QPushButton, QFileDialog, QTabBar, QMenu,
    QProgressBar, QLineEdit,
)
from PyQt6.QtCore import Qt, QPoint, QSize, QTimer, QMimeData, pyqtSignal, QThread, QObject, QUrl, QProcess
from PyQt6.QtGui import QDrag
from PyQt6.QtGui import QKeySequence, QShortcut, QAction, QPixmap, QColor, QFont
from PyQt6.QtWidgets import QApplication, QCompleter
from PyQt6.QtCore import QStringListModel
import os

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from assets.icons import icon
from zametka_dbs.core.event_bus import get_bus, Events
from zametka_dbs.core.config import get_config
from zametka_dbs.ui.code_editor import CodeEditor
from zametka_dbs.ui.file_tree_widget import FileTreeWidget
from zametka_dbs.ui.preview_widget import PreviewWidget
from zametka_dbs.ui.backlinks_panel import BacklinksPanel
from zametka_dbs.ui.search_widget import SearchWidget
from zametka_dbs.ui.pinned_widget import PinnedWidget
from zametka_dbs.ui.activity_bar import ActivityBar
from zametka_dbs.ui.notes_browser import NotesBrowser
from zametka_dbs.ui.note_window import NoteWindow
from zametka_dbs.markdown.wikilinks import LinkResolver, BacklinkIndex
from zametka_dbs.search.engine import SearchEngine
from zametka_dbs.ui.terminal_widget import TerminalWidget
from zametka_dbs.ui.command_palette import CommandPalette

try:
    from zametka_dbs.ui.html_browser import HtmlBrowser
except ImportError:
    HtmlBrowser = None


from zametka_dbs.ui.draggable_tab_bar import DraggableTabBar


class VaultWorker(QObject):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal()

    def __init__(self, vault_path, resolver, backlinks, search_engine):
        super().__init__()
        self._vault_path = vault_path
        self._resolver = resolver
        self._backlinks = backlinks
        self._search_engine = search_engine
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        self.progress.emit(0, 0, "Scanning files...")
        self._resolver.set_vault_path(self._vault_path)
        if self._cancelled:
            self.finished.emit()
            return

        all_files = list(self._resolver.all_notes.values())
        total = len(all_files)

        if total == 0:
            self.progress.emit(0, 0, "No markdown files found")
            self.finished.emit()
            return

        self.progress.emit(0, total, f"Indexing for search...")
        self._search_engine.index_vault(self._vault_path)
        if self._cancelled:
            self.finished.emit()
            return

        for i, fp in enumerate(all_files):
            if self._cancelled:
                self.finished.emit()
                return
            self.progress.emit(i + 1, total, f"Building links {i+1} of {total}...")
            self._backlinks.index_file(fp)
        self._backlinks._rebuild_backlinks()

        self.progress.emit(total, total, "Ready")
        self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bus = get_bus()
        self._current_file = ""

        # Wikilinks engine
        self._resolver = LinkResolver()
        self._backlinks = BacklinkIndex(self._resolver)

        # Search engine
        self._search_engine = SearchEngine()
        self._backlinks_visible = True
        self._preview_visible = True

        # Tab state
        self._open_tabs: list[str] = []
        self._tab_state: dict[str, dict] = {}
        self._untitled_counter = 0

        # File watcher
        self._watcher: Observer | None = None

        # Command palette
        self._command_palette = CommandPalette()
        self._command_palette.command_triggered.connect(self._on_command)
        self._command_palette.set_commands(self._get_commands())

        # Drag & drop from OS
        self.setAcceptDrops(True)

        self._init_window()
        self._create_activity_bar()
        self._create_sidebar()
        self._create_editor_area()

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

        self._create_status_bar()
        self._setup_layout()
        self._create_menu_bar()

        self._connect_signals()
        self._setup_shortcuts()
        self.bus.emit(Events.APP_READY)
        QTimer.singleShot(2000, self._auto_check_updates)

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

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _create_activity_bar(self):
        self._activity_bar = ActivityBar()
        self._explorer_btn = self._activity_bar.add_button("folder", "Explorer")
        self._explorer_btn.clicked.connect(lambda: self._switch_sidebar(0))
        self._search_btn_ab = self._activity_bar.add_button("search", "Search")
        self._search_btn_ab.clicked.connect(lambda: self._switch_sidebar(1))
        self._notes_btn = self._activity_bar.add_button("layout", "Notes")
        self._notes_btn.clicked.connect(lambda: self._switch_sidebar(2))
        self._git_btn = self._activity_bar.add_button("git-branch", "History")
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

        # Page 0: Explorer (vault header + file tree + pinned)
        explorer_page = QWidget()
        explorer_layout = QVBoxLayout(explorer_page)
        explorer_layout.setContentsMargins(0, 0, 0, 0)
        explorer_layout.setSpacing(0)

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
        header_label = QLabel("EXPLORER")
        header_label.setObjectName("vault-label")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        self._vault_menu = QPushButton()
        self._vault_menu.setIcon(icon("folder-open"))
        self._vault_menu.setIconSize(QSize(14, 14))
        self._vault_menu.setObjectName("icon-btn")
        self._vault_menu.setFixedSize(22, 22)
        self._vault_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self._vault_menu.setToolTip("Vault menu")
        self._vault_menu.clicked.connect(self._show_vault_menu)
        header_layout.addWidget(self._vault_menu)

        self._help_btn = QPushButton()
        self._help_btn.setIcon(icon("file-text"))
        self._help_btn.setIconSize(QSize(14, 14))
        self._help_btn.setObjectName("icon-btn")
        self._help_btn.setFixedSize(22, 22)
        self._help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._help_btn.setToolTip("Open Handbook")
        self._help_btn.clicked.connect(self._open_handbook)
        header_layout.addWidget(self._help_btn)

        explorer_layout.addWidget(header)

        self._file_search_edit = QLineEdit()
        self._file_search_edit.setObjectName("file-search-edit")
        self._file_search_edit.setPlaceholderText("Search files...")
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

        self.backlinks_panel = BacklinksPanel()
        explorer_layout.addWidget(self.backlinks_panel)

        self._sidebar_stack.addWidget(explorer_page)

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

    def _create_editor_area(self):
        self._editor_container = QWidget()
        container_layout = QVBoxLayout(self._editor_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Tab bar (always visible)
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
        self._tab_bar.tabCloseRequested.connect(self._close_tab)
        self._tab_bar.currentChanged.connect(self._on_tab_switched)
        self._tab_bar.dragged_tab.connect(self._on_tab_dragged_out)
        tab_row_layout.addWidget(self._tab_bar, 1)

        tab_row_layout.addSpacing(8)

        self._save_btn = QPushButton(" Save")
        self._save_btn.setIcon(icon("save"))
        self._save_btn.setIconSize(QSize(14, 14))
        self._save_btn.setObjectName("tab-btn")
        self._save_btn.setFixedHeight(24)
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setToolTip("Save (Ctrl+S)")
        self._save_btn.clicked.connect(self._save_current_file)
        tab_row_layout.addWidget(self._save_btn)

        self._save_as_btn = QPushButton(" Save As…")
        self._save_as_btn.setIcon(icon("save"))
        self._save_as_btn.setIconSize(QSize(14, 14))
        self._save_as_btn.setObjectName("tab-btn")
        self._save_as_btn.setFixedHeight(24)
        self._save_as_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_as_btn.clicked.connect(self._save_as)
        tab_row_layout.addWidget(self._save_as_btn)

        # Preview toggle button
        self._preview_toggle_btn = QPushButton()
        self._preview_toggle_btn.setIcon(icon("layout"))
        self._preview_toggle_btn.setIconSize(QSize(14, 14))
        self._preview_toggle_btn.setObjectName("tab-btn")
        self._preview_toggle_btn.setFixedHeight(24)
        self._preview_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._preview_toggle_btn.setToolTip("Toggle Preview (Ctrl+P)")
        self._preview_toggle_btn.clicked.connect(self._toggle_preview)
        tab_row_layout.addWidget(self._preview_toggle_btn)

        # Split editor toggle button
        self._split_btn = QPushButton()
        self._split_btn.setIcon(icon("columns"))
        self._split_btn.setIconSize(QSize(14, 14))
        self._split_btn.setObjectName("tab-btn")
        self._split_btn.setFixedHeight(24)
        self._split_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._split_btn.setToolTip("Split Editor")
        self._split_btn.setCheckable(True)
        self._split_btn.clicked.connect(self._toggle_split)
        tab_row_layout.addWidget(self._split_btn)

        # HTML render toggle button
        self._html_toggle_btn = QPushButton()
        self._html_toggle_btn.setIcon(icon("eye"))
        self._html_toggle_btn.setIconSize(QSize(14, 14))
        self._html_toggle_btn.setObjectName("tab-btn")
        self._html_toggle_btn.setFixedHeight(24)
        self._html_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._html_toggle_btn.setToolTip("Просмотр HTML")
        self._html_toggle_btn.setVisible(False)
        self._html_toggle_btn.clicked.connect(self._toggle_html_view)
        tab_row_layout.addWidget(self._html_toggle_btn)

        container_layout.addWidget(tab_row)

        # Stack: Editor page | Browser page
        self._main_stack = QStackedWidget()

        # Page 0: Editor + Preview
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

        # Page 1: WebEngine browser (lazy)
        self._browser = None

        container_layout.addWidget(self._main_stack, 1)

        self._main_stack.setCurrentIndex(0)
        self.editor_area = self._editor_container

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("status-bar")
        self.status_bar.setFixedHeight(26)

        self.status_saved = QLabel("Saved")
        self.status_cursor = QLabel("Ln 1, Col 1")
        self.status_words = QLabel("Words: 0")
        self.status_font = QLabel("System UI")

        self._search_btn = QPushButton(" Search")
        self._search_btn.setIcon(icon("search"))
        self._search_btn.setIconSize(QSize(14, 14))
        self._search_btn.setObjectName("search-btn")
        self._search_btn.setFixedHeight(20)
        self._search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._search_btn.clicked.connect(self._toggle_search)

        self._terminal_btn = QPushButton()
        self._terminal_btn.setIcon(icon("terminal"))
        self._terminal_btn.setIconSize(QSize(14, 14))
        self._terminal_btn.setObjectName("terminal-btn")
        self._terminal_btn.setFixedSize(20, 20)
        self._terminal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._terminal_btn.setToolTip("Toggle Terminal (Ctrl+`)")
        self._terminal_btn.setCheckable(True)
        self._terminal_btn.clicked.connect(self._toggle_terminal)

        self.status_info = QLabel("Ready")

        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("status-progress")
        self._progress_bar.setFixedWidth(160)
        self._progress_bar.setFixedHeight(18)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.hide()

        self.status_bar.addWidget(self.status_saved)
        self.status_bar.addPermanentWidget(self._terminal_btn)
        self.status_bar.addPermanentWidget(self._search_btn)
        self.status_bar.addPermanentWidget(self.status_cursor)
        self.status_bar.addPermanentWidget(self.status_words)
        self.status_bar.addPermanentWidget(self.status_font)
        self.status_bar.addPermanentWidget(self._progress_bar)
        self.status_bar.addPermanentWidget(self.status_info)

        self.setStatusBar(self.status_bar)

    def _switch_sidebar(self, index: int):
        self._sidebar_stack.setCurrentIndex(index)
        self._activity_bar.set_active(index)
        if index == 1:
            self.search_widget.focus()
            self._backlinks_visible = self.backlinks_panel.isVisible()
            self.backlinks_panel.setVisible(False)
        elif index == 2:
            self.notes_browser.refresh()
            self.backlinks_panel.setVisible(False)
        elif index == 3:
            self.git_history.set_vault_path(self._resolver._vault_path)
            self.backlinks_panel.setVisible(False)
        else:
            self.backlinks_panel.setVisible(getattr(self, '_backlinks_visible', True))

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

        self.terminal_widget = TerminalWidget()
        self.terminal_widget.setVisible(False)
        self.terminal_widget.toggled.connect(lambda v: self._terminal_btn.setChecked(v))
        main_layout.addWidget(self.terminal_widget)

        self.setCentralWidget(central)

    def _create_menu_bar(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("Файл")
        act_open_file = QAction("Open File...", self)
        act_open_file.triggered.connect(self._open_file_dialog)
        file_menu.addAction(act_open_file)
        act_open_folder = QAction("Open Folder...", self)
        act_open_folder.triggered.connect(self._open_vault_dialog)
        file_menu.addAction(act_open_folder)
        act_close_folder = QAction("Close Folder", self)
        act_close_folder.triggered.connect(self._close_current_vault)
        file_menu.addAction(act_close_folder)
        file_menu.addSeparator()
        act_save = QAction("Save", self)
        act_save.triggered.connect(self._save_current_file)
        file_menu.addAction(act_save)
        act_save_as = QAction("Save As...", self)
        act_save_as.triggered.connect(self._save_as)
        file_menu.addAction(act_save_as)
        file_menu.addSeparator()
        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        view_menu = mb.addMenu("Вид")
        act_preview = QAction("Toggle Preview", self)
        act_preview.triggered.connect(self._toggle_preview)
        view_menu.addAction(act_preview)
        act_terminal = QAction("Toggle Terminal", self)
        act_terminal.triggered.connect(self._toggle_terminal)
        view_menu.addAction(act_terminal)
        act_search = QAction("Toggle Search", self)
        act_search.triggered.connect(self._toggle_search)
        view_menu.addAction(act_search)
        act_file_search = QAction("Toggle File Search", self)
        act_file_search.triggered.connect(self._toggle_file_search)
        view_menu.addAction(act_file_search)
        act_palette = QAction("Command Palette", self)
        act_palette.triggered.connect(self._toggle_command_palette)
        view_menu.addAction(act_palette)
        act_split = QAction("Split Editor", self)
        act_split.triggered.connect(self._toggle_split)
        view_menu.addAction(act_split)
        view_menu.addSeparator()
        config = get_config()
        current_theme = config.get("theme", "dark")
        act_theme = QAction("Light Theme" if current_theme == "dark" else "Dark Theme", self)
        act_theme.triggered.connect(self._toggle_theme)
        view_menu.addAction(act_theme)

        ref_menu = mb.addMenu("Справочник")
        act_handbook = QAction("Markdown Handbook", self)
        act_handbook.triggered.connect(self._open_handbook)
        ref_menu.addAction(act_handbook)

        about_menu = mb.addMenu("О приложении")
        act_about = QAction("About Zametka", self)
        act_about.triggered.connect(self._show_about)
        about_menu.addAction(act_about)
        about_menu.addSeparator()
        act_update = QAction("Проверить обновления...", self)
        act_update.triggered.connect(self._check_updates)
        about_menu.addAction(act_update)

    def _show_about(self):
        from PyQt6.QtWidgets import QMessageBox
        from zametka_dbs.core.version import __version__, __repo__
        QMessageBox.about(self, "About Zametka",
            "Zametka — заметки с Rust-ядром\n\n"
            f"Версия: {__version__}\n"
            f"GitHub: {__repo__}\n"
            "Движок: zametka_core (Rust)\n"
            "UI: PyQt6"
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
        sc_new.activated.connect(self._new_note)

        sc_open = QShortcut(QKeySequence("Ctrl+O"), self)
        sc_open.activated.connect(self._open_vault_dialog)

        sc_search = QShortcut(QKeySequence("Ctrl+F"), self)
        sc_search.activated.connect(self._toggle_search)

        sc_preview = QShortcut(QKeySequence("Ctrl+P"), self)
        sc_preview.activated.connect(self._toggle_preview)

        sc_fs = QShortcut(QKeySequence("F11"), self)
        sc_fs.activated.connect(self._toggle_maximize)

        sc_term = QShortcut(QKeySequence("Ctrl+`"), self)
        sc_term.activated.connect(self._toggle_terminal)

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
            ("toggle_terminal", "Toggle Terminal (Ctrl+`)"),
            ("toggle_theme", "Toggle Theme"),
            ("toggle_split", "Split Editor (Ctrl+Shift+S)"),
            ("toggle_maximize", "Toggle Fullscreen (F11)"),
            ("open_handbook", "Open Handbook"),
        ]

    def _on_command(self, cmd_id: str):
        method_map = {
            "new_note": self._new_note,
            "save": self._save_current_file,
            "save_as": self._save_as,
            "open_file": self._open_file_dialog,
            "open_vault": self._open_vault_dialog,
            "toggle_preview": self._toggle_preview,
            "toggle_search": self._toggle_search,
            "toggle_file_search": self._toggle_file_search,
            "toggle_terminal": self._toggle_terminal,
            "toggle_theme": self._toggle_theme,
            "toggle_split": self._toggle_split,
            "toggle_maximize": self._toggle_maximize,
            "open_handbook": self._open_handbook,
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

    def _toggle_terminal(self):
        visible = not self.terminal_widget.isVisible()
        self.terminal_widget.setVisible(visible)
        self._terminal_btn.setChecked(visible)
        if visible:
            self.terminal_widget.focus_input()

    def _save_current_file(self):
        if not self._current_file or self._current_file.startswith("__"):
            self._save_as()
            return
        try:
            with open(self._current_file, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.status_saved.setText("Saved")
            if self._current_file in self._tab_state:
                self._tab_state[self._current_file]["modified"] = False
                tidx = self._tab_index_of(self._current_file)
                if tidx >= 0:
                    name = os.path.basename(self._current_file)
                    self._tab_bar.setTabText(tidx, name)
        except Exception as e:
            self.status_info.setText(f"Save error: {e}")

    def _save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Note As", "",
            "Markdown (*.md);;All Files (*)"
        )
        if not path:
            return
        old_path = self._current_file
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
        except Exception as e:
            self.status_info.setText(f"Save error: {e}")
            return

        # Update tab data
        tidx = self._tab_index_of(old_path)
        if tidx >= 0:
            self._open_tabs.remove(old_path)
            self._open_tabs.append(path)
            if old_path in self._tab_state:
                del self._tab_state[old_path]
            self._tab_state[path] = {
                "content": self.editor.toPlainText(),
                "cursor": (self.editor.get_current_line(), self.editor.get_current_column()),
                "scroll": self.editor.verticalScrollBar().value() if self.editor.verticalScrollBar() else 0,
                "modified": False,
            }
            self._tab_bar.setTabData(tidx, path)
            name = os.path.basename(path)
            self._tab_bar.setTabText(tidx, name)

        self._current_file = path
        self.status_saved.setText("Saved")
        self.status_info.setText(path)
        name = os.path.basename(path)
        self.setWindowTitle(f"{name} — Zametka")

    def _connect_signals(self):
        self.editor.cursorPositionChanged.connect(self._update_status_cursor)
        self.editor.textChanged.connect(self._on_editor_changed)
        self.editor2.cursorPositionChanged.connect(self._update_status_cursor)
        self.editor2.textChanged.connect(self._on_editor2_changed)
        self.file_tree.file_opened.connect(self._on_file_opened)
        self.preview.wikilink_clicked.connect(self._on_wikilink_clicked)
        self.preview.rendered.connect(self._on_preview_rendered)
        self.backlinks_panel.backlink_clicked.connect(self._on_file_opened)
        self.search_widget.result_clicked.connect(self._on_file_opened)
        self.search_widget.replace_requested.connect(self._on_replace_in_file)

        self._tab_bar.tab_rename_requested.connect(self._on_tab_rename_requested)
        self._tab_bar.tab_close_others_requested.connect(self._on_tab_close_others)
        self._tab_bar.tab_close_all_requested.connect(self._on_tab_close_all)
        self._tab_bar.tab_copy_path_requested.connect(self._on_tab_copy_path)

        self._syncing_scroll = False
        editor_scroll = self.editor.verticalScrollBar()
        editor_scroll.valueChanged.connect(self._sync_editor_scroll_to_preview)

        # Create initial tab with welcome note
        content = (
            "# Welcome to Zametka\n\n"
            "Click the folder icon in the sidebar to open a vault folder,\n"
            "or start typing here to create a new note."
        )
        self._untitled_counter += 1
        path = f"__untitled_{self._untitled_counter}__"
        self._open_tabs.append(path)
        self._tab_state[path] = {
            "content": content,
            "cursor": (1, 1),
            "scroll": 0,
            "modified": False,
        }
        tidx = self._tab_bar.addTab("untitled.md")
        self._tab_bar.setTabData(tidx, path)
        self._tab_bar.setCurrentIndex(tidx)
        self._switch_to_tab(tidx)

        config = get_config()
        vault_path = config.get("vault_path", "")
        if vault_path and os.path.isdir(vault_path):
            self._init_vault(vault_path)
            self.status_info.setText("Vault opened")
        else:
            self.status_info.setText("No vault — open a folder to start")

    def _start_watcher(self, vault_path: str):
        self._stop_watcher()

        class _Handler(FileSystemEventHandler):
            def __init__(self, win):
                self.win = win

            def on_modified(self, event):
                if event.is_directory:
                    return
                self.win.status_info.setText(f"File changed: {os.path.basename(event.src_path)}")

            def on_created(self, event):
                if event.is_directory:
                    return
                self.win.status_info.setText(f"File created: {os.path.basename(event.src_path)}")

        self._watcher = Observer()
        self._watcher.schedule(_Handler(self), vault_path, recursive=True)
        self._watcher.start()

    def _stop_watcher(self):
        if self._watcher:
            self._watcher.stop()
            self._watcher.join(timeout=2)
            self._watcher = None

    def closeEvent(self, event):
        self._stop_watcher()
        if hasattr(self, 'terminal_widget'):
            proc = getattr(self.terminal_widget, 'process', None)
            if proc is not None and proc.state() != QProcess.ProcessState.NotRunning:
                proc.kill()
                proc.waitForFinished(3000)
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
                self._on_file_opened(path)
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

    def _init_vault(self, vault_path: str):
        self.file_tree.set_vault_path(vault_path)
        self.terminal_widget.set_workdir(vault_path)

        self._progress_bar.show()
        self._progress_bar.setRange(0, 0)
        self.status_info.setText("Initializing vault...")

        self._cleanup_vault_worker()

        self._vault_thread = QThread()
        self._vault_worker = VaultWorker(
            vault_path, self._resolver, self._backlinks, self._search_engine
        )
        self._vault_worker.moveToThread(self._vault_thread)
        self._vault_thread.started.connect(self._vault_worker.run)
        self._vault_worker.finished.connect(self._vault_thread.quit)
        self._vault_worker.finished.connect(self._vault_worker.deleteLater)
        self._vault_thread.finished.connect(self._vault_thread.deleteLater)
        self._vault_worker.progress.connect(self._on_vault_progress)
        self._vault_worker.finished.connect(
            lambda: self._on_vault_finished(vault_path)
        )
        self._vault_thread.start()

    def _on_vault_progress(self, current, total, message):
        if total > 0:
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(current)
        else:
            self._progress_bar.setRange(0, 0)
        self.status_info.setText(message)

    def _on_vault_finished(self, vault_path):
        self._progress_bar.hide()
        all_files = list(self._resolver.all_notes.values())
        self.preview.set_note_map(self._resolver.all_notes)
        self._start_watcher(vault_path)
        self.status_info.setText(
            f"Vault: {len(all_files)} notes"
        )

    def _cleanup_vault_worker(self):
        if hasattr(self, '_vault_worker') and self._vault_worker is not None:
            self._vault_worker.cancel()
            self._vault_worker = None
        if hasattr(self, '_vault_thread') and self._vault_thread is not None:
            if self._vault_thread.isRunning():
                self._vault_thread.quit()
                self._vault_thread.wait(2000)
            self._vault_thread = None

    def _new_note(self):
        self._untitled_counter += 1
        path = f"__untitled_{self._untitled_counter}__"
        self._open_tabs.append(path)
        self._tab_state[path] = {
            "content": "",
            "cursor": (1, 1),
            "scroll": 0,
            "modified": False,
        }
        tidx = self._tab_bar.addTab("untitled.md")
        self._tab_bar.setCurrentIndex(tidx)
        self._tab_bar.setTabData(tidx, path)
        self._switch_to_tab(tidx)

    def _on_tab_rename_requested(self, index: int):
        path = self._tab_bar.tabData(index)
        if not path:
            return
        old_name = os.path.basename(path)
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Rename Tab", "New name:", text=old_name)
        if not ok or not name or name == old_name:
            return
        self._tab_bar.setTabText(index, name)

    def _on_tab_close_others(self, index: int):
        keep_path = self._tab_bar.tabData(index)
        for i in range(self._tab_bar.count() - 1, -1, -1):
            if i != index:
                path = self._tab_bar.tabData(i)
                self._tab_bar.removeTab(i)
                if path in self._open_tabs:
                    self._open_tabs.remove(path)
                if path in self._tab_state:
                    del self._tab_state[path]

    def _on_tab_close_all(self):
        for i in range(self._tab_bar.count() - 1, -1, -1):
            path = self._tab_bar.tabData(i)
            self._tab_bar.removeTab(i)
            if path in self._open_tabs:
                self._open_tabs.remove(path)
            if path in self._tab_state:
                del self._tab_state[path]
        self._new_note()

    def _on_tab_copy_path(self, index: int):
        path = self._tab_bar.tabData(index)
        if path:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(str(path))

    def _tab_index_of(self, path: str) -> int:
        try:
            return self._open_tabs.index(path)
        except ValueError:
            return -1

    def _save_current_tab_state(self):
        path = self._current_file
        if path not in self._tab_state:
            return
        state = self._tab_state[path]
        state["content"] = self.editor.toPlainText()
        state["cursor"] = (
            self.editor.get_current_line(),
            self.editor.get_current_column(),
        )
        scroll = self.editor.verticalScrollBar().value() if self.editor.verticalScrollBar() else 0
        state["scroll"] = scroll

    def _switch_to_tab(self, index: int):
        if index < 0 or index >= self._tab_bar.count():
            return
        path = self._tab_bar.tabData(index)
        if not path or path not in self._tab_state:
            return

        # Save current document before switching
        old_path = self._current_file
        if old_path and old_path in self._tab_state:
            self._tab_state[old_path]["content"] = self.editor.toPlainText()
            self._tab_state[old_path]["scroll"] = (
                self.editor.verticalScrollBar().value() if self.editor.verticalScrollBar() else 0
            )

        self._current_file = path
        state = self._tab_state[path]

        viewer_path = state.get("viewer_path")
        viewer_type = state.get("viewer_type")
        self.editor.blockSignals(True)
        if viewer_path and os.path.isfile(viewer_path):
            if viewer_type == "pdf":
                self.preview.show_pdf(viewer_path)
            else:
                self.preview.show_image(viewer_path)
            self.editor.setPlainText("")
            self.editor.setReadOnly(True)
            self.status_saved.setText("")
        else:
            self.editor.setReadOnly(False)
            self.editor.setPlainText(state["content"])
            if path:
                self.editor.set_language_for_file(path)

            if state["cursor"]:
                line, col = state["cursor"]
                self.editor.set_cursor_position(line, col)
            if state.get("scroll") is not None:
                sb = self.editor.verticalScrollBar()
                if sb:
                    sb.setValue(state["scroll"])

            modified = state.get("modified", False)
            self.status_saved.setText("Unsaved" if modified else "Saved")

            cached = state.get("html")
            if cached:
                self.preview.set_html(cached)
            else:
                self.preview.update_content(state["content"])

        self.editor.blockSignals(False)

        is_untitled = path.startswith("__untitled_") if path else True
        if is_untitled:
            self.setWindowTitle("Zametka")
        else:
            name = os.path.basename(path)
            self.setWindowTitle(f"{name} — Zametka")

        if path and not is_untitled and not viewer_path:
            self.status_info.setText(path)
            backlinks = self._backlinks.get_backlinks(path)
            self.backlinks_panel.update_backlinks(backlinks)
        else:
            self.backlinks_panel.clear()

        is_html = path and not is_untitled and path.lower().endswith((".html", ".htm"))
        self._html_toggle_btn.setVisible(is_html)
        if self._main_stack.currentIndex() == 1:
            if is_html and path and os.path.isfile(path):
                self._browser.load_file(os.path.abspath(path))
            else:
                self._main_stack.setCurrentIndex(0)

    def _on_pinned_item_clicked(self, path: str):
        if os.path.isfile(path):
            self._on_file_opened(path)
        elif os.path.isdir(path):
            self.status_info.setText(f"Pinned folder: {path}")
            config = get_config()
            config.set("vault_path", path)
            self._init_vault(path)

    def _on_notes_open(self, filepath: str):
        w = NoteWindow(filepath)
        w.set_note_map(self._resolver.all_notes)
        w.show()
        w.raise_()

    def _on_tab_switched(self, index: int):
        self._save_current_tab_state()
        self._switch_to_tab(index)

    def _close_tab(self, index: int):
        if index < 0 or index >= self._tab_bar.count():
            return
        path = self._tab_bar.tabData(index)
        self._save_current_tab_state()

        state = self._tab_state.get(path)
        if state and state.get("modified"):
            from PyQt6.QtWidgets import QMessageBox
            name = os.path.basename(path) if path and not path.startswith("__") else "Untitled"
            ret = QMessageBox.question(
                self, "Unsaved changes",
                f"Save changes to {name}?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if ret == QMessageBox.StandardButton.Cancel:
                return
            if ret == QMessageBox.StandardButton.Save:
                if path.startswith("__untitled"):
                    self._save_as()
                else:
                    self._save_current_file()

        self._tab_bar.removeTab(index)
        if path in self._open_tabs:
            self._open_tabs.remove(path)
        if path in self._tab_state:
            del self._tab_state[path]

        if self._tab_bar.count() == 0:
            self._new_note()

    def _show_vault_menu(self):
        menu = QMenu(self)

        act_open_file = QAction("Open File", self)
        act_open_file.triggered.connect(self._open_file_dialog)
        menu.addAction(act_open_file)

        act_create_file = QAction("Create File", self)
        act_create_file.triggered.connect(self._new_note)
        menu.addAction(act_create_file)

        menu.addSeparator()

        act_open_folder = QAction("Open Folder", self)
        act_open_folder.triggered.connect(self._open_vault_dialog)
        menu.addAction(act_open_folder)

        act_close_folder = QAction("Close Folder", self)
        act_close_folder.triggered.connect(self._close_current_vault)
        menu.addAction(act_close_folder)

        menu.addSeparator()

        act_save = QAction("Save", self)
        act_save.triggered.connect(self._save_current_file)
        menu.addAction(act_save)

        act_save_as = QAction("Save As...", self)
        act_save_as.triggered.connect(self._save_as)
        menu.addAction(act_save_as)

        menu.addSeparator()

        config = get_config()
        current_theme = config.get("theme", "dark")
        act_toggle_theme = QAction(
            "Light Theme" if current_theme == "dark" else "Dark Theme", self
        )
        act_toggle_theme.triggered.connect(self._toggle_theme)
        menu.addAction(act_toggle_theme)

        menu.exec(self._vault_menu.mapToGlobal(self._vault_menu.rect().bottomLeft()))

    def _open_file_dialog(self):
        config = get_config()
        vault_path = config.get("vault_path", "")

        # If vault is open, start from vault directory
        start_dir = vault_path if vault_path and os.path.isdir(vault_path) else ""

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", start_dir,
            "Markdown Files (*.md);;All Files (*)"
        )
        if file_path:
            self._on_file_opened(file_path)

    def _close_current_vault(self):
        self._current_file = ""
        if hasattr(self, 'file_tree'):
            self.file_tree.clear_vault()
        config = get_config()
        config.set("vault_path", "")
        self.status_info.setText("Vault closed — open a folder to start")

    def _open_vault_dialog(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Open Vault Folder", "",
            QFileDialog.Option.ShowDirsOnly
        )
        if dir_path:
            config = get_config()
            config.set("vault_path", dir_path)
            self._init_vault(dir_path)
            self.status_info.setText(f"Vault: {dir_path}")

    def _open_handbook(self):
        from zametka_dbs.markdown.md_handbook import get_handbook
        content = get_handbook()
        self._untitled_counter += 1
        path = f"__handbook_{self._untitled_counter}__"
        self._open_tabs.append(path)
        self._tab_state[path] = {
            "content": content,
            "cursor": (1, 1),
            "scroll": 0,
            "modified": False,
        }
        tidx = self._tab_bar.addTab("📖 Handbook.md")
        self._tab_bar.setCurrentIndex(tidx)
        self._tab_bar.setTabData(tidx, path)
        self._switch_to_tab(tidx)
        self.status_info.setText("Handbook opened")

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
            path = self._current_file
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
            self._preview_toggle_btn.setToolTip("Show Preview (Ctrl+P)")
            self._preview_toggle_btn.setIcon(icon("layout"))
        else:
            self._preview_toggle_btn.setToolTip("Hide Preview (Ctrl+P)")
            self._preview_toggle_btn.setIcon(icon("layout"))

    def _on_tab_dragged_out(self, path: str):
        idx = self._tab_index_of(path)
        if idx >= 0:
            self._close_tab(idx)

    def _on_replace_in_file(self, find_text: str, replace_text: str):
        content = self.editor.toPlainText()
        new_content = content.replace(find_text, replace_text)
        if new_content != content:
            cursor = self.editor.textCursor()
            pos = cursor.position()
            self.editor.setPlainText(new_content)
            cursor.setPosition(min(pos, len(new_content)))
            self.editor.setTextCursor(cursor)

    def _on_file_opened(self, path: str):
        idx = self._tab_index_of(path)
        if idx >= 0:
            self._tab_bar.setCurrentIndex(idx)
            return

        ext = os.path.splitext(path)[1].lower()
        if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}:
            name = os.path.basename(path)
            self._save_current_tab_state()
            self._open_tabs.append(path)
            self._tab_state[path] = {
                "content": "",
                "cursor": (1, 1),
                "scroll": 0,
                "modified": False,
                "viewer_path": path,
                "viewer_type": "image",
            }
            tidx = self._tab_bar.addTab(name)
            self._tab_bar.setTabData(tidx, path)
            self._tab_bar.setCurrentIndex(tidx)
            self._switch_to_tab(tidx)
            self.preview.show_image(path)
            return

        if ext == ".pdf":
            name = os.path.basename(path)
            self._save_current_tab_state()
            self._open_tabs.append(path)
            self._tab_state[path] = {
                "content": "",
                "cursor": (1, 1),
                "scroll": 0,
                "modified": False,
                "viewer_path": path,
                "viewer_type": "pdf",
            }
            tidx = self._tab_bar.addTab(name)
            self._tab_bar.setTabData(tidx, path)
            self._tab_bar.setCurrentIndex(tidx)
            self._switch_to_tab(tidx)
            self.preview.show_pdf(path)
            return

        from zametka_dbs.utils.file_size import is_file_too_large, format_size
        if is_file_too_large(path):
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, "Large file",
                f"File is {format_size(path)}. Open anyway? "
                "Large files may cause performance issues.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            self._save_current_tab_state()

            self._open_tabs.append(path)
            self._tab_state[path] = {
                "content": content,
                "cursor": (1, 1),
                "scroll": 0,
                "modified": False,
            }
            name = os.path.basename(path)
            tidx = self._tab_bar.addTab(name)
            self._tab_bar.setTabData(tidx, path)
            self._tab_bar.setCurrentIndex(tidx)
            self._switch_to_tab(tidx)
        except Exception as e:
            self.status_info.setText(f"Error: {e}")

    def _on_wikilink_clicked(self, target: str):
        """Handle click on [[wikilink]] in preview."""
        resolved = self._resolver.resolve(target)
        if resolved:
            self._on_file_opened(resolved)
        else:
            self.status_info.setText(f"Wikilink not found: {target}")

    def _update_status_cursor(self):
        line = self.editor.get_current_line()
        col = self.editor.get_current_column()
        self.status_cursor.setText(f"Ln {line}, Col {col}")

    def _on_preview_rendered(self, html: str):
        if self._current_file in self._tab_state:
            self._tab_state[self._current_file]["html"] = html
        self._sync_editor_scroll_to_preview(force=True)

    def _sync_editor_scroll_to_preview(self, value=None, force=False):
        editor_sb = self.editor.verticalScrollBar()
        preview_sb = self.preview._browser.verticalScrollBar()
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
        self.preview.update_content(self.editor.toPlainText())
        if self._current_file:
            self.status_saved.setText("Unsaved")
            if self._current_file in self._tab_state:
                self._tab_state[self._current_file]["modified"] = True
                self._tab_state[self._current_file].pop("html", None)

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
        self.bus.emit(Events.THEME_CHANGED, theme=theme)

    def _load_stylesheet(self, theme: str = "dark") -> str:
        from zametka_dbs.ui.styles import the_stylesheet
        return the_stylesheet(theme)
