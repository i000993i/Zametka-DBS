# Zametka

Быстрый редактор Markdown-заметок. Ядро на Rust, интерфейс на Python (PyQt6).
Работает из коробки — запустил `.exe` и всё.

## Возможности

- **Markdown-редактор** с предпросмотром (Ctrl+P)
- **Подсветка синтаксиса** для 20+ языков, автоопределение темы (тёмная/светлая)
- **[[Вики-ссылки]]** с обратными связями (backlinks)
- **Полнотекстовый поиск** по всем заметкам (TF-IDF, Rust)
- **Прикрепление файлов/папок** (Pinned) — быстрый доступ к важному
- **Дерево файлов** с навигацией как в VS Code
- **Просмотр HTML** в браузере (Chromium, QWebEngineView)
- **Бейджи** — 201 значок в 8 категориях с 6 стилями отображения
- **Раздел "Notes"** — коллекция заметок в виде кирпичиков-карточек с бейджами
- **Окно заметки** — просмотр/редактирование файла в отдельном окне
- **Встроенный терминал** (Ctrl+`) — несколько вкладок, кликабельные ссылки/пути
- **Проверка обновлений** через GitHub (автоматическая при запуске)
- **Сборка в единый `.exe`** — несмотря на Rust-ядро, всё упаковывается в один файл

## Ядро на Rust

| Модуль | Описание |
|---|---|
| `config.rs` | Загрузка/сохранение JSON-конфига (serde_json) |
| `search.rs` | Инвертированный индекс, TF-IDF, рекурсивный обход папок |
| `markdown.rs` | Рендеринг MD→HTML через comrak, парсинг `[[wikilinks]]`, backlinks |
| `language.rs` | Определение языка по расширению, сканирование папок (до 5 языков) |

Python-код автоматически использует Rust-модуль при наличии; если его нет — прозрачное падение на Python-реализацию.

## Быстрый старт

### Из исходников

```bash
pip install -r requirements.txt
python app.py
```

### Сборка `.exe`

```bash
pip install maturin pyinstaller
python build.py
```

Готовый файл: `dist/Zametka/Zametka.exe`

### Сборка `.exe` + установщик

```bash
pip install maturin pyinstaller winshell pywin32
python build.py --installer
```

Готовые файлы: `dist/Zametka/Zametka.exe` + `dist/Zametka-Installer.exe`

### Сборка установщика

**Вариант A — Inno Setup:**
```bash
iscc installer\setup.iss
```
Готовый файл: `dist/Zametka-Setup-*.exe`

**Вариант B — Python-установщик:**
```bash
pip install pyinstaller winshell pywin32
pyinstaller installer/installer.py --onefile --windowed --icon=assets/app_icon.ico --name Zametka-Installer
```
Готовый файл: `dist/Zametka-Installer.exe`

## Горячие клавиши

| Комбинация | Действие |
|---|---|
| `Ctrl+N` | Новая заметка |
| `Ctrl+O` | Открыть папку |
| `Ctrl+S` | Сохранить |
| `Ctrl+P` | Предпросмотр |
| `Ctrl+F` | Поиск |
| `Ctrl+` ` | Встроенный терминал |
| `Ctrl+Shift+F` | Поиск файлов |
| `Ctrl+Shift+P` | Палитра команд |
| `Ctrl+Shift+S` | Разделить редактор |
| `F11` | На весь экран |

## Обновления

Приложение автоматически проверяет наличие новой версии на GitHub при запуске.
Вручную: меню "О приложении" → "Проверить обновления...".

Релизы публикуются на https://github.com/i000993i/Zametka-DBS/releases

## Структура проекта

```
zametka_dbs/
├── core/          # Конфиг, EventBus, Badges, Version, Updater (Rust/Python)
├── markdown/      # Вики-ссылки, шаблоны, Handbook
├── preview/       # Рендеринг Markdown (Rust / markdown-it)
├── search/        # Поиск (Rust / Python)
└── ui/            # MainWindow, CodeEditor, Preview, FileTree, Pinned,
                   # Backlinks, SearchWidget, NotesBrowser, NoteWindow,
                   # HTML-браузер (QWebEngineView), Terminal

zametka-core/      # Rust-ядро (PyO3)
├── src/
│   ├── config.rs
│   ├── search.rs
│   ├── markdown.rs
│   └── language.rs
├── Cargo.toml
└── pyproject.toml

installer/         # Установщик
├── installer.py   #  Python-установщик (PyQt6)
└── setup.iss      #  Inno Setup скрипт

assets/
└── svg/           # SVG-иконки
```

## Архитектура

```
app.py
  └── MainWindow (QMainWindow)
        ├── Sidebar (QStackedWidget)
        │     ├── Page 0: Pinned + FileTree + Backlinks (Explorer)
        │     ├── Page 1: SearchWidget
        │     └── Page 2: NotesBrowser (карточки-кирпичи)
        ├── ActivityBar (48px): Explorer | Search | Notes
        ├── Editor Area: TabBar + Stack
        │     ├── Page 0: CodeEditor + Preview (QSplitter)
        │     └── Page 1: QWebEngineView (Chromium, для .html)
        ├── Terminal (нижняя панель, Ctrl+`, много вкладок)
        └── StatusBar
```

- **Rust-ядро**: компилируется в `.pyd` через PyO3, встраивается в Python
- **Fallback**: каждый модуль сначала пробует `import zametka_core`; при ошибке — самодостаточная Python-реализация
- **EventBus**: слабо связанная шина событий (pub/sub) для общения компонентов
- **NoteWindow**: отдельное `QMainWindow` для каждой открытой заметки
- **Updater**: проверка релизов через GitHub API, автоматическое уведомление

## Конфигурация

Файл: `%APPDATA%/Zametka/config.json`

## Лицензия

MIT
