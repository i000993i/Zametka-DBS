import os
import re
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

from zametka_dbs.core.rust_bridge import HAS_RUST
from zametka_dbs.core.rust_bridge import rust_extract_wikilinks as _rust_extract
from zametka_dbs.core.rust_bridge import rust_find_markdown_files as _rust_find_md
from zametka_dbs.core.rust_bridge import rust_build_backlinks as _rust_build_backlinks


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


def _py_build_backlinks(note_map):
    from zametka_dbs.utils.file_size import is_file_too_large
    back = defaultdict(list)
    for name, path in note_map.items():
        if is_file_too_large(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            continue
        for ref in _WIKILINK_RE.findall(content):
            target = ref.split("|")[0].strip()
            if target in note_map:
                back[note_map[target]].append(path)
    return dict(back)


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

    def resolve_all(self, targets: list[str]) -> dict[str, str | None]:
        return {t: self.resolve(t) for t in targets}

    @property
    def all_notes(self) -> dict[str, str]:
        return dict(self._file_index)


class BacklinkIndex:
    def __init__(self, resolver: LinkResolver | None = None):
        self._resolver = resolver
        self._forward: dict[str, list[str]] = defaultdict(list)
        self._back: dict[str, list[str]] = defaultdict(list)

    def set_resolver(self, resolver: LinkResolver):
        self._resolver = resolver

    def _clean_stale_backlinks(self, filepath: str):
        for target, sources in list(self._back.items()):
            if filepath in sources:
                sources.remove(filepath)
                if not sources:
                    del self._back[target]

    def index_file(self, filepath: str):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Failed to index {filepath}: {e}")
            return
        self._clean_stale_backlinks(filepath)
        links = parse_wikilinks(content)
        targets = [link["target"] for link in links]
        self._forward[filepath].clear()
        for target in targets:
            resolved = self._resolver.resolve(target) if self._resolver else None
            if resolved:
                self._forward[filepath].append(resolved)
                if filepath not in self._back[resolved]:
                    self._back[resolved].append(filepath)

    def rebuild_all(self, filepaths: list[str] | None = None):
        self._forward.clear()
        self._back.clear()
        if self._resolver and self._resolver._file_index:
            note_map = dict(self._resolver._file_index)
            try:
                if HAS_RUST:
                    raw = _rust_build_backlinks(note_map)
                else:
                    raw = _py_build_backlinks(note_map)
                self._back = defaultdict(list, raw)
                for target, sources in self._back.items():
                    for src in set(sources):
                        self._forward[src].append(target)
                return
            except Exception as e:
                logger.warning(f"Build backlinks failed: {e}")
                return
        if filepaths is None and self._resolver:
            filepaths = list(self._resolver.all_notes.values())
        if not filepaths:
            return
        for fp in filepaths:
            self.index_file(fp)
        self._rebuild_backlinks()

    def _rebuild_backlinks(self):
        self._back.clear()
        for source, targets in self._forward.items():
            for target in targets:
                self._back[target].append(source)

    def get_backlinks(self, filepath: str) -> list[str]:
        return self._back.get(filepath, [])

    def get_forward_links(self, filepath: str) -> list[str]:
        return self._forward.get(filepath, [])

    def get_all_links(self) -> dict[str, list[str]]:
        return dict(self._forward)
