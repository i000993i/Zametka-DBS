import os
import tempfile
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zametka_dbs.utils.file_size import is_file_too_large, format_size, MAX_FILE_SIZE


def test_small_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"hello")
        path = f.name
    assert not is_file_too_large(path)
    os.unlink(path)


def test_large_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"x" * (MAX_FILE_SIZE + 1))
        path = f.name
    assert is_file_too_large(path)
    os.unlink(path)


def test_nonexistent_file():
    assert not is_file_too_large("/nonexistent/path")


def test_format_size():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"x" * 2048)
        path = f.name
    result = format_size(path)
    assert "KB" in result
    os.unlink(path)


if __name__ == "__main__":
    test_small_file()
    test_large_file()
    test_nonexistent_file()
    test_format_size()
    print("All file size tests passed")
