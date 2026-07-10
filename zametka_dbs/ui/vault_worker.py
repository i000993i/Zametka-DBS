from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class VaultWorker(QObject):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal()

    def __init__(self, vault_path: str, resolver=None, search_engine=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._vault_path: str = vault_path
        self._resolver = resolver
        self._search_engine = search_engine
        self._cancelled: bool = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        import os

        md_files: list[str] = []
        for root, dirs, files in os.walk(self._vault_path):
            dirs[:] = [d for d in dirs
                       if not d.startswith(".") and d not in ("node_modules", "__pycache__")]
            for f in files:
                if self._cancelled:
                    self.finished.emit()
                    return
                if f.endswith(".md"):
                    fp: str = os.path.join(root, f)
                    md_files.append(fp)
        self.finished.emit()
