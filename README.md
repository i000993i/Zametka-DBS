# Zametka

Быстрый редактор Markdown-заметок. Ядро на Rust, интерфейс на Python (PyQt6).
Сборка: `Zametka.exe` (скомпилированный Python) + `_internal/` (нативные DLL).

## Возможности

- **Markdown-редактор** с предпросмотром (Ctrl+P) — рендеринг через Rust (comrak) или markdown-it
- **Подсветка синтаксиса** для 40+ языков, автоопределение темы (тёмная/светлая)
- **[[Вики-ссылки]]** с обратными связями (backlinks)
- **Полнотекстовый поиск** по всем заметкам (TF-IDF, Rust)
- **Прикрепление файлов/папок** (Pinned) — быстрый доступ к важному
- **Дерево файлов** с навигацией как в VS Code
- **Просмотр HTML/PDF** — Chromium (QWebEngineView) для `.html`, PyMuPDF для `.pdf/.epub/.cbz`
- **Бейджи** — 201+ значок в 8 категориях с 6 стилями отображения
- **Раздел "Notes"** — коллекция заметок в виде кирпичиков-карточек с бейджами
- **Встроенный терминал** (Ctrl+`) — несколько вкладок, ConPTY (Rust), поддержка UTF-8, кликабельные ссылки/пути
- **Git History** — просмотр изменений, коммитов и диффов (асинхронно, без зависаний)
- **Проверка обновлений** через GitHub (автоматическая при запуске)
- **Переключение языка** (RU/EN) — кнопка в статус-баре
- **Проверка SHA256** при установке — установщик сверяет контрольную сумму скачанного архива

## Ядро на Rust

### `zametka-core` (PyO3-модуль)

| Модуль | Описание |
|---|---|
| `config.rs` | Загрузка/сохранение JSON-конфига, dot-нотация, native Python-типы |
| `search.rs` | Инвертированный индекс, TF-IDF, рекурсивный обход папок |
| `markdown.rs` | Рендеринг MD→HTML через comrak, парсинг `[[wikilinks]]`, backlinks |
| `language.rs` | Определение языка по расширению, сканирование папок (до 5 языков) |

### `zametka-conpty` (PyO3-модуль)

| Модуль | Описание |
|---|---|
| `conpty.rs` | Windows Pseudo Console (ConPTY) — создание, запись, чтение, ресайз |
| `ansi.rs` | Парсер ANSI-escape последовательностей (8/16/256 цветов) |

### `dbs-renderer` (CLI)

Утилита для рендеринга PDF/текстовых страниц в RGBA-изображения (pdf-extract + ab_glyph).

Python-код автоматически использует Rust-модули при наличии; если их нет — прозрачное падение на Python-реализацию.

## Быстрый старт

### Из исходников

```bash
pip install -r requirements.txt
python app.py
```

### Сборка `.exe` + папка `_internal/`

```bash
pip install maturin pyinstaller
python build.py
```

Готовые файлы: `dist/Zametka.exe` (~5-10 МБ, только скомпилированный Python) + `dist/Zametka/_internal/` (DLL, .pyd, ресурсы)

### Сборка Python-установщика

```bash
pip install maturin pyinstaller pywin32
pyinstaller installer/installer.py --onefile --windowed --icon=assets/app_icon.ico --name Zametka-Installer
```

Готовый файл: `dist/Zametka-Installer.exe`

Установщик скачивает последний релиз с GitHub, проверяет SHA256, распаковывает `Zametka.exe` + `_internal/` в выбранную папку, создаёт ярлыки и регистрирует ассоциации файлов.

### Сборка Inno Setup установщика

```bash
iscc installer\setup.iss
```

Готовый файл: `dist/Zametka-Setup-*.exe`

## Горячие клавиши

| Комбинация | Действие |
|---|---|
| `Ctrl+N` | Новая заметка |
| `Ctrl+O` | Открыть папку |
| `Ctrl+S` | Сохранить |
| `Ctrl+P` | Предпросмотр |
| `Ctrl+F` | Поиск |
| `` Ctrl+` `` | Встроенный терминал |
| `Ctrl+Shift+F` | Поиск файлов |
| `Ctrl+Shift+P` | Палитра команд |
| `Ctrl+Shift+S` | Разделить редактор |
| `F11` | На весь экран |

## Обновления

Приложение автоматически проверяет наличие новой версии на GitHub при запуске.
Вручную: меню "О приложении" → "Проверить обновления...".

Версия `v0.2.2` — SHA256-верификация архива, исправление UI-багов.

Релизы публикуются на https://github.com/i000993i/Zametka-DBS/releases

## Структура проекта

```
zametka_dbs/
├── __init__.py
├── __main__.py       # Точка входа: python -m zametka_dbs
├── core/             # Конфиг, EventBus, i18n, rust_bridge, Badges, Version, Updater
│   ├── config.py     #   Config (Rust/Python), type-safe get/set
│   ├── event_bus.py  #   Pub/sub шина (Events.THEME_CHANGED, LANGUAGE_CHANGED, ...)
│   ├── i18n.py       #   Интернационализация (tr(), set_language())
│   ├── rust_bridge.py#   Единая точка импорта zametka_core / zametka_conpty
│   └── badges.py     #   Бейджи, заметки
├── markdown/         # Вики-ссылки, шаблоны, Handbook
├── preview/          # Рендеринг Markdown (Rust / markdown-it)
├── search/           # Поиск (Rust / Python)
└── ui/               # MainWindow, CodeEditor, Preview, FileTree, Pinned,
                      # Backlinks, SearchWidget, NotesBrowser, NoteWindow,
                      # PDF-вьюер (PyMuPDF), Terminal, CommandPalette, GitHistory

zametka-core/         # Rust → PyO3 (zametka_core.pyd)
├── src/
│   ├── config.rs     #   Config: get/set с native Python-типами
│   ├── search.rs     #   SearchIndex: TF-IDF
│   ├── markdown.rs   #   comrak, wikilinks, backlinks
│   └── language.rs   #   detect_language, scan_folder_languages
├── Cargo.toml
└── pyproject.toml

zametka-conpty/       # Rust → PyO3 (zametka_conpty.pyd)
├── src/
│   ├── conpty.rs     #   Windows ConPTY обёртка
│   └── ansi.rs       #   ANSI escape-парсер
├── Cargo.toml
└── pyproject.toml

dbs-renderer/         # Rust CLI — PDF/TXT → PNG
├── src/main.rs
└── Cargo.toml

assets/
├── icons.py          # Загрузчик SVG-иконок с LRU-кэшем
├── svg/              # SVG-иконки
├── lang/             # Файлы переводов (en.json, ru.json)
└── app_icon.ico

installer/            # Установщик
├── installer.py      #   Python-установщик (PyQt6) с SHA256-проверкой
└── setup.iss         #   Inno Setup скрипт
```

## Архитектура

```
app.py / python -m zametka_dbs
  └── MainWindow (QMainWindow)
        ├── ActivityBar (48px): Explorer | Search | Notes | History
        │
        ├── Sidebar (QStackedWidget, 280px)
        │     ├── Page 0: FileTree + Pinned + Backlinks (Explorer)
        │     ├── Page 1: SearchWidget (полнотекстовый поиск)
        │     ├── Page 2: NotesBrowser (карточки с бейджами)
        │     └── Page 3: GitHistory (асинхронный)
        │
        ├── Editor Area
        │     ├── TabBar (DraggableTabBar — перетаскивание, контекстное меню)
        │     ├── Page 0: CodeEditor + Preview (QSplitter)
        │     │     ├── CodeEditor (QPlainTextEdit + LineGutter + SyntaxHighlighter)
        │     │     ├── CodeEditor2 (split-режим)
        │     │     └── PreviewWidget (рендер Markdown, только для .md/.markdown/.mdown)
        │     ├── Page 1: QWebEngineView (Chromium, для .html)
        │     └── Page 2: DocumentViewer (PDF/EPUB через PyMuPDF)
        │
        ├── Terminal (нижняя панель, Ctrl+`, ConPTY, много вкладок, UTF-8)
        │
        ├── StatusBar
        │     ├── Статус сохранения + Позиция курсора + Счётчик слов
        │     ├── Кнопка языка (RU/EN)
        │     └── Полоса прогресса + Информационная строка
        │
        └── CommandPalette (Ctrl+Shift+P, VS Code-style)
```

- **Rust-ядро**: компилируется в `.pyd` через PyO3, встраивается в Python
- **Fallback**: все Rust-модули импортируются через единый `rust_bridge.py`; при ошибке — самодостаточная Python-реализация
- **EventBus**: слабо связанная шина событий (pub/sub) для общения компонентов
- **i18n**: `tr(key)` читает переводы из `assets/lang/{lang}.json`; смена языка через кнопку в статус-баре / `Events.LANGUAGE_CHANGED`
- **NoteWindow**: отдельное `QMainWindow` для каждой открытой заметки
- **Updater**: проверка релизов через GitHub API, автоматическое уведомление
- **SHA256**: установщик вычисляет хеш скачанного архива и сверяет с релизным `.sha256`

## Конфигурация

Файл: `%APPDATA%/Zametka/config.json`

```json
{
  "vault_path": "",
  "theme": "dark",
  "language": "ru",
  "editor": { "font_family": "...", "font_size": 14, ... },
  "ui": { "sidebar_width": 300, ... },
  "pinned": { "items": [] },
  "notes": { "items": [] },
  "badges": { ... }
}
```

## Интернационализация

- Язык по умолчанию: русский (`ru`)
- Кнопка переключения в статус-баре
- Файлы переводов: `assets/lang/en.json`, `assets/lang/ru.json`
- Событие: `Events.LANGUAGE_CHANGED` — подписчики обновляют UI

## Лицензия

MIT
