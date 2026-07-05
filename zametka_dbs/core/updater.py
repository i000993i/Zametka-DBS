import json
import logging
import os
import ssl
import sys
import tempfile
import threading
import zipfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from zametka_dbs.core.version import __version__, __api_url__, __repo__

logger = logging.getLogger(__name__)


def _latest_release():
    req = Request(__api_url__, headers={"User-Agent": "Zametka-Updater/1.0", "Accept": "application/json"})
    ctx = ssl.create_default_context()
    resp = urlopen(req, timeout=10, context=ctx)
    return json.loads(resp.read().decode("utf-8"))


def _parse_tag(tag):
    return tag.lstrip("v")


class UpdateCheckResult:
    def __init__(self):
        self.available = False
        self.latest_version = ""
        self.download_url = ""
        self.release_notes = ""
        self.error = ""


def check_for_updates():
    result = UpdateCheckResult()
    try:
        data = _latest_release()
        tag = data.get("tag_name", "")
        result.latest_version = _parse_tag(tag)
        result.release_notes = data.get("body", "")
        current = [int(x) for x in __version__.split(".")]
        latest = [int(x) for x in result.latest_version.split(".")]
        if latest > current:
            result.available = True
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".zip") or name.endswith(".exe"):
                    result.download_url = asset["browser_download_url"]
                    break
            if not result.download_url:
                result.download_url = data.get("zipball_url", "")
    except URLError as e:
        result.error = f"Network error: {e.reason}"
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        result.error = f"Invalid response: {e}"
    except Exception as e:
        result.error = str(e)
    return result


class UpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Проверка обновлений")
        self.setFixedSize(480, 300)
        self._result = None
        self._build_ui()
        QTimer.singleShot(0, self._do_check)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self._status = QLabel("Проверка обновлений...")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        self._bar = QProgressBar()
        self._bar.setRange(0, 0)
        layout.addWidget(self._bar)
        self._notes = QLabel()
        self._notes.setWordWrap(True)
        self._notes.setVisible(False)
        layout.addWidget(self._notes)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._download_btn = QPushButton("Скачать обновление")
        self._download_btn.setVisible(False)
        self._download_btn.clicked.connect(self._do_download)
        btn_row.addWidget(self._download_btn)
        self._close_btn = QPushButton("Закрыть")
        self._close_btn.clicked.connect(self.close)
        btn_row.addWidget(self._close_btn)
        layout.addLayout(btn_row)

    def _do_check(self):
        import threading
        threading.Thread(target=self._check_thread, daemon=True).start()

    def _check_thread(self):
        result = check_for_updates()
        self._result = result
        QTimer.singleShot(0, self._show_result)

    def _show_result(self):
        self._bar.hide()
        r = self._result
        if r.error:
            self._status.setText(f"Ошибка: {r.error}")
            return
        if r.available:
            self._status.setText(
                f"Доступна новая версия: {r.latest_version}\n"
                f"Текущая версия: {__version__}"
            )
            if r.release_notes:
                self._notes.setText(f"Что нового:\n{r.release_notes[:500]}")
                self._notes.setVisible(True)
            self._download_btn.setVisible(True)
        else:
            self._status.setText(f"У вас актуальная версия ({__version__}).")

    def _do_download(self):
        self._download_btn.setEnabled(False)
        self._status.setText("Загрузка...")
        self._bar.setRange(0, 100)
        threading.Thread(target=self._download_thread, daemon=True).start()

    def _download_thread(self):
        url = self._result.download_url
        if not url:
            QTimer.singleShot(0, lambda: self._status.setText("Нет ссылки для скачивания."))
            return
        try:
            tmp = tempfile.gettempdir()
            dest = os.path.join(tmp, "Zametka-Update.zip")
            req = Request(url, headers={"User-Agent": "Zametka-Updater/1.0"})
            ctx = ssl.create_default_context()
            resp = urlopen(req, timeout=60, context=ctx)
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 65536
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = int(downloaded * 100 / total)
                        QTimer.singleShot(0, lambda v=pct: self._bar.setValue(v))
            QTimer.singleShot(0, self._finish_download)
        except Exception as e:
            QTimer.singleShot(0, lambda: self._status.setText(f"Ошибка загрузки: {e}"))

    def _finish_download(self):
        from PyQt6.QtWidgets import QMessageBox
        self._status.setText("Обновление загружено. Запустите установщик для применения.")
        self._download_btn.setVisible(False)
        reply = QMessageBox.question(
            self, "Обновление загружено",
            "Открыть папку с обновлением?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            import subprocess
            subprocess.Popen(["explorer", tempfile.gettempdir()])
