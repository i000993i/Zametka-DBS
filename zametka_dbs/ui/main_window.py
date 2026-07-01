from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QSplitter, QLabel, QStatusBar,
    QScrollArea, QFrame, QPushButton, QFileDialog, QTabBar, QMenu
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QKeySequence, QShortcut, QAction
import os
import threading

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
from zametka_dbs.ui.html_browser import HtmlBrowser
from zametka_dbs.markdown.wikilinks import LinkResolver, BacklinkIndex
from zametka_dbs.search.engine import SearchEngine


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

        self._init_window()
        self._create_sidebar()
        self._create_editor_area()
        self._create_status_bar()
        self._setup_layout()

        self._connect_signals()
        self._setup_shortcuts()
        self.bus.emit(Events.APP_READY)

    def _init_window(self):
        self.setWindowTitle("Zametka")
        self.setMinimumSize(1000, 600)
        self.resize(1400, 850)
        self.setStyleSheet(self._load_stylesheet())

    def _create_title_bar(self):
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

    def _create_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

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
        header_label = QLabel("VAULT")
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

        sidebar_layout.addWidget(header)

        # Pinned section
        self.pinned_widget = PinnedWidget()
        self.pinned_widget.item_clicked.connect(self._on_pinned_item_clicked)
        sidebar_layout.addWidget(self.pinned_widget)

        self.file_tree = FileTreeWidget()
        sidebar_layout.addWidget(self.file_tree, 1)

        self.backlinks_panel = BacklinksPanel()
        sidebar_layout.addWidget(self.backlinks_panel)

        self.search_widget = SearchWidget(self._search_engine)
        self.search_widget.setVisible(False)
        sidebar_layout.addWidget(self.search_widget)

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

        self._tab_bar = QTabBar()
        self._tab_bar.setObjectName("editor-tabs")
        self._tab_bar.setTabsClosable(True)
        self._tab_bar.setDrawBase(False)
        self._tab_bar.setExpanding(False)
        self._tab_bar.setUsesScrollButtons(True)
        self._tab_bar.tabCloseRequested.connect(self._close_tab)
        self._tab_bar.currentChanged.connect(self._on_tab_switched)
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

        self.editor = CodeEditor()
        self.editor.setObjectName("editor-pane")
        self.splitter.addWidget(self.editor)

        self.preview = PreviewWidget()
        self.splitter.addWidget(self.preview)
        self.splitter.setSizes([700, 500])

        editor_layout.addWidget(self.splitter)
        self._main_stack.addWidget(self._editor_page)

        # Page 1: WebEngine browser for HTML preview
        self._browser = HtmlBrowser()
        self._main_stack.addWidget(self._browser)

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

        self.status_info = QLabel("Ready")

        self.status_bar.addWidget(self.status_saved)
        self.status_bar.addPermanentWidget(self._search_btn)
        self.status_bar.addPermanentWidget(self.status_cursor)
        self.status_bar.addPermanentWidget(self.status_words)
        self.status_bar.addPermanentWidget(self.status_font)
        self.status_bar.addPermanentWidget(self.status_info)

        self.setStatusBar(self.status_bar)

    def _setup_layout(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar.setFixedWidth(300)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.editor_area, 1)

        self.setCentralWidget(widget)

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

    def _save_current_file(self):
        if not self._current_file:
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
        self.file_tree.file_opened.connect(self._on_file_opened)
        self.preview.wikilink_clicked.connect(self._on_wikilink_clicked)
        self.backlinks_panel.backlink_clicked.connect(self._on_file_opened)
        self.search_widget.result_clicked.connect(self._on_file_opened)

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
        super().closeEvent(event)

    def _init_vault(self, vault_path: str):
        self.file_tree.set_vault_path(vault_path)
        self._resolver.set_vault_path(vault_path)

        # Index all files for backlinks
        all_files = list(self._resolver.all_notes.values())
        self._backlinks.rebuild_all(all_files)

        # Index all files for search
        self._search_engine.index_vault(vault_path)

        self._start_watcher(vault_path)

        self.status_info.setText(
            f"Vault: {len(all_files)} notes"
        )

    def _new_note(self):
        self._untitled_counter += 1
        path = f"__untitled_{self._untitled_counter}__"
        self._open_tabs.append(path)
        self._tab_state[path] = {
            "content": "",
            "cursor": (1, 1),
            "scroll": 0,
            "modified": True,
        }
        tidx = self._tab_bar.addTab("untitled.md")
        self._tab_bar.setCurrentIndex(tidx)
        self._tab_bar.setTabData(tidx, path)
        self._switch_to_tab(tidx)

    def _tab_index_of(self, path: str) -> int:
        try:
            return self._open_tabs.index(path)
        except ValueError:
            return -1

    def _save_current_tab_state(self):
        path = self._current_file
        if path not in self._tab_state:
            return
        self._tab_state[path]["content"] = self.editor.toPlainText()
        self._tab_state[path]["cursor"] = (
            self.editor.get_current_line(),
            self.editor.get_current_column(),
        )
        scroll = self.editor.verticalScrollBar().value() if self.editor.verticalScrollBar() else 0
        self._tab_state[path]["scroll"] = scroll

    def _switch_to_tab(self, index: int):
        if index < 0 or index >= self._tab_bar.count():
            return
        path = self._tab_bar.tabData(index)
        if not path or path not in self._tab_state:
            return
        self._current_file = path
        state = self._tab_state[path]

        self.editor.setPlainText(state["content"])
        if path:
            self.editor.set_language_for_file(path)

        if state["cursor"]:
            line, col = state["cursor"]
            self.editor.set_cursor_position(line, col)
        if state["scroll"]:
            sb = self.editor.verticalScrollBar()
            if sb:
                sb.setValue(state["scroll"])

        modified = state.get("modified", False)
        self.status_saved.setText("Unsaved" if modified else "Saved")

        is_untitled = path.startswith("__untitled_") if path else True
        if is_untitled:
            self.setWindowTitle("Zametka")
        else:
            name = os.path.basename(path)
            self.setWindowTitle(f"{name} — Zametka")

        if path and not is_untitled:
            self.status_info.setText(path)
            backlinks = self._backlinks.get_backlinks(path)
            self.backlinks_panel.update_backlinks(backlinks)
        else:
            self.backlinks_panel.clear()

        self.preview.update_content(state["content"])

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
            old_vault = config.get("vault_path", "")
            if old_vault and os.path.isdir(old_vault):
                self.file_tree.navigate_to_folder(path)
            else:
                config.set("vault_path", path)
                self._init_vault(path)

    def _on_tab_switched(self, index: int):
        self._save_current_tab_state()
        self._switch_to_tab(index)

    def _close_tab(self, index: int):
        if index < 0 or index >= self._tab_bar.count():
            return
        path = self._tab_bar.tabData(index)
        self._save_current_tab_state()

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
        visible = self.search_widget.isVisible()
        self.search_widget.setVisible(not visible)
        if not visible:
            self._backlinks_visible = self.backlinks_panel.isVisible()
            self.backlinks_panel.setVisible(False)
            self.search_widget.focus()
        else:
            self.backlinks_panel.setVisible(self._backlinks_visible)

    def _toggle_html_view(self):
        if self._main_stack.currentIndex() == 0:
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

    def _on_file_opened(self, path: str):
        idx = self._tab_index_of(path)
        if idx >= 0:
            self._tab_bar.setCurrentIndex(idx)
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

    def _on_editor_changed(self):
        count = self.editor.word_count()
        self.status_words.setText(f"Words: {count}")
        self.preview.update_content(self.editor.toPlainText())
        if self._current_file:
            self.status_saved.setText("Unsaved")
            if self._current_file in self._tab_state:
                self._tab_state[self._current_file]["modified"] = True

    def _load_stylesheet(self) -> str:
        close_icon = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "svg", "x.svg").replace("\\", "/")
        return """
            QMainWindow {
                background-color: #0a0a0a;
            }
            QFrame#sidebar {
                background-color: #0a0a0a;
                border-right: 1px solid #1a1a1a;
            }
            QFrame#sidebar-header {
                border-bottom: 1px solid #1a1a1a;
                background-color: #0a0a0a;
            }
            QLabel#vault-label {
                color: #808080;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
                text-transform: uppercase;
            }
            QPushButton#icon-btn {
                background-color: transparent;
                color: #808080;
                border: none;
                border-radius: 3px;
                font-size: 13px;
                padding: 0;
            }
            QPushButton#icon-btn:hover {
                background-color: #1a1a1a;
                color: #eeeeee;
            }
            QLabel#sidebar-placeholder {
                font-size: 13px;
                color: #808080;
            }
            QWidget#tab-row {
                background-color: #0a0a0a;
                border-bottom: 1px solid #1a1a1a;
            }
            QTabBar#editor-tabs {
                background-color: #0a0a0a;
                border: none;
            }
            QTabBar#editor-tabs::tab {
                background-color: #0a0a0a;
                color: #808080;
                font-size: 12px;
                padding: 4px 14px;
                margin: 0;
                border: none;
                border-right: 1px solid #1a1a1a;
                border-bottom: 2px solid transparent;
                min-height: 26px;
            }
            QTabBar#editor-tabs::tab:selected {
                color: #eeeeee;
                border-bottom: 2px solid #fab283;
            }
            QTabBar#editor-tabs::tab:hover:!selected {
                background-color: #111111;
            }
            QTabBar#editor-tabs::close-button {
                background-color: transparent;
                image: url(""" + close_icon + """);
                width: 16px;
                height: 16px;
                margin: 0 2px;
                border-radius: 3px;
            }
            QTabBar#editor-tabs::close-button:hover {
                background-color: #2a2a2a;
            }
            QPushButton#tab-btn {
                background-color: transparent;
                color: #808080;
                border: 1px solid #1a1a1a;
                border-radius: 4px;
                font-size: 11px;
                padding: 0 10px;
                margin: 4px 0;
            }
            QPushButton#tab-btn:hover {
                background-color: #1a1a1a;
                color: #eeeeee;
            }
            QFrame#editor-pane, QPlainTextEdit {
                background-color: #0a0a0a;
                border: none;
                color: #eeeeee;
                font-family: "Cascadia Code", "Consolas", monospace;
                font-size: 14px;
                selection-background-color: #333333;
            }
            QFrame#preview-pane {
                background-color: #0a0a0a;
                border-left: 1px solid #1a1a1a;
            }
            QLabel#preview-header {
                color: #808080;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
                text-transform: uppercase;
                padding: 6px 14px;
                border-bottom: 1px solid #1a1a1a;
                background-color: #0a0a0a;
            }
            QScrollArea#preview-scroll {
                background-color: #0a0a0a;
                border: none;
            }
            QScrollArea#preview-scroll QWidget {
                background-color: #0a0a0a;
            }
            QLabel#preview-text {
                font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif;
                font-size: 14px;
                line-height: 1.7;
                color: #eeeeee;
                background-color: transparent;
            }
            QStatusBar#status-bar {
                background-color: #121212;
                border-top: 1px solid #2a2a2a;
                color: #a0a0a0;
                font-size: 11px;
                padding: 0 14px;
            }
            QStatusBar#status-bar QLabel {
                color: #a0a0a0;
                font-size: 11px;
                padding: 0 8px;
            }
            QPushButton#search-btn {
                background-color: #1a1a1a;
                color: #808080;
                border: none;
                border-radius: 3px;
                padding: 0 8px;
                font-size: 11px;
            }
            QPushButton#search-btn:hover {
                background-color: #2a2a2a;
                color: #eeeeee;
            }
            QStackedWidget {
                background-color: #0a0a0a;
                border: none;
            }
            QSplitter::handle {
                background-color: #1a1a1a;
            }
            QSplitter::handle:hover {
                background-color: #fab283;
            }
            QScrollBar:vertical {
                background-color: #0a0a0a;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #1a1a1a;
                min-height: 30px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #2a2a2a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """
