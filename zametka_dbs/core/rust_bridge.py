import logging

logger = logging.getLogger(__name__)

try:
    from zametka_core import (
        Config as RustConfig,
        SearchIndex as RustSearchIndex,
        render_markdown as rust_render_markdown,
        resolve_wikilinks as rust_resolve_wikilinks,
        extract_wikilinks as rust_extract_wikilinks,
        find_markdown_files as rust_find_markdown_files,
        detect_language as rust_detect_language,
        scan_folder_languages as rust_scan_folder_languages,
        compute_line_numbers as rust_compute_line_numbers,
    )
    HAS_RUST = True
except ImportError as e:
    logger.debug("zametka_core not available: %s", e)
    HAS_RUST = False
    RustConfig = None
    RustSearchIndex = None
    rust_render_markdown = None
    rust_resolve_wikilinks = None
    rust_extract_wikilinks = None
    rust_find_markdown_files = None
    rust_detect_language = None
    rust_scan_folder_languages = None
    rust_compute_line_numbers = None
