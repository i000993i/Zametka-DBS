# Zametka

A modular note-taking desktop application built with Python and PyQt6, inspired by Obsidian — with Markdown editing, wikilinks, code syntax highlighting, full-text search, and a force-directed graph view.

## Features

- **Markdown editor** with live preview (debounced, 200 ms)
- **Syntax highlighting** for Markdown and 20+ programming languages (Python, JS, TS, HTML, CSS, Java, C++, C#, Go, Rust, SQL, Ruby, PHP, Swift, Kotlin, Dart, Lua, Shell, PowerShell, YAML, TOML, JSON, INI) — auto-detected by file extension
- **[[Wikilinks]]** — cross-note linking with backlinks panel and link resolution (Obsidian-compatible: basename, case-insensitive, subfolder paths)
- **Full-text search** — in-memory TF-ranked search across all vault files with snippet extraction
- **Graph view** — force-directed interactive graph of note connections (drag, zoom, hover, click navigation)
- **Multi-tab editing** — open multiple files simultaneously with per-tab cursor/scroll state
- **Daily notes** with template engine (`{{date}}`, `{{time}}`, `{{title}}`, etc.)
- **File tree** — native file browser with smart filtering (hides `.git`, `node_modules`, `__pycache__`, hidden files, etc.)
- **File watcher** — watchdog-based monitoring for external file changes
- **Dark theme** — opencode-inspired palette (`#0a0a0a` background, `#eeeeee` text, `#808080` muted)
- **Lucide SVG icons** — 13 custom icons with hover states, no emoji
- **Windows file association** — `.md` / `.markdown` / `.mdown` registered as "Open with Zametka"
- **Portable single-file executable** — PyInstaller build available

## Requirements

- Python 3.10+
- PyQt6 >= 6.5
- markdown-it-py >= 3.0
- watchdog >= 4.0

## Quick Start

```bash
pip install -r requirements.txt
python app.py
```

On first launch no vault is opened — click the folder icon in the sidebar to open a note folder, or start typing to create a new note.

## Building Executable

```bash
pip install pyinstaller
pyinstaller --clean --noconfirm Zametka.spec
```

The output is `dist/Zametka.exe`. An `uninstall.cmd` script is provided to clean up Windows registry entries (`Zametka.exe --unregister`).

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New note |
| `Ctrl+O` | Open vault folder |
| `Ctrl+S` | Save current note |
| `Ctrl+F` | Toggle search sidebar |
| `Ctrl+G` | Toggle graph view |
| `F11` | Toggle fullscreen |
| `Esc` | Close search panel |

## Project Structure

```
zametka_dbs/
├── core/           # Config, EventBus, file associations
├── editor/         # (reserved for future plugin-based editors)
├── filesystem/     # (reserved for file watching services)
├── graph/          # NoteGraph, ForceLayout, GraphView (QGraphicsView)
├── markdown/       # Wikilink parser, LinkResolver, BacklinkIndex, templates
├── plugins/        # (reserved for plugin system)
├── preview/        # markdown-it-py → HTML renderer
├── search/         # In-memory full-text search engine
└── ui/             # MainWindow, CodeEditor, Preview, FileTree, Backlinks, Tabs
```

### Key Modules

| Module | File | Purpose |
|--------|------|---------|
| EventBus | `core/event_bus.py` | Typed pub/sub with weakref cleanup |
| Config | `core/config.py` | JSON config in `%APPDATA%/Zametka/config.json` |
| MainWindow | `ui/main_window.py` | Window layout, tabs, save, status bar, shortcuts |
| CodeEditor | `ui/code_editor.py` | QPlainTextEdit with line gutter, active line, language highlighting |
| MarkdownHighlighter | `ui/syntax_highlighter.py` | QSyntaxHighlighter for headings, bold, code, wikilinks, tags |
| LanguageHighlighters | `ui/language_highlighters.py` | 20+ language definitions with opencode syntax colors |
| PreviewWidget | `ui/preview_widget.py` | QTextBrowser with 200 ms debounce, wikilink navigation |
| FileTreeWidget | `ui/file_tree_widget.py` | QTreeView + QSortFilterProxyModel (filters junk files) |
| BacklinksPanel | `ui/backlinks_panel.py` | Shows which notes link to current note |
| GraphView | `ui/graph_view.py` | Force-directed QGraphicsView |
| SearchWidget | `ui/search_widget.py` | QLineEdit + QListWidget with debounced search |
| Renderer | `preview/renderer.py` | markdown-it-py → HTML + CSS |
| Wikilinks | `markdown/wikilinks.py` | Link parsing, resolution, backlink indexing |
| Templates | `markdown/templates.py` | Daily note creation with template variables |
| FileAssoc | `core/file_assoc.py` | Windows registry registration/cleanup |

## Configuration

Config file: `%APPDATA%/Zametka/config.json`

| Key | Default | Description |
|-----|---------|-------------|
| `vault_path` | `""` | Path to the notes folder |
| `editor.font_family` | `"Consolas"` | Monospace font for editor |
| `editor.font_size` | `14` | Editor font size |
| `editor.tab_size` | `4` | Tab width in spaces |
| `editor.word_wrap` | `true` | Enable word wrapping |

## Uninstall

If you used the PyInstaller build:

1. Run `uninstall.cmd` (or `Zametka.exe --unregister`) to remove Windows file associations
2. Delete the application folder
3. (Optional) Delete `%APPDATA%/Zametka/config.json` to remove settings

## License

MIT
