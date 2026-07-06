import os
import tempfile
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zametka_dbs.search.engine import SearchEngine, _PySearchIndex


def test_py_search_index():
    idx = _PySearchIndex()
    idx._index_file("/test/file1.md", "# Hello World\n\nThis is a test file.")
    idx._index_file("/test/file2.md", "# Another File\n\nWith some content here.")
    results = idx.search("test")
    assert len(results) > 0
    assert "/test/file1.md" in [r[0] for r in results]


def test_search_results():
    idx = _PySearchIndex()
    idx._index_file("/test/a.md", "python code is great for testing")
    idx._index_file("/test/b.md", "java code is also great")
    results = idx.search("python")
    assert len(results) >= 1
    assert results[0][0] == "/test/a.md"


def test_search_no_match():
    idx = _PySearchIndex()
    idx._index_file("/test/a.md", "hello world")
    results = idx.search("nonexistent")
    assert len(results) == 0


def test_search_empty():
    idx = _PySearchIndex()
    results = idx.search("test")
    assert len(results) == 0


def test_search_engine_vault():
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("note1.md", "note2.md"):
            with open(os.path.join(tmp, name), "w") as f:
                f.write(f"# {name}\n\ncontent here")
        eng = SearchEngine()
        eng.index_vault(tmp)
        assert eng.file_count == 2
        results = eng.search("content")
        assert len(results) == 2


if __name__ == "__main__":
    test_py_search_index()
    test_search_results()
    test_search_no_match()
    test_search_empty()
    test_search_engine_vault()
    print("All search tests passed")
