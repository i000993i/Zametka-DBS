import os

MAX_FILE_SIZE = 10 * 1024 * 1024


def is_file_too_large(path: str, max_bytes: int = MAX_FILE_SIZE) -> bool:
    try:
        return os.path.getsize(path) > max_bytes
    except OSError:
        return False


def format_size(path: str) -> str:
    size = os.path.getsize(path)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
