import logging
import re

logger = logging.getLogger(__name__)

from zametka_dbs.core.rust_bridge import HAS_RUST
from zametka_dbs.core.rust_bridge import rust_render_markdown as _rust_render
from zametka_dbs.core.rust_bridge import rust_resolve_wikilinks as _rust_resolve_wikilinks

from zametka_dbs.preview.styles import _preview_css, empty_preview, process_tags, process_callouts


_WIKILINK_HTML_RE = re.compile(
    r'<a\s+href="([^"]+)"[^>]*>\[\[([^\]]+)\]\]</a>'
)


def _py_resolve_wikilinks(html: str, note_map: dict) -> str:
    def _replace(m):
        href = m.group(1)
        display = m.group(2)
        target = href.strip("/").replace("\\", "/")
        if target in note_map:
            resolved = note_map[target]
            return f'<a href="{resolved}">{display}</a>'
        return m.group(0)
    return _WIKILINK_HTML_RE.sub(_replace, html)


def render_markdown(text: str, note_map: dict | None = None, dark: bool = True) -> str:
    css = _preview_css(dark)
    if not text:
        return empty_preview(dark)
    if HAS_RUST:
        html = _rust_render(text)
    else:
        from markdown_it import MarkdownIt
        try:
            import linkify_it  # noqa: F401
            md = MarkdownIt("default", {"breaks": True, "linkify": True})
        except ImportError:
            md = MarkdownIt("default", {"breaks": True, "linkify": False})
        html = md.render(text)
    html = process_tags(html)
    html = process_callouts(html)
    if note_map:
        if HAS_RUST:
            html = _rust_resolve_wikilinks(html, note_map)
        else:
            html = _py_resolve_wikilinks(html, note_map)
    return css + html
