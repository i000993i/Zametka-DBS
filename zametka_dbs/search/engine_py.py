import os
import logging

logger = logging.getLogger(__name__)


class SearchResult:
    __slots__ = ("path", "filename", "title", "score", "snippet", "matches")

    def __init__(self, path="", filename="", title="",
                 score=0.0, snippet="", matches=0):
        self.path = path
        self.filename = filename
        self.title = title
        self.score = score
        self.snippet = snippet
        self.matches = matches

    def __repr__(self):
        return f"SearchResult({self.filename}, score={self.score:.2f})"


class SearchEngine:
    def __init__(self):
        self._titles = {}
        self._indexed = False
        self._file_contents = {}

    def index_vault(self, vault_path):
        if not vault_path or not os.path.isdir(vault_path):
            logger.warning(f"Invalid vault path: {vault_path}")
            return
        self._titles.clear()
        self._file_contents.clear()
        count = 0
        for root, dirs, files in os.walk(vault_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                fp = os.path.join(root, f)
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                    self._file_contents[fp] = content
                    if content.startswith("#"):
                        self._titles[fp] = content.split("\n")[0].lstrip("# \t").strip()
                    else:
                        self._titles[fp] = os.path.basename(fp)
                    count += 1
                except Exception:
                    self._titles[fp] = os.path.basename(fp)
        self._indexed = True
        logger.info(f"Indexed {count} files via Python engine")

    def index_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            self._file_contents[filepath] = content
            if content and content.startswith("#"):
                self._titles[filepath] = content.split("\n")[0].lstrip("# \t").strip()
            else:
                self._titles[filepath] = os.path.basename(filepath)
        except Exception as e:
            logger.warning(f"Failed to index {filepath}: {e}")

    def remove_file(self, filepath):
        self._titles.pop(filepath, None)
        self._file_contents.pop(filepath, None)

    def search(self, query, max_results=20):
        if not query or not self._indexed:
            return []
        query_lower = query.lower()
        scored = []
        for path, content in self._file_contents.items():
            content_lower = content.lower()
            matches = content_lower.count(query_lower)
            if matches > 0:
                score = matches / max(len(content), 1) * 100
                scored.append((path, score, matches))
        scored.sort(key=lambda x: -x[1])
        results = []
        for path, score, match_count in scored[:max_results]:
            filename = os.path.basename(path)
            title = self._titles.get(path, filename)
            snippet = self._build_snippet(path, query)
            results.append(SearchResult(
                path=path, filename=filename, title=title,
                score=score, snippet=snippet, matches=match_count,
            ))
        return results

    def _build_snippet(self, path, query, context=60):
        content = self._file_contents.get(path)
        if content is None:
            return ""
        idx = content.lower().find(query.lower())
        if idx == -1:
            return content[:150] + "..." if len(content) > 150 else content
        start = max(0, idx - context)
        end = min(len(content), idx + len(query) + context)
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        return snippet

    @property
    def file_count(self):
        return len(self._titles)

    @property
    def is_indexed(self):
        return self._indexed
