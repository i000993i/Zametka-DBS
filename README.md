# Zametka

Быстрый редактор Markdown-заметок. Ядро на Rust, интерфейс на Python (PyQt6).
Работает из коробки — запустил `.exe` и всё.

## Возможности

- **Markdown-редактор** с предпросмотром (Ctrl+P)
- **Подсветка синтаксиса** для 20+ языков
- **[[Вики-ссылки]]** с обратными связями (backlinks)
- **Полнотекстовый поиск** по всем заметкам (TF-IDF, Rust)
- **Прикрепление файлов/папок** (Pinned) — быстрый доступ к важному
- **Дерево файлов** с навигацией как в VS Code
- **Просмотр HTML** в браузере (Chromium, QWebEngineView)
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

Готовый файл: `dist/Zametka.exe`

## Горячие клавиши

| Комбинация | Действие |
|---|---|
| `Ctrl+N` | Новая заметка |
| `Ctrl+O` | Открыть папку |
| `Ctrl+S` | Сохранить |
| `Ctrl+P` | Предпросмотр |
| `Ctrl+F` | Поиск |
| `F11` | На весь экран |

## Структура проекта

```
zametka_dbs/
├── core/          # Конфиг, EventBus (Rust/Python)
├── markdown/      # Вики-ссылки, шаблоны, Handbook
├── preview/       # Рендеринг Markdown (Rust / markdown-it)
├── search/        # Поиск (Rust / Python)
└── ui/            # MainWindow, CodeEditor, Preview, FileTree, Pinned,
                   # Backlinks, SearchWidget + HTML-браузер (QWebEngineView)

zametka-core/      # Rust-ядро (PyO3)
├── src/
│   ├── config.rs
│   ├── search.rs
│   ├── markdown.rs
│   └── language.rs
├── Cargo.toml
└── pyproject.toml

assets/
└── svg/           # SVG-иконки
```

## Архитектура

```
app.py
  └── MainWindow (QMainWindow)
        ├── Sidebar: Pinned | FileTree | Backlinks | Search
        ├── Editor Area: TabBar (всегда виден) + Stack
        │     ├── Page 0: CodeEditor + Preview (QSplitter)
        │     └── Page 1: QWebEngineView (Chromium, для .html)
        └── StatusBar
```

- **Rust-ядро**: компилируется в `.pyd` через PyO3 встраивается в Python
- **Fallback**: каждый модуль сначала пробует `import zametka_core`; при ошибке — самодостаточная Python-реализация
- **EventBus**: слабо связанная шина событий (pub/sub) для общения компонентов

## Конфигурация

Файл: `%APPDATA%/Zametka/config.json`

| Ключ | Описание |
|---|---|
| `vault_path` | Путь к папке с заметками |
| `editor.font_family` | Шрифт редактора |
| `editor.font_size` | Размер шрифта (14) |
| `pinned.items` | Список закреплённых файлов/папок |

## Лицензия

MIT
