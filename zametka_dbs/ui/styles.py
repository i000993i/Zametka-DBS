import os


def the_stylesheet(theme: str = "dark") -> str:
    close_icon = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "svg", "x.svg").replace("\\", "/")
    is_dark = theme == "dark"
    if is_dark:
        bg0 = "#0a0a0a"
        bg1 = "#121212"
        bg2 = "#1a1a1a"
        bg3 = "#2a2a2a"
        bg4 = "#111111"
        fg0 = "#eeeeee"
        fg1 = "#a0a0a0"
        fg2 = "#808080"
        border = "#1a1a1a"
        border2 = "#2a2a2a"
        sel_bg = "#333333"
    else:
        bg0 = "#ffffff"
        bg1 = "#f0f0f0"
        bg2 = "#e0e0e0"
        bg3 = "#cccccc"
        bg4 = "#e8e8e8"
        fg0 = "#333333"
        fg1 = "#666666"
        fg2 = "#888888"
        border = "#e0e0e0"
        border2 = "#d0d0d0"
        sel_bg = "#dddddd"
    return f"""
        QMainWindow {{
            background-color: {bg0};
        }}
        QFrame#activity-bar {{
            background-color: {bg1};
            border-right: 1px solid {border};
        }}
        QPushButton#activity-btn {{
            background-color: transparent;
            color: {fg2};
            border: none;
            border-radius: 0;
            padding: 8px 0;
            font-size: 10px;
            text-align: center;
        }}
        QPushButton#activity-btn:hover {{
            background-color: {bg2};
            color: {fg0};
        }}
        QPushButton#activity-btn:checked {{
            background-color: {bg2};
            color: {fg0};
            border-left: 2px solid #4a9eff;
        }}
        QFrame#sidebar {{
            background-color: {bg1};
            border-right: 1px solid {border};
        }}
        QWidget#sidebar-header {{
            background-color: {bg4};
            border-bottom: 1px solid {border};
        }}
        QLabel#vault-label {{
            color: {fg2};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
        }}
        QPushButton#icon-btn {{
            background-color: transparent;
            color: {fg2};
            border: none;
            border-radius: 2px;
        }}
        QPushButton#icon-btn:hover {{
            background-color: {bg2};
            color: {fg0};
        }}
        QLineEdit#file-search-edit {{
            background-color: {bg2};
            color: {fg0};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 12px;
        }}
        QWidget#editor-tab-row {{
            background-color: {bg1};
            border-bottom: 1px solid {border};
        }}
        QTabBar#editor-tabs {{
            background-color: {bg1};
            border: none;
            font-size: 12px;
        }}
        QTabBar#editor-tabs::tab {{
            background-color: {bg1};
            color: {fg1};
            border: none;
            border-right: 1px solid {border};
            padding: 6px 16px;
            min-width: 60px;
            max-width: 200px;
        }}
        QTabBar#editor-tabs::tab:selected {{
            background-color: {bg0};
            color: {fg0};
            border-bottom: 2px solid #4a9eff;
        }}
        QTabBar#editor-tabs::tab:hover:!selected {{
            background-color: {bg2};
            color: {fg0};
        }}
        QTabBar#editor-tabs::close-button {{
            image: url("{close_icon}");
            subcontrol-position: right;
            padding: 0 4px;
        }}
        QPushButton#tab-btn {{
            background-color: transparent;
            color: {fg1};
            border: none;
            border-radius: 0;
            padding: 0 8px;
            font-size: 11px;
        }}
        QPushButton#tab-btn:hover {{
            background-color: {bg2};
            color: {fg0};
        }}
        QPushButton#tab-btn:checked {{
            background-color: {bg2};
            color: #4a9eff;
        }}
        QSplitter::handle {{
            background-color: {border};
        }}
        QSplitter::handle:horizontal {{
            width: 1px;
        }}
        QSplitter::handle:vertical {{
            height: 1px;
        }}
        QPlainTextEdit#editor-pane {{
            background-color: {bg0};
            color: {fg0};
            border: none;
            font-size: 14px;
            selection-background-color: #264f78;
        }}
        QStatusBar {{
            background-color: {bg1};
            color: {fg1};
            border-top: 1px solid {border};
            font-size: 11px;
        }}
        QStatusBar QLabel {{
            color: {fg1};
            font-size: 11px;
            padding: 0 8px;
        }}
        QPushButton#search-btn, QPushButton#terminal-btn {{
            background-color: transparent;
            color: {fg1};
            border: none;
            border-radius: 2px;
            font-size: 11px;
            padding: 2px 6px;
        }}
        QPushButton#search-btn:hover, QPushButton#terminal-btn:hover {{
            background-color: {bg2};
            color: {fg0};
        }}
        QPushButton#search-btn:checked, QPushButton#terminal-btn:checked {{
            color: #4a9eff;
        }}
        QProgressBar#status-progress {{
            background-color: {bg2};
            border: none;
            border-radius: 2px;
            text-align: center;
            font-size: 9px;
            color: {fg1};
        }}
        QProgressBar#status-progress::chunk {{
            background-color: #4a9eff;
            border-radius: 2px;
        }}
        QFrame#terminal-container {{
            background-color: {bg0};
            border-top: 1px solid {border};
        }}
        QStackedWidget#sidebar-stack {{
            background-color: {bg1};
        }}
        QWidget#search-page {{
            background-color: {bg1};
        }}
        QLineEdit#search-input {{
            background-color: {bg2};
            color: {fg0};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 13px;
        }}
        QListWidget#search-results {{
            background-color: {bg1};
            color: {fg0};
            border: none;
            font-size: 12px;
            outline: none;
        }}
        QListWidget#search-results::item {{
            padding: 4px 8px;
            border-bottom: 1px solid {border};
        }}
        QListWidget#search-results::item:hover {{
            background-color: {bg2};
        }}
        QListWidget#search-results::item:selected {{
            background-color: {sel_bg};
        }}
        QWidget#notes-page {{
            background-color: {bg1};
        }}
        QPushButton#notes-add-btn {{
            background-color: {bg2};
            color: {fg1};
            border: 1px solid {border2};
            border-radius: 3px;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 6px;
        }}
        QPushButton#notes-add-btn:hover {{
            background-color: {bg3};
            border-color: {fg1};
            color: {fg0};
        }}
        QScrollArea#notes-scroll {{
            background: {bg0};
            border: none;
        }}
        QScrollArea#notes-scroll QScrollBar:vertical {{
            background: {bg0}; width: 6px; margin: 0;
        }}
        QScrollArea#notes-scroll QScrollBar::handle:vertical {{
            background: {bg2}; min-height: 20px; border-radius: 3px;
        }}
        QScrollArea#notes-scroll QScrollBar::handle:vertical:hover {{
            background: {bg3};
        }}
        QWidget#card-container {{
            background: {bg0};
        }}
    """
