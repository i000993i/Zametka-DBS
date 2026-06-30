import re
import os
import glob
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

try:
    from zametka_core import extract_wikilinks as _rust_extract

    def parse_wikilinks(text):
        targets = _rust_extract(text)
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

except ImportError:
    WIKILINK_SPLIT_RE = re.compile(r'\[\[([^\]]+?)(?:\|([^\]]+))?\]\]')

    def parse_wikilinks(text):
        results = []
        for match in WIKILINK_SPLIT_RE.finditer(text):
            target = match.group(1).strip()
            alias = match.group(2).strip() if match.group(2) else None
            results.append({
                "raw": match.group(0),
                "target": target,
                "alias": alias,
                "start": match.start(),
                "end": match.end(),
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
        pattern = os.path.join(self._vault_path, "**", "*.md")
        for filepath in glob.glob(pattern, recursive=True):
            name_without_ext = os.path.splitext(os.path.basename(filepath))[0]
            self._file_index[name_without_ext] = filepath
            rel = os.path.relpath(filepath, self._vault_path)
            rel_no_ext = os.path.splitext(rel)[0].replace("\\", "/")
            self._file_index[rel_no_ext] = filepath

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

    def index_file(self, filepath: str):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Failed to index {filepath}: {e}")
            return
        links = parse_wikilinks(content)
        targets = [link["target"] for link in links]
        self._forward[filepath].clear()
        for target in targets:
            resolved = self._resolver.resolve(target) if self._resolver else None
            if resolved:
                self._forward[filepath].append(resolved)

    def rebuild_all(self, filepaths: list[str] | None = None):
        self._forward.clear()
        self._back.clear()
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
