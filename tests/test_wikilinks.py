import os
import tempfile
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zametka_dbs.markdown.wikilinks import (
    parse_wikilinks, _py_extract_wikilinks,
    LinkResolver, _py_find_markdown_files,
)


def test_parse_wikilinks():
    text = "Hello [[World]] and [[Note|display]]"
    links = parse_wikilinks(text)
    targets = [l["target"] for l in links]
    assert "World" in targets
    assert "Note" in targets


def test_py_extract_wikilinks():
    result = _py_extract_wikilinks("[[File]] and [[Another File|alias]]")
    assert result == ["File", "Another File"]


def test_no_wikilinks():
    result = _py_extract_wikilinks("plain text without links")
    assert result == []


def test_find_markdown_files():
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("a.md", "b.md", "c.txt"):
            with open(os.path.join(tmp, name), "w") as f:
                f.write("content")
        index = _py_find_markdown_files(tmp)
        assert "a" in index
        assert "b" in index
        assert "c" not in index


def test_link_resolver():
    resolver = LinkResolver()
    with tempfile.TemporaryDirectory() as tmp:
        resolver.set_vault_path(tmp)
        assert resolver._vault_path == tmp


if __name__ == "__main__":
    test_parse_wikilinks()
    test_py_extract_wikilinks()
    test_no_wikilinks()
    test_find_markdown_files()
    test_link_resolver()
    print("All wikilinks tests passed")
