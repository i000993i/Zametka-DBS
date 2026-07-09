import os
import re

from zametka_dbs.core.rust_bridge import HAS_RUST
from zametka_dbs.core.rust_bridge import rust_extract_wikilinks as _rust_extract
from zametka_dbs.core.rust_bridge import rust_find_markdown_files as _rust_find_md


_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def _py_extract_wikilinks(text):
    return _WIKILINK_RE.findall(text)


def _py_find_markdown_files(vault_path):
    index = {}
    for root, _dirs, files in os.walk(vault_path):
        for fname in files:
            if fname.endswith(".md"):
                name = os.path.splitext(fname)[0]
                path = os.path.join(root, fname)
                index[name] = path
    return index


def parse_wikilinks(text):
    if HAS_RUST:
        targets = _rust_extract(text)
    else:
        targets = _py_extract_wikilinks(text)
    results = []
    for raw in targets:
        parts = raw.split("|")
        target = parts[0].strip()
        alias = parts[1].strip() if len(parts) > 1 else None
        results.append({
            "raw": f"[[{raw}]]",
            "target": target,
            "alias": alias,
        })
    return results


class LinkResolver:
    def __init__(self, vault_path: str = ""):
        self._vault_path = vault_path
        self._file_index: dict[str, str] = {}

    def set_vault_path(self, vault_path: str):
        self._vault_path = vault_path
        self._rebuild_index()

    def _rebuild_index(self):
        self._file_index.clear()
        if not self._vault_path or not os.path.isdir(self._vault_path):
            return
        if HAS_RUST:
            self._file_index = _rust_find_md(self._vault_path)
        else:
            self._file_index = _py_find_markdown_files(self._vault_path)

    def resolve(self, target: str) -> str | None:
        if not self._vault_path:
            return None
        target = target.strip().replace("\\", "/")
        if target in self._file_index:
            return self._file_index[target]
        if target.endswith(".md"):
            key = target[:-3]
            if key in self._file_index:
                return self._file_index[key]
        target_lower = target.lower()
        for name, path in self._file_index.items():
            if name.lower() == target_lower:
                return path
        return None

    @property
    def all_notes(self) -> dict[str, str]:
        return dict(self._file_index)
