import os

_THEME_VARS = {
    "dark": {
        "bg0": "#0a0a0a", "bg1": "#121212", "bg2": "#1a1a1a", "bg3": "#2a2a2a",
        "bg4": "#111111", "fg0": "#eeeeee", "fg1": "#a0a0a0", "fg2": "#808080",
        "border": "#1a1a1a", "border2": "#2a2a2a", "sel_bg": "#333333",
    },
    "light": {
        "bg0": "#ffffff", "bg1": "#f0f0f0", "bg2": "#e0e0e0", "bg3": "#cccccc",
        "bg4": "#e8e8e8", "fg0": "#333333", "fg1": "#666666", "fg2": "#888888",
        "border": "#e0e0e0", "border2": "#d0d0d0", "sel_bg": "#dddddd",
    },
}


def the_stylesheet(theme: str = "dark") -> str:
    v = _THEME_VARS.get(theme, _THEME_VARS["dark"])
    close_icon = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "svg", "x.svg").replace("\\", "/")
    return f"""
        QMainWindow {{
            background-color: {v["bg0"]};
        }}
        QFrame#activity-bar {{
            background-color: {v["bg1"]};
            border-right: 1px solid {v["border"]};
        }}
        QPushButton#activity-btn {{
            background-color: transparent;
            color: {v["fg2"]};
            border: none;
            border-left: 2px solid transparent;
            border-radius: 0;
            padding: 0;
        }}
        QPushButton#activity-btn:hover {{
            background-color: {v["bg2"]};
        }}
        QPushButton#activity-btn:checked {{
            background-color: {v["bg2"]};
            color: {v["fg0"]};
            border-left: 2px solid #4a9eff;
        }}
        QPushButton#activity-btn QLabel {{
            color: {v["fg2"]};
            font-size: 10px;
        }}
        QFrame#sidebar {{
            background-color: {v["bg1"]};
            border-right: 1px solid {v["border"]};
        }}
        QWidget#sidebar-header {{
            background-color: {v["bg4"]};
            border-bottom: 1px solid {v["border"]};
        }}
        QLabel#vault-label {{
            color: {v["fg2"]};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        QPushButton#icon-btn {{
            background-color: transparent;
            color: {v["fg2"]};
            border: none;
            border-radius: 2px;
        }}
        QPushButton#icon-btn:hover {{
            background-color: {v["bg2"]};
            color: {v["fg0"]};
        }}
        QLineEdit#file-search-edit {{
            background-color: {v["bg2"]};
            color: {v["fg0"]};
            border: 1px solid {v["border"]};
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 12px;
        }}
        QWidget#tab-row {{
            background-color: {v["bg1"]};
            border-bottom: 1px solid {v["border"]};
        }}
        QTabBar#editor-tabs {{
            background-color: {v["bg1"]};
            border: none;
            font-size: 12px;
        }}
        QTabBar#editor-tabs::tab {{
            background-color: {v["bg1"]};
            color: {v["fg1"]};
            border: none;
            border-right: 1px solid {v["border"]};
            padding: 6px 16px;
            min-width: 60px;
            max-width: 200px;
        }}
        QTabBar#editor-tabs::tab:selected {{
            background-color: {v["bg0"]};
            color: {v["fg0"]};
            border-bottom: 2px solid #4a9eff;
        }}
        QTabBar#editor-tabs::tab:hover:!selected {{
            background-color: {v["bg2"]};
            color: {v["fg0"]};
        }}
        QTabBar#editor-tabs::close-button {{
            image: url("{close_icon}");
            subcontrol-position: right;
            padding: 0 4px;
        }}
        QTabBar#editor-tabs::close-button:hover {{
            background-color: {v["bg3"]};
            border-radius: 2px;
        }}
        QPushButton#tab-btn {{
            background-color: transparent;
            color: {v["fg1"]};
            border: none;
            border-radius: 0;
            padding: 0 8px;
            font-size: 11px;
        }}
        QPushButton#tab-btn:hover {{
            background-color: {v["bg2"]};
            color: {v["fg0"]};
        }}
        QPushButton#tab-btn:checked {{
            background-color: {v["bg2"]};
            color: #4a9eff;
        }}
        QPushButton#tab-btn:disabled {{
            color: {v["fg2"]};
        }}
        QSplitter::handle {{
            background-color: {v["border"]};
        }}
        QSplitter::handle:horizontal {{
            width: 1px;
        }}
        QSplitter::handle:vertical {{
            height: 1px;
        }}
        QFrame#editor-pane, QPlainTextEdit {{
            background-color: {v["bg0"]};
            color: {v["fg0"]};
            border: none;
            font-size: 14px;
            selection-background-color: #264f78;
        }}
        QPlainTextEdit#editor-pane QScrollBar:vertical {{
            width: 8px;
        }}
        QFrame#preview-pane {{
            background-color: {v["bg0"]};
        }}
        QStatusBar#status-bar {{
            background-color: {v["bg1"]};
            color: {v["fg1"]};
            border-top: 1px solid {v["border"]};
            font-size: 11px;
        }}
        QStatusBar QLabel {{
            color: {v["fg1"]};
            font-size: 11px;
            padding: 0 8px;
        }}
        QPushButton#search-btn {{
            background-color: transparent;
            color: {v["fg1"]};
            border: none;
            border-radius: 2px;
            font-size: 11px;
            padding: 2px 6px;
        }}
        QPushButton#search-btn:hover {{
            background-color: {v["bg2"]};
            color: {v["fg0"]};
        }}
        QPushButton#search-btn:checked {{
            color: #4a9eff;
        }}
        QPushButton#terminal-btn {{
            background-color: transparent;
            color: {v["fg1"]};
            border: none;
            border-radius: 2px;
            font-size: 11px;
            padding: 2px 6px;
        }}
        QPushButton#terminal-btn:hover {{
            background-color: {v["bg2"]};
            color: {v["fg0"]};
        }}
        QPushButton#terminal-btn:checked {{
            color: #4a9eff;
        }}
        QProgressBar#status-progress {{
            background-color: {v["bg2"]};
            border: none;
            border-radius: 2px;
            text-align: center;
            font-size: 9px;
            color: {v["fg1"]};
        }}
        QProgressBar#status-progress::chunk {{
            background-color: #4a9eff;
            border-radius: 2px;
        }}
        QFrame#terminal-container {{
            background-color: {v["bg0"]};
            border-top: 1px solid {v["border"]};
        }}
        QStackedWidget#sidebar-stack {{
            background-color: {v["bg1"]};
        }}
        QWidget#search-header {{
            background-color: {v["bg4"]};
            border-bottom: 1px solid {v["border"]};
        }}
        QLabel#search-header-label {{
            color: {v["fg2"]};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        QWidget#search-page {{
            background-color: {v["bg1"]};
        }}
        QWidget#search-widget {{
            background-color: {v["bg1"]};
        }}
        QLineEdit#search-input {{
            background-color: {v["bg2"]};
            color: {v["fg0"]};
            border: 1px solid {v["border"]};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 13px;
        }}
        QLineEdit#search-input:focus {{
            border-color: #4a9eff;
        }}
        QLineEdit#search-input, QLineEdit#replace-input {{
            background-color: {v["bg2"]};
            color: {v["fg0"]};
            border: 1px solid {v["border"]};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 13px;
        }}
        QPushButton#replace-btn {{
            background-color: {v["bg2"]};
            color: {v["fg0"]};
            border: 1px solid {v["border"]};
            border-radius: 3px;
            padding: 2px 8px;
            font-size: 11px;
        }}
        QPushButton#replace-btn:hover {{
            background-color: {v["bg3"]};
        }}
        QListWidget#search-results {{
            background-color: {v["bg1"]};
            color: {v["fg0"]};
            border: none;
            font-size: 12px;
            outline: none;
        }}
        QListWidget#search-results::item {{
            padding: 4px 8px;
            border-bottom: 1px solid {v["border"]};
        }}
        QListWidget#search-results::item:hover {{
            background-color: {v["bg2"]};
        }}
        QListWidget#search-results::item:selected {{
            background-color: {v["sel_bg"]};
        }}
        QWidget#notes-header {{
            background-color: {v["bg4"]};
            border-bottom: 1px solid {v["border"]};
        }}
        QLabel#notes-label {{
            color: {v["fg2"]};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        QWidget#notes-page {{
            background-color: {v["bg1"]};
        }}
        QPushButton#notes-add-btn {{
            background-color: {v["bg2"]};
            color: {v["fg1"]};
            border: 1px solid {v["border2"]};
            border-radius: 3px;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 6px;
        }}
        QPushButton#notes-add-btn:hover {{
            background-color: {v["bg3"]};
            border-color: {v["fg1"]};
            color: {v["fg0"]};
        }}
        QScrollArea#notes-scroll {{
            background: {v["bg0"]};
            border: none;
        }}
        QWidget#backlinks-panel {{
            background-color: {v["bg0"]};
            border-top: 1px solid {v["border"]};
        }}
        QWidget#backlinks-header {{
            background-color: {v["bg0"]};
        }}
        QLabel#backlinks-header-label {{
            color: {v["fg2"]};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        QListWidget#backlinks-list {{
            background-color: {v["bg0"]};
            color: {v["fg2"]};
            font-size: 12px;
            border: none;
            outline: none;
            padding: 2px 0;
        }}
        QListWidget#backlinks-list::item {{
            padding: 2px 8px;
            border: none;
        }}
        QListWidget#backlinks-list::item:hover {{
            background-color: {v["bg2"]};
            color: {v["fg0"]};
        }}
        QWidget#pinned-header {{
            background-color: {v["bg0"]};
            border-bottom: 1px solid {v["border"]};
            border-top: 1px solid {v["border"]};
        }}
        QLabel#pinned-label {{
            color: {v["fg2"]};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        QPushButton#pinned-add-btn {{
            background-color: transparent;
            color: {v["fg2"]};
            border: none;
            border-radius: 2px;
            font-size: 11px;
        }}
        QPushButton#pinned-add-btn:hover {{
            background-color: {v["bg2"]};
            color: {v["fg0"]};
        }}
        QWidget#pinned-item {{
            background-color: transparent;
        }}
        QLabel#pinned-name {{
            font-size: 12px;
            color: {v["fg0"]};
        }}
        QListWidget#pinned-list {{
            background-color: {v["bg0"]};
            border: none;
            color: {v["fg0"]};
            font-size: 12px;
            outline: none;
            max-height: 200px;
        }}
        QListWidget#pinned-list::item {{
            padding: 0;
            border: none;
        }}
        QListWidget#pinned-list::item:hover {{
            background-color: {v["bg2"]};
        }}
        QListWidget#pinned-list::item:selected {{
            background-color: {v["bg2"]};
        }}
        QWidget#preview-widget {{
            background-color: {v["bg0"]};
        }}
        QLabel#preview-header {{
            color: {v["fg2"]};
            font-size: 11px;
            font-weight: 600;
            padding: 4px 8px;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        QTextBrowser#preview-browser {{
            background-color: {v["bg0"]};
            color: {v["fg0"]};
            border: none;
            font-size: 14px;
            padding: 16px;
            selection-background-color: #264f78;
        }}
        QScrollArea#preview-scroll {{
            background-color: {v["bg0"]};
            border: none;
        }}
        QScrollArea#preview-image-scroll {{
            background-color: {v["bg1"]};
            border: none;
        }}
        QLabel#preview-image-label {{
            background-color: transparent;
        }}
        QLabel#preview-text {{
            color: {v["fg1"]};
            font-size: 13px;
        }}
        QWidget#pdf-container {{
            background-color: {v["bg1"]};
        }}
        QPushButton#pdf-prev, QPushButton#pdf-next,
        QPushButton#pdf-zoom-in, QPushButton#pdf-zoom-out {{
            background-color: transparent;
            color: {v["fg1"]};
            border: 1px solid {v["border2"]};
            border-radius: 3px;
            padding: 4px 8px;
            font-size: 12px;
        }}
        QPushButton#pdf-prev:hover, QPushButton#pdf-next:hover,
        QPushButton#pdf-zoom-in:hover, QPushButton#pdf-zoom-out:hover {{
            background-color: {v["bg2"]};
            color: {v["fg0"]};
        }}
        QLabel#pdf-page-label {{
            color: {v["fg1"]};
            font-size: 12px;
        }}
        QTreeView {{
            background-color: {v["bg1"]};
            color: {v["fg0"]};
            border: none;
            font-size: 13px;
            outline: none;
        }}
        QTreeView::item {{
            padding: 2px 4px;
        }}
        QTreeView::item:hover {{
            background-color: {v["bg2"]};
        }}
        QTreeView::item:selected {{
            background-color: {v["sel_bg"]};
            color: {v["fg0"]};
        }}
        QTreeView::branch:has-children:!has-siblings:closed,
        QTreeView::branch:closed:has-children:has-siblings {{
            border-image: none;
            image: none;
        }}
        QTreeView::branch:open:has-children:!has-siblings,
        QTreeView::branch:open:has-children:has-siblings {{
            border-image: none;
            image: none;
        }}
        QWidget#git-history-page {{
            background-color: {v["bg1"]};
        }}
        QPushButton#git-action-btn {{
            background-color: {v["bg2"]};
            color: {v["fg1"]};
            border: 1px solid {v["border2"]};
            border-radius: 3px;
            padding: 4px 8px;
            font-size: 11px;
        }}
        QPushButton#git-action-btn:hover {{
            background-color: {v["bg3"]};
            color: {v["fg0"]};
        }}
        QListWidget#git-list {{
            background-color: {v["bg0"]};
            color: {v["fg0"]};
            border: 1px solid {v["border"]};
            font-size: 12px;
            outline: none;
        }}
        QListWidget#git-list::item {{
            padding: 4px 8px;
            border-bottom: 1px solid {v["border"]};
        }}
        QListWidget#git-list::item:hover {{
            background-color: {v["bg2"]};
        }}
        QTextEdit#git-diff {{
            background-color: {v["bg0"]};
            color: {v["fg0"]};
            border: 1px solid {v["border"]};
            font-family: Consolas, monospace;
            font-size: 12px;
        }}
        QLabel#sidebar-placeholder {{
            color: {v["fg2"]};
            font-size: 12px;
        }}
        QWidget {{
            font-family: 'Segoe UI', system-ui, sans-serif;
        }}
    """
