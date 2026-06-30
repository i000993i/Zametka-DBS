import os
import logging

logger = logging.getLogger(__name__)

try:
    from zametka_core import SearchIndex as _RustSearchIndex

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
            self._index = _RustSearchIndex()
            self._titles = {}
            self._indexed = False

        def index_vault(self, vault_path):
            if not vault_path or not os.path.isdir(vault_path):
                logger.warning(f"Invalid vault path: {vault_path}")
                return
            self._index.clear()
            self._titles.clear()
            count = self._index.index_vault(vault_path)
            # Extract titles from files
            for root, dirs, files in os.walk(vault_path):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in files:
                    if f.endswith(".md"):
                        fp = os.path.join(root, f)
                        try:
                            with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                                first_line = fh.readline()
                            if first_line.startswith("#"):
                                self._titles[fp] = first_line.lstrip("# \t").strip()
                            else:
                                self._titles[fp] = os.path.basename(fp)
                        except Exception:
                            self._titles[fp] = os.path.basename(fp)
            self._indexed = True
            logger.info(f"Indexed {count} files via Rust core")

        def index_file(self, filepath):
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                self._index.index_file(filepath, content)
                if content and content.startswith("#"):
                    self._titles[filepath] = content.split("\n")[0].lstrip("# \t").strip()
                else:
                    self._titles[filepath] = os.path.basename(filepath)
            except Exception as e:
                logger.warning(f"Failed to index {filepath}: {e}")

        def remove_file(self, filepath):
            self._titles.pop(filepath, None)

        def search(self, query, max_results=20):
            if not query or not self._indexed:
                return []
            raw_results = self._index.search(query, max_results)
            results = []
            for path, score in raw_results:
                filename = os.path.basename(path)
                title = self._titles.get(path, filename)
                snippet = self._build_snippet(path, query)
                match_count = int(score * 3)
                results.append(SearchResult(
                    path=path, filename=filename, title=title,
                    score=score, snippet=snippet, matches=match_count,
                ))
            return results

        def _build_snippet(self, path, query, context=60):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
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

except ImportError:
    logger.info("Rust core not available, using Python search engine")
    from zametka_dbs.search.engine_py import SearchEngine, SearchResult
