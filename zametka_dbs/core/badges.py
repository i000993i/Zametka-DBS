import os
import logging

logger = logging.getLogger(__name__)

_PILL_BADGES = {
    "Stable", "Beta", "Deprecated", "Experimental", "Archived",
    "WIP", "Draft", "TODO", "Online", "Away", "Busy", "Offline",
    "Open Source",
}

_OUTLINE_BADGES = {
    "Verified", "Featured", "Premium", "Pro",
}

_GLOW_BADGES = {
}

_GRADIENT_BADGES: dict[str, tuple[str, str]] = {
}

BADGE_CATEGORIES: dict[str, list[dict]] = {
    "Status": [
        {"label": "Stable", "color": "#3fb950", "bg": "#1a472a"},
        {"label": "Beta", "color": "#58a6ff", "bg": "#1c2b41"},
        {"label": "Deprecated", "color": "#f85149", "bg": "#2d1b1b"},
        {"label": "Experimental", "color": "#e3b341", "bg": "#2d2416"},
        {"label": "Archived", "color": "#8b949e", "bg": "#21262d"},
        {"label": "WIP", "color": "#e3b341", "bg": "#2d2416"},
        {"label": "Draft", "color": "#58a6ff", "bg": "#1c2b41"},
        {"label": "TODO", "color": "#8b949e", "bg": "#21262d"},
        {"label": "Verified", "color": "#3fb950", "bg": "#1a472a"},
        {"label": "Featured", "color": "#e3b341", "bg": "#2d2416"},
        {"label": "Online", "color": "#3fb950", "bg": "#1a472a"},
        {"label": "Away", "color": "#e3b341", "bg": "#2d2416"},
        {"label": "Busy", "color": "#f85149", "bg": "#2d1b1b"},
        {"label": "Offline", "color": "#8b949e", "bg": "#21262d"},
        {"label": "Open Source", "color": "#3fb950", "bg": "#1a472a"},
        {"label": "Premium", "color": "#a371f7", "bg": "#271c3d"},
        {"label": "Pro", "color": "#a371f7", "bg": "#271c3d"},
    ],
    "Framework": [
        {"label": "React", "color": "#61dafb", "bg": "#20232a"},
        {"label": "Vue", "color": "#41b883", "bg": "#34495e"},
        {"label": "Angular", "color": "#dd0031", "bg": "#1a1a1a"},
        {"label": "Svelte", "color": "#ff3e00", "bg": "#1a1a1a"},
        {"label": "Next.js", "color": "#fff", "bg": "#000"},
        {"label": "Nuxt", "color": "#00dc82", "bg": "#1a1a1a"},
        {"label": "Django", "color": "#092e20", "bg": "#e8e8e8"},
        {"label": "Flask", "color": "#fff", "bg": "#000"},
        {"label": "FastAPI", "color": "#009688", "bg": "#1a1a2e"},
        {"label": "Spring", "color": "#6db33f", "bg": "#1a1a2e"},
        {"label": "Express", "color": "#fff", "bg": "#1a1a2e"},
        {"label": "Rails", "color": "#cc342d", "bg": "#1a1a2e"},
        {"label": "Laravel", "color": "#ff2d20", "bg": "#1a1a2e"},
        {"label": "ASP.NET", "color": "#512bd4", "bg": "#1a1a2e"},
        {"label": "Flutter", "color": "#02569b", "bg": "#1a1a2e"},
        {"label": "Tauri", "color": "#ffc131", "bg": "#1a1a2e"},
    ],
    "Database": [
        {"label": "PostgreSQL", "color": "#336791", "bg": "#1a1a2e"},
        {"label": "MySQL", "color": "#00758f", "bg": "#1a1a2e"},
        {"label": "MongoDB", "color": "#47a248", "bg": "#1a1a2e"},
        {"label": "Redis", "color": "#dc382d", "bg": "#1a1a2e"},
        {"label": "SQLite", "color": "#003b57", "bg": "#1a1a2e"},
        {"label": "Elasticsearch", "color": "#f7b93e", "bg": "#1a1a2e"},
        {"label": "MariaDB", "color": "#01529e", "bg": "#1a1a2e"},
        {"label": "DynamoDB", "color": "#4053d6", "bg": "#1a1a2e"},
        {"label": "Firebase", "color": "#ffca28", "bg": "#1a1a2e"},
        {"label": "Supabase", "color": "#3ecf8e", "bg": "#1a1a2e"},
    ],
    "DevOps": [
        {"label": "Docker", "color": "#2496ed", "bg": "#1a1a2e"},
        {"label": "Kubernetes", "color": "#326ce5", "bg": "#1a1a2e"},
        {"label": "AWS", "color": "#ff9900", "bg": "#1a1a2e"},
        {"label": "Azure", "color": "#0078d4", "bg": "#1a1a2e"},
        {"label": "GCP", "color": "#4285f4", "bg": "#1a1a2e"},
        {"label": "Terraform", "color": "#7b42bc", "bg": "#1a1a2e"},
        {"label": "GitHub Actions", "color": "#2088ff", "bg": "#1a1a2e"},
        {"label": "Jenkins", "color": "#d24939", "bg": "#1a1a2e"},
        {"label": "Grafana", "color": "#f46800", "bg": "#1a1a2e"},
        {"label": "Prometheus", "color": "#e6522c", "bg": "#1a1a2e"},
        {"label": "Nginx", "color": "#009639", "bg": "#1a1a2e"},
        {"label": "Ansible", "color": "#ee0000", "bg": "#1a1a2e"},
    ],
    "Tool": [
        {"label": "Git", "color": "#f05032", "bg": "#1a1a2e"},
        {"label": "VS Code", "color": "#0078d7", "bg": "#1a1a2e"},
        {"label": "Webpack", "color": "#8dd6f9", "bg": "#1a1a2e"},
        {"label": "Vite", "color": "#646cff", "bg": "#1a1a2e"},
        {"label": "Jest", "color": "#99425b", "bg": "#1a1a2e"},
        {"label": "Cypress", "color": "#69d3a7", "bg": "#1a1a2e"},
        {"label": "ESLint", "color": "#4b32c3", "bg": "#1a1a2e"},
        {"label": "Prettier", "color": "#f7b93e", "bg": "#1a1a2e"},
        {"label": "Babel", "color": "#f9dc3e", "bg": "#1a1a2e"},
        {"label": "Rollup", "color": "#ec4a3e", "bg": "#1a1a2e"},
    ],
    "CI/CD": [
        {"label": "Passing", "color": "#3fb950", "bg": "#1a472a"},
        {"label": "Failing", "color": "#f85149", "bg": "#2d1b1b"},
        {"label": "Running", "color": "#e3b341", "bg": "#2d2416"},
        {"label": "Skipped", "color": "#8b949e", "bg": "#21262d"},
        {"label": "Cancelled", "color": "#8b949e", "bg": "#21262d"},
        {"label": "Coverage 90+", "color": "#3fb950", "bg": "#1a472a"},
        {"label": "Coverage 70+", "color": "#e3b341", "bg": "#2d2416"},
        {"label": "Coverage <70", "color": "#f85149", "bg": "#2d1b1b"},
    ],
    "Topic": [
        {"label": "#react", "color": "#58a6ff", "bg": "#1c2b41", "style": "pill"},
        {"label": "#python", "color": "#58a6ff", "bg": "#1c2b41", "style": "pill"},
        {"label": "#typescript", "color": "#a5d6ff", "bg": "#1c2b41", "style": "pill"},
        {"label": "#javascript", "color": "#a5d6ff", "bg": "#1c2b41", "style": "pill"},
        {"label": "#opensource", "color": "#56d364", "bg": "#1a472a", "style": "pill"},
        {"label": "#devops", "color": "#e3b341", "bg": "#2d2416", "style": "pill"},
        {"label": "#hacktoberfest", "color": "#d2a8ff", "bg": "#271c3d", "style": "pill"},
        {"label": "#ai", "color": "#58a6ff", "bg": "#1c2b41", "style": "pill"},
        {"label": "#data", "color": "#e3b341", "bg": "#2d2416", "style": "pill"},
        {"label": "#web", "color": "#58a6ff", "bg": "#1c2b41", "style": "pill"},
        {"label": "#mobile", "color": "#a371f7", "bg": "#271c3d", "style": "pill"},
        {"label": "#security", "color": "#f85149", "bg": "#2d1b1b", "style": "pill"},
    ],
    "Language": [
        {"label": "Python", "color": "#fff", "bg": "#3776AB"},
        {"label": "JavaScript", "color": "#000", "bg": "#f1e05a"},
        {"label": "TypeScript", "color": "#fff", "bg": "#3178c6"},
        {"label": "Rust", "color": "#000", "bg": "#dea584"},
        {"label": "Go", "color": "#fff", "bg": "#00add8"},
        {"label": "Ruby", "color": "#fff", "bg": "#cc342d"},
        {"label": "C", "color": "#fff", "bg": "#555555"},
        {"label": "C++", "color": "#fff", "bg": "#f34b7d"},
        {"label": "C#", "color": "#fff", "bg": "#178600"},
        {"label": "Java", "color": "#fff", "bg": "#b07219"},
        {"label": "Kotlin", "color": "#fff", "bg": "#7f52ff"},
        {"label": "Swift", "color": "#fff", "bg": "#f05138"},
        {"label": "PHP", "color": "#fff", "bg": "#777bb3"},
        {"label": "HTML", "color": "#fff", "bg": "#e34f26"},
        {"label": "CSS", "color": "#fff", "bg": "#2965f1"},
        {"label": "SCSS", "color": "#fff", "bg": "#cd6799"},
        {"label": "Sass", "color": "#fff", "bg": "#cc6699"},
        {"label": "Less", "color": "#fff", "bg": "#2b4c7e"},
        {"label": "Lua", "color": "#fff", "bg": "#2c2d72"},
        {"label": "SQL", "color": "#fff", "bg": "#e38c00"},
        {"label": "R", "color": "#fff", "bg": "#276dc3"},
        {"label": "Dart", "color": "#fff", "bg": "#00b4ab"},
        {"label": "Shell", "color": "#fff", "bg": "#4eaa25"},
        {"label": "PowerShell", "color": "#fff", "bg": "#012456"},
        {"label": "Perl", "color": "#fff", "bg": "#39457e"},
        {"label": "Haskell", "color": "#fff", "bg": "#5e5086"},
        {"label": "Scala", "color": "#fff", "bg": "#dc322f"},
        {"label": "Elixir", "color": "#fff", "bg": "#4b275f"},
        {"label": "Clojure", "color": "#fff", "bg": "#5881d8"},
        {"label": "Erlang", "color": "#fff", "bg": "#a90533"},
        {"label": "Julia", "color": "#fff", "bg": "#cb3c33"},
        {"label": "Zig", "color": "#000", "bg": "#f7a41d"},
        {"label": "Nim", "color": "#000", "bg": "#ffe953"},
        {"label": "Solidity", "color": "#fff", "bg": "#363636"},
        {"label": "YAML", "color": "#fff", "bg": "#cb171e"},
        {"label": "JSON", "color": "#fff", "bg": "#292929"},
        {"label": "TOML", "color": "#fff", "bg": "#9c4221"},
        {"label": "Markdown", "color": "#fff", "bg": "#083fa1"},
        {"label": "Dockerfile", "color": "#fff", "bg": "#384d54"},
        {"label": "Makefile", "color": "#fff", "bg": "#427819"},
        {"label": "CMake", "color": "#fff", "bg": "#064f8c"},
        {"label": "TeX", "color": "#fff", "bg": "#3d6117"},
        {"label": "ActionScript", "color": "#fff", "bg": "#882b0f"},
        {"label": "Ada", "color": "#000", "bg": "#02f88c"},
        {"label": "Agda", "color": "#fff", "bg": "#315665"},
        {"label": "AMPL", "color": "#000", "bg": "#e6efbb"},
        {"label": "ANTLR", "color": "#000", "bg": "#9dc3ff"},
        {"label": "Apex", "color": "#fff", "bg": "#1797c0"},
        {"label": "APL", "color": "#fff", "bg": "#5a8164"},
        {"label": "Arduino", "color": "#fff", "bg": "#00979d"},
        {"label": "Asymptote", "color": "#fff", "bg": "#4a0c0c"},
        {"label": "Batch", "color": "#000", "bg": "#c1f12e"},
        {"label": "Bison", "color": "#fff", "bg": "#6a463f"},
        {"label": "COBOL", "color": "#fff", "bg": "#005ca5"},
        {"label": "ColdFusion", "color": "#fff", "bg": "#ed1c24"},
        {"label": "Component Pascal", "color": "#000", "bg": "#b0ce4e"},
        {"label": "D", "color": "#fff", "bg": "#b03931"},
        {"label": "Delphi", "color": "#fff", "bg": "#e62431"},
        {"label": "Elm", "color": "#fff", "bg": "#60b5cc"},
        {"label": "Emacs Lisp", "color": "#fff", "bg": "#7f5ab6"},
        {"label": "F#", "color": "#fff", "bg": "#4d7ab3"},
        {"label": "Forth", "color": "#fff", "bg": "#341708"},
        {"label": "Fortran", "color": "#fff", "bg": "#4d41b1"},
        {"label": "GLSL", "color": "#fff", "bg": "#5686a5"},
        {"label": "Groovy", "color": "#fff", "bg": "#4298b8"},
        {"label": "Haxe", "color": "#fff", "bg": "#df7900"},
        {"label": "HolyC", "color": "#000", "bg": "#f2efe9"},
        {"label": "Idris", "color": "#fff", "bg": "#b30000"},
        {"label": "Io", "color": "#fff", "bg": "#a9188d"},
        {"label": "J", "color": "#000", "bg": "#9eedff"},
        {"label": "Janet", "color": "#fff", "bg": "#7c8f9e"},
        {"label": "LabVIEW", "color": "#000", "bg": "#fedb06"},
        {"label": "Lisp", "color": "#fff", "bg": "#3fb68b"},
        {"label": "LLVM", "color": "#fff", "bg": "#185619"},
        {"label": "Logos", "color": "#fff", "bg": "#90a0b0"},
        {"label": "MATLAB", "color": "#fff", "bg": "#0076a8"},
        {"label": "Meson", "color": "#fff", "bg": "#007500"},
        {"label": "Metal", "color": "#fff", "bg": "#8f14e9"},
        {"label": "MIPS", "color": "#fff", "bg": "#4b6c9b"},
        {"label": "MoonBit", "color": "#000", "bg": "#f6c915"},
        {"label": "Nix", "color": "#fff", "bg": "#7ebae4"},
        {"label": "Objective-C", "color": "#fff", "bg": "#438eff"},
        {"label": "Objective-J", "color": "#fff", "bg": "#ff0c5a"},
        {"label": "Oberon", "color": "#fff", "bg": "#1a7f8a"},
        {"label": "OCaml", "color": "#fff", "bg": "#3be133"},
        {"label": "Odin", "color": "#fff", "bg": "#4f82e2"},
        {"label": "OpenCL", "color": "#fff", "bg": "#ed1c24"},
        {"label": "Pascal", "color": "#000", "bg": "#e3f171"},
        {"label": "Pawn", "color": "#000", "bg": "#dbb40c"},
        {"label": "Pony", "color": "#fff", "bg": "#960000"},
        {"label": "PostScript", "color": "#fff", "bg": "#da291c"},
        {"label": "PowerQuery", "color": "#000", "bg": "#f2c811"},
        {"label": "Processing", "color": "#fff", "bg": "#006699"},
        {"label": "Prolog", "color": "#fff", "bg": "#74283c"},
        {"label": "PureScript", "color": "#fff", "bg": "#1d222d"},
        {"label": "Q", "color": "#fff", "bg": "#004b8b"},
        {"label": "QML", "color": "#fff", "bg": "#44a51c"},
        {"label": "Racket", "color": "#fff", "bg": "#9f1d20"},
        {"label": "Raku", "color": "#fff", "bg": "#0000a0"},
        {"label": "Reason", "color": "#fff", "bg": "#dc3c3c"},
        {"label": "Red", "color": "#fff", "bg": "#f50000"},
        {"label": "Rexx", "color": "#fff", "bg": "#d90e09"},
        {"label": "Ring", "color": "#fff", "bg": "#2d54cb"},
        {"label": "SAS", "color": "#fff", "bg": "#b34936"},
        {"label": "Scheme", "color": "#fff", "bg": "#1e4a6b"},
        {"label": "SPARQL", "color": "#fff", "bg": "#0c4597"},
        {"label": "Tcl", "color": "#000", "bg": "#e4cc98"},
        {"label": "Unison", "color": "#fff", "bg": "#f55c2a"},
        {"label": "V", "color": "#fff", "bg": "#009688"},
        {"label": "Vala", "color": "#fff", "bg": "#a56b46"},
        {"label": "Verilog", "color": "#000", "bg": "#b2b7f8"},
        {"label": "VHDL", "color": "#fff", "bg": "#0b2e5c"},
        {"label": "Vyper", "color": "#fff", "bg": "#2980b9"},
        {"label": "X10", "color": "#fff", "bg": "#4b6bef"},
        {"label": "ZIL", "color": "#000", "bg": "#dc75cd"},
        {"label": "Brainfuck", "color": "#fff", "bg": "#2d2d2d"},
    ],
}

ALL_BADGES: list[dict] = []
for cat, items in BADGE_CATEGORIES.items():
    for b in items:
        entry = {**b, "category": cat}
        if "style" not in entry:
            if entry["label"] in _PILL_BADGES:
                entry["style"] = "pill"
            elif entry["label"] in _OUTLINE_BADGES:
                entry["style"] = "outline"
            elif entry["label"] in _GLOW_BADGES:
                entry["style"] = "glow"
            elif entry["label"] in _GRADIENT_BADGES:
                entry["style"] = "gradient"
                c1, c2 = _GRADIENT_BADGES[entry["label"]]
                entry["gradient"] = (c1, c2)
            else:
                entry["style"] = "flat"
        ALL_BADGES.append(entry)


def badge_style(b: dict) -> str:
    return b.get("style", "flat")


def badge_stylesheet(b: dict, font_size: str = "9px", extra: str = "") -> str:
    style = badge_style(b)
    color = b["color"]
    bg = b["bg"]
    if style == "flat":
        return (
            f"background: {bg}; color: {color}; "
            f"font-size: {font_size}; font-weight: 600; padding: 1px 5px; "
            f"border-radius: 3px;{extra}"
        )
    if style == "pill":
        return (
            f"background: {bg}; color: {color}; "
            f"font-size: {font_size}; font-weight: 600; padding: 1px 8px; "
            f"border-radius: 999px;{extra}"
        )
    if style == "outline":
        return (
            f"background: transparent; color: {color}; "
            f"font-size: {font_size}; font-weight: 600; padding: 1px 7px; "
            f"border-radius: 3px; border: 1.5px solid {color};{extra}"
        )
    if style == "glow":
        return (
            f"background: {bg}; color: {color}; "
            f"font-size: {font_size}; font-weight: 600; padding: 1px 7px; "
            f"border-radius: 4px; box-shadow: 0 0 8px {color}66, 0 0 16px {color}33;{extra}"
        )
    if style == "gradient":
        c1, c2 = b.get("gradient", (bg, color))
        return (
            f"background: linear-gradient(90deg, {c1}, {c2}); color: {color}; "
            f"font-size: {font_size}; font-weight: 700; padding: 1px 8px; "
            f"border-radius: 4px;{extra}"
        )
    if style == "glass":
        return (
            f"background: {bg}33; color: {color}; "
            f"font-size: {font_size}; font-weight: 600; padding: 1px 8px; "
            f"border-radius: 999px; border: 1px solid {color}33;{extra}"
        )
    return (
        f"background: {bg}; color: {color}; "
        f"font-size: {font_size}; font-weight: 600; padding: 1px 5px; "
        f"border-radius: 3px;{extra}"
    )


_EXT_LANG_MAP: dict[str, tuple[str, str]] = {
    ".py": ("Python", "#3776AB"),
    ".pyw": ("Python", "#3776AB"),
    ".js": ("JavaScript", "#f1e05a"),
    ".mjs": ("JavaScript", "#f1e05a"),
    ".cjs": ("JavaScript", "#f1e05a"),
    ".jsx": ("JavaScript", "#f1e05a"),
    ".ts": ("TypeScript", "#3178c6"),
    ".tsx": ("TypeScript", "#3178c6"),
    ".rs": ("Rust", "#dea584"),
    ".go": ("Go", "#00add8"),
    ".rb": ("Ruby", "#cc342d"),
    ".rbw": ("Ruby", "#cc342d"),
    ".java": ("Java", "#b07219"),
    ".class": ("Java", "#b07219"),
    ".jar": ("Java", "#b07219"),
    ".kt": ("Kotlin", "#7f52ff"),
    ".kts": ("Kotlin", "#7f52ff"),
    ".swift": ("Swift", "#f05138"),
    ".c": ("C", "#555555"),
    ".h": ("C", "#555555"),
    ".cpp": ("C++", "#f34b7d"),
    ".hpp": ("C++", "#f34b7d"),
    ".cc": ("C++", "#f34b7d"),
    ".cxx": ("C++", "#f34b7d"),
    ".cs": ("C#", "#178600"),
    ".php": ("PHP", "#777bb3"),
    ".phtml": ("PHP", "#777bb3"),
    ".lua": ("Lua", "#2c2d72"),
    ".html": ("HTML", "#e34f26"),
    ".htm": ("HTML", "#e34f26"),
    ".xhtml": ("HTML", "#e34f26"),
    ".css": ("CSS", "#2965f1"),
    ".scss": ("SCSS", "#cd6799"),
    ".sass": ("Sass", "#cc6699"),
    ".less": ("Less", "#2b4c7e"),
    ".sql": ("SQL", "#e38c00"),
    ".r": ("R", "#276dc3"),
    ".R": ("R", "#276dc3"),
    ".dart": ("Dart", "#00b4ab"),
    ".sh": ("Shell", "#4eaa25"),
    ".bash": ("Shell", "#4eaa25"),
    ".zsh": ("Shell", "#4eaa25"),
    ".ps1": ("PowerShell", "#012456"),
    ".psm1": ("PowerShell", "#012456"),
    ".pl": ("Perl", "#39457e"),
    ".pm": ("Perl", "#39457e"),
    ".hs": ("Haskell", "#5e5086"),
    ".scala": ("Scala", "#dc322f"),
    ".ex": ("Elixir", "#4b275f"),
    ".exs": ("Elixir", "#4b275f"),
    ".clj": ("Clojure", "#5881d8"),
    ".cljs": ("Clojure", "#5881d8"),
    ".erl": ("Erlang", "#a90533"),
    ".hrl": ("Erlang", "#a90533"),
    ".jl": ("Julia", "#cb3c33"),
    ".zig": ("Zig", "#f7a41d"),
    ".nim": ("Nim", "#ffe953"),
    ".sol": ("Solidity", "#363636"),
    ".yaml": ("YAML", "#cb171e"),
    ".yml": ("YAML", "#cb171e"),
    ".json": ("JSON", "#292929"),
    ".toml": ("TOML", "#9c4221"),
    ".md": ("Markdown", "#083fa1"),
    ".mdx": ("Markdown", "#083fa1"),
    ".txt": ("Text", "#808080"),
    ".dockerfile": ("Dockerfile", "#384d54"),
    "Dockerfile": ("Dockerfile", "#384d54"),
    ".makefile": ("Makefile", "#427819"),
    "Makefile": ("Makefile", "#427819"),
    "CMakeLists.txt": ("CMake", "#064f8c"),
    ".tex": ("TeX", "#3d6117"),
    ".sty": ("TeX", "#3d6117"),
    ".cls": ("TeX", "#3d6117"),
    ".vue": ("Vue", "#41b883"),
    ".svelte": ("Svelte", "#ff3e00"),
    ".astro": ("Astro", "#ff5d01"),
    ".pas": ("Pascal", "#e3f171"),
    ".pp": ("Pascal", "#e3f171"),
    ".ml": ("OCaml", "#3be133"),
    ".mli": ("OCaml", "#3be133"),
}


def detect_file_badges(filepath: str) -> list[dict]:
    name = os.path.basename(filepath)
    if name in _EXT_LANG_MAP:
        info = _EXT_LANG_MAP[name]
        return [{"label": info[0], "color": "#fff", "bg": info[1], "category": "Language"}]
    ext = os.path.splitext(filepath)[1].lower()
    info = _EXT_LANG_MAP.get(ext)
    if info:
        return [{"label": info[0], "color": "#fff", "bg": info[1], "category": "Language"}]
    return []


def get_assigned_badges(filepath: str) -> list[dict]:
    from zametka_dbs.core.config import get_config
    config = get_config()
    assigned = config.get(f"badges.{filepath}", [])
    if isinstance(assigned, str):
        import json
        try:
            assigned = json.loads(assigned)
        except (json.JSONDecodeError, TypeError):
            assigned = []
    if not isinstance(assigned, list):
        assigned = []
    result = []
    for label in assigned:
        for b in ALL_BADGES:
            if b["label"] == label:
                result.append(dict(b))
                break
    return result


def set_assigned_badges(filepath: str, badges: list[dict]):
    from zametka_dbs.core.config import get_config
    config = get_config()
    labels = [b["label"] for b in badges]
    config.set(f"badges.{filepath}", labels)


def add_assigned_badge(filepath: str, badge: dict):
    current = get_assigned_badges(filepath)
    if not any(b["label"] == badge["label"] for b in current):
        current.append(badge)
        set_assigned_badges(filepath, current)


def remove_assigned_badge(filepath: str, label: str):
    current = get_assigned_badges(filepath)
    current = [b for b in current if b["label"] != label]
    set_assigned_badges(filepath, current)


def _ensure_notes_list(notes) -> list[str]:
    if isinstance(notes, str):
        import json
        try:
            return json.loads(notes)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(notes, list):
        return notes
    return []


def get_notes_list() -> list[str]:
    from zametka_dbs.core.config import get_config
    config = get_config()
    notes = _ensure_notes_list(config.get("notes.items", []))
    return [n for n in notes if os.path.exists(n)]


def add_note(filepath: str):
    from zametka_dbs.core.config import get_config
    config = get_config()
    notes = _ensure_notes_list(config.get("notes.items", []))
    if filepath not in notes:
        notes.append(filepath)
        config.set("notes.items", notes)


def remove_note(filepath: str):
    from zametka_dbs.core.config import get_config
    config = get_config()
    notes = _ensure_notes_list(config.get("notes.items", []))
    if filepath in notes:
        notes.remove(filepath)
        config.set("notes.items", notes)
