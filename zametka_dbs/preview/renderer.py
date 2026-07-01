import logging

logger = logging.getLogger(__name__)

try:
    from zametka_core import render_markdown as _rust_render
    _HAS_RUST = True
except ImportError:
    _HAS_RUST = False

if _HAS_RUST:
    from zametka_dbs.preview.styles import PREVIEW_CSS, empty_preview, process_tags, process_callouts

    def render_markdown(text: str) -> str:
        if not text:
            return empty_preview()
        html = _rust_render(text)
        html = process_tags(html)
        html = process_callouts(html)
        return PREVIEW_CSS + html
else:
    logger.info("Rust core not available, using Python markdown renderer")
    from zametka_dbs.preview.renderer_py import render_markdown
