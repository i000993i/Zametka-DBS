from __future__ import annotations

import os

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QProgressBar, QLabel

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from zametka_dbs.core.config import get_config
from zametka_dbs.ui.vault_worker import VaultWorker


class _VaultFileHandler(FileSystemEventHandler):
    def __init__(self, status_info: QLabel):
        self.status_info = status_info

    def on_modified(self, event):
        if event.is_directory:
            return
        self.status_info.setText(f"File changed: {os.path.basename(event.src_path)}")

    def on_created(self, event):
        if event.is_directory:
            return
        self.status_info.setText(f"File created: {os.path.basename(event.src_path)}")


class VaultManager(QObject):
    vault_opened = pyqtSignal(str)
    vault_closed = pyqtSignal()

    def __init__(
        self,
        file_tree,
        progress_bar: QProgressBar,
        status_info: QLabel,
        preview,
        resolver,
        search_engine,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._file_tree = file_tree
        self._progress_bar = progress_bar
        self._status_info = status_info
        self._preview = preview
        self._resolver = resolver
        self._search_engine = search_engine

        self._watcher = None
        self._vault_thread: QThread | None = None
        self._vault_worker: VaultWorker | None = None

    def init_on_startup(self) -> None:
        config = get_config()
        vault_path = config.get("vault_path", "")
        if vault_path and os.path.isdir(vault_path):
            self._init_vault(vault_path)
            self._status_info.setText("Vault opened")
        else:
            self._status_info.setText("No vault — open a folder to start")

    def open_dialog(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self.parent(), "Open Vault Folder", "",
            QFileDialog.Option.ShowDirsOnly
        )
        if dir_path:
            config = get_config()
            config.set("vault_path", dir_path)
            self._init_vault(dir_path)
            self._status_info.setText(f"Vault: {dir_path}")

    def close_vault(self) -> None:
        self._cleanup_worker()
        self.vault_closed.emit()
        if hasattr(self._file_tree, "clear_vault"):
            self._file_tree.clear_vault()
        config = get_config()
        config.set("vault_path", "")
        self._status_info.setText("Vault closed — open a folder to start")

    def stop_watcher(self) -> None:
        if self._watcher:
            self._watcher.stop()
            self._watcher.join(timeout=2)
            self._watcher = None

    def init_from_pin(self, path: str) -> None:
        config = get_config()
        config.set("vault_path", path)
        self._init_vault(path)

    def _init_vault(self, vault_path: str) -> None:
        self._file_tree.set_vault_path(vault_path)

        self._progress_bar.show()
        self._progress_bar.setRange(0, 0)
        self._status_info.setText("Initializing vault...")

        self._cleanup_worker()

        thread = QThread()
        worker = VaultWorker(
            vault_path, self._resolver, self._search_engine
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(
            lambda: self._on_finished(vault_path)
        )
        thread.start()
        self._vault_thread = thread
        self._vault_worker = worker

    def _on_progress(self, current: int, total: int, message: str) -> None:
        if total > 0:
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(current)
        else:
            self._progress_bar.setRange(0, 0)
        self._status_info.setText(message)

    def _on_finished(self, vault_path: str) -> None:
        self._progress_bar.hide()
        all_files = list(self._resolver.all_notes.values())
        self._preview.set_note_map(self._resolver.all_notes)
        self._start_watcher(vault_path)
        self._status_info.setText(f"Vault: {len(all_files)} notes")
        self.vault_opened.emit(vault_path)

    def _start_watcher(self, vault_path: str) -> None:
        self.stop_watcher()
        self._watcher = Observer()
        self._watcher.schedule(
            _VaultFileHandler(self._status_info), vault_path, recursive=True
        )
        self._watcher.start()

    def _cleanup_worker(self) -> None:
        if self._vault_worker is not None:
            self._vault_worker.cancel()
            self._vault_worker = None
        if self._vault_thread is not None:
            old = self._vault_thread
            self._vault_thread = None
            if old.isRunning():
                old.quit()
                old.wait(3000)
            old.deleteLater()
