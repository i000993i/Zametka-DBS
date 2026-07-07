import os
import re
import math
import logging
from collections import Counter

logger = logging.getLogger(__name__)

from zametka_dbs.core.rust_bridge import HAS_RUST, RustSearchIndex as _RustSearchIndex


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


class _PySearchIndex:
    def __init__(self):
        self._docs = {}
        self._index = {}
        self._indexed_files = []

    def clear(self):
        self._docs.clear()
        self._index.clear()
        self._indexed_files.clear()

    def index_vault(self, vault_path):
        from zametka_dbs.utils.file_size import is_file_too_large
        count = 0
        for root, _dirs, files in os.walk(vault_path):
            for fname in files:
                path = os.path.join(root, fname)
                if is_file_too_large(path):
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    self._index_file(path, content)
                    count += 1
                except Exception:
                    continue
        return count

    def index_file(self, path, content):
        self._index_file(path, content)

    def _index_file(self, path, content):
        self._docs[path] = content
        if path not in self._indexed_files:
            self._indexed_files.append(path)
        tokens = re.findall(r"\w+", content.lower())
        tf = Counter(tokens)
        for token, freq in tf.items():
            if token not in self._index:
                self._index[token] = {}
            self._index[token][path] = freq

    def search(self, query, max_results=20):
        query_tokens = re.findall(r"\w+", query.lower())
        if not query_tokens or not self._docs:
            return []
        n = len(self._docs)
        scores = Counter()
        for token in query_tokens:
            if token not in self._index:
                continue
            df = len(self._index[token])
            idf = math.log((n + 1) / (df + 1)) + 1
            for path, freq in self._index[token].items():
                doc_len = len(re.findall(r"\w+", self._docs.get(path, "")))
                tf = freq / doc_len if doc_len else 0
                scores[path] += tf * idf
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        return ranked[:max_results]

    @property
    def indexed_files(self):
        return list(self._indexed_files)


class SearchEngine:
    def __init__(self):
        if HAS_RUST:
            self._index = _RustSearchIndex()
        else:
            logger.info("Using Python search backend")
            self._index = _PySearchIndex()
        self._titles = {}
        self._indexed = False

    def index_vault(self, vault_path):
        if not vault_path or not os.path.isdir(vault_path):
            logger.warning(f"Invalid vault path: {vault_path}")
            return
        self._index.clear()
        self._titles.clear()
        try:
            if HAS_RUST:
                count = self._index.index_vault(vault_path)
            else:
                count = self._index.index_vault(vault_path)
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            return
        for fp in self._index.indexed_files:
            if fp.endswith(".md"):
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
        logger.info(f"Indexed {count} files")

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
