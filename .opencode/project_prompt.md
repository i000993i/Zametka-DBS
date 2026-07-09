# ========================================================================
# ZAMETKA-DBS — ПРОМТ ДЛЯ РАЗРАБОТКИ
# ========================================================================
# Версия: 1.1 (актуально на 2026-07-09)
# ========================================================================

Ты — эксперт по Python, PyQt6 и Rust. Zametka-DBS — редактор Markdown-заметок
с опциональным ядром на Rust (PyO3) и интерфейсом на PyQt6.

## КЛЮЧЕВЫЕ ХАРАКТЕРИСТИКИ:
- Markdown-редактор с предпросмотром
- Подсветка синтаксиса для 20+ языков (только `.md` — MarkdownHighlighter, остальные — LanguageHighlighter или NullHighlighter)
- [[Вики-ссылки]] через LinkResolver
- Полнотекстовый поиск (TF-IDF, Python, опционально Rust)
- Pinned-файлы/папки (быстрый доступ)
- Дерево файлов (как в VS Code)
- Просмотр HTML через QWebEngineView
- Бейджи (201 значок, 8 категорий, 6 стилей)
- Notes — карточки заметок с бейджами
- NoteWindow — отдельное окно для просмотра файла
- Проверка обновлений через GitHub API
- Сборка в .exe (PyInstaller)

## ФАЙЛЫ ПРОЕКТА (ТОЛЬКО СУЩЕСТВУЮЩИЕ):

```
zametka_dbs/
├── __init__.py
├── __main__.py
├── core/
│   ├── __init__.py
│   ├── config.py          # Загрузка/сохранение config.json
│   ├── event_bus.py       # Шина событий (get_bus — синглтон)
│   ├── badges.py          # Система бейджей
│   ├── version.py         # version, repo, api_url
│   ├── updater.py         # Проверка обновлений GitHub
│   ├── rust_bridge.py     # try: from zametka_core import ...
│   ├── i18n.py            # tr(), set_language()
│   └── file_assoc.py      # Регистрация .md/.zametka
├── markdown/
│   ├── __init__.py
│   ├── wikilinks.py       # parse_wikilinks, LinkResolver (BacklinkIndex удалён)
│   └── md_handbook.py     # handbook.md
├── preview/
│   ├── __init__.py
│   ├── renderer.py        # render_markdown(text, note_map, dark) → html
│   └── styles.py          # _preview_css, process_tags, process_callouts
├── search/
│   ├── __init__.py
│   └── engine.py          # SearchEngine (Tf-idf)
├── utils/
│   ├── __init__.py
│   └── file_size.py       # is_file_too_large, format_size
└── ui/
    ├── __init__.py
    ├── main_window.py     # ~1375 строк, MainWindow(QMainWindow)
    ├── code_editor.py     # CodeEditor, NullHighlighter
    ├── syntax_highlighter.py  # MarkdownHighlighter
    ├── language_highlighters.py  # LanguageHighlighter + get_highlighter_for_file
    ├── preview_widget.py  # PreviewWidget(QTextBrowser)
    ├── document_viewer.py # DocumentViewer (PDF, изображения)
    ├── html_browser.py    # HtmlBrowser(QWebEngineView)
    ├── file_tree_widget.py # FileTreeWidget(QTreeView)
    ├── pinned_widget.py   # PinnedWidget (закреплённые)
    ├── notes_browser.py   # NotesBrowser (карточки)
    ├── note_window.py     # NoteWindow(QMainWindow)
    ├── git_history.py     # GitHistoryWidget
    ├── search_widget.py   # SearchWidget
    ├── command_palette.py # CommandPalette
    ├── activity_bar.py    # ActivityBar (48px)
    ├── draggable_tab_bar.py  # DraggableTabBar
    ├── line_gutter.py     # LineGutter (номера строк)
    ├── vault_worker.py    # VaultWorker(QThread)
    └── styles.py          # _THEME_VARS, the_stylesheet()
```

## АРХИТЕКТУРА:

```
app.py
└── MainWindow (QMainWindow)
    ├── ActivityBar (48px): Explorer | Search | Notes | Git
    ├── Sidebar (QStackedWidget, 280px)
    │   ├── Page 0: Explorer (header + file_search + FileTree + PinnedWidget)
    │   ├── Page 1: SearchWidget
    │   ├── Page 2: NotesBrowser
    │   └── Page 3: GitHistoryWidget
    ├── Editor Area
    │   ├── TabRow (DraggableTabBar + кнопки)
    │   └── MainStack
    │       ├── Page 0: QSplitter [CodeEditor | CodeEditor2 | PreviewWidget]
    │       └── Page 1: HtmlBrowser (ленивый)
    └── StatusBar (search_btn, status_info, lang_btn, saved, cursor, words)
```

## ПРИНЦИПЫ:
1. Fallback: `try: from zametka_core import X` → `except ImportError: pass` (Python-реализация)
2. EventBus — `get_bus()` (синглтон), методы `.emit()`, `.subscribe()`, `Events.*`
3. Долгие операции — QThread / QTimer.setSingleShot, не блокировать UI
4. Поддержка тёмной/светлой темы через `_THEME_VARS[theme]["ключ"]`
5. Type hints добавлены во все UI-файлы (`from __future__ import annotations`)
6. NO терминал — zametka-conpty удалён
7. NO BacklinkIndex — удалён (только LinkResolver для [[вики-ссылок]])

## ЦВЕТА (ТЁМНАЯ):
- bg0: #1e1e1e, bg1: #2d2d2d, bg2: #373737
- fg0: #d4d4d4, fg1: #cccccc, fg2: #9d9d9d
- border: #3c3c3c, border2: #4a4a4a
- sel_bg: #264f78, accent: #0e639c, accent_hover: #1177bb

## СТИЛЬ КОДА:
- snake_case для функций/переменных, CamelCase для классов
- f-строки, макс 100 символов
- Импорты: stdlib → PyQt6 → локальные
- Докстринги — Google Style (только для публичных функций)
- Абсолютные импорты (`from zametka_dbs.core.event_bus import get_bus`)
