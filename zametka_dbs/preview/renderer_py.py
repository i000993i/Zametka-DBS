import logging

logger = logging.getLogger(__name__)

from zametka_dbs.preview.styles import PREVIEW_CSS, empty_preview, process_tags, process_callouts


def render_markdown(text: str) -> str:
    if not text:
        return empty_preview()
    from markdown_it import MarkdownIt
    md = MarkdownIt("gfm-like", {"breaks": True})
    html = md.render(text)
    html = process_tags(html)
    html = process_callouts(html)
    return PREVIEW_CSS + html
