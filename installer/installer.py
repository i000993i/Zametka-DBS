#!/usr/bin/env python3
"""
Zametka Installer — скачивает последнюю версию с GitHub и устанавливает.
Сборка: PyInstaller installer.py --onefile --windowed --icon=..\assets\app_icon.ico
"""

import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

from PyQt6.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox,
    QProgressBar, QTextEdit, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

API_URL = "https://api.github.com/repos/i000993i/Zametka-DBS/releases/latest"
REPO_URL = "https://github.com/i000993i/Zametka-DBS"


def _get_latest_release():
    req = Request(API_URL, headers={"User-Agent": "Zametka-Installer/1.0", "Accept": "application/json"})
    ctx = ssl.create_default_context()
    resp = urlopen(req, timeout=15, context=ctx)
    return json.loads(resp.read().decode("utf-8"))


class DownloadThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, dest):
        super().__init__()
        self.url = url
        self.dest = dest

    def run(self):
        try:
            req = Request(self.url, headers={"User-Agent": "Zametka-Installer/1.0"})
            ctx = ssl.create_default_context()
            resp = urlopen(req, timeout=120, context=ctx)
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 65536
            with open(self.dest, "wb") as f:
                while True:
                    data = resp.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    if total:
                        self.progress.emit(int(downloaded * 100 / total))
            self.finished.emit(self.dest)
        except Exception as e:
            self.error.emit(str(e))


class InstallThread(QThread):
    status = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, zip_path, install_dir, create_desktop, create_startmenu):
        super().__init__()
        self.zip_path = zip_path
        self.install_dir = install_dir
        self.create_desktop = create_desktop
        self.create_startmenu = create_startmenu

    def run(self):
        try:
            self.status.emit("Распаковка...")
            target = Path(self.install_dir)
            target.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(self.zip_path, "r") as zf:
                files = zf.namelist()
                for i, name in enumerate(files):
                    zf.extract(name, str(target))
                    self.progress.emit(int((i + 1) * 100 / len(files)))
            exe_src = target / "Zametka" / "Zametka.exe"
            if exe_src.exists():
                shutil.move(str(exe_src), str(target / "Zametka.exe"))
                internal = target / "Zametka" / "_internal"
                if internal.exists():
                    shutil.move(str(internal), str(target / "_internal"))
                (target / "Zametka").rmdir()
            exe_path = target / "Zametka.exe"
            if not exe_path.exists():
                for f in target.rglob("*.exe"):
                    if "Zametka" in f.name:
                        exe_path = f
                        break
            self.status.emit("Создание ярлыков...")
            self._create_shortcuts(exe_path)
            self._register_file_assoc(exe_path)
            self._write_uninstall(exe_path)
            self.status.emit("Установка завершена!")
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

    def _create_shortcuts(self, exe_path):
        import winshell
        icon_path = str(exe_path)
        if self.create_desktop:
            desktop = Path(winshell.desktop())
            link = desktop / "Zametka.lnk"
            self._make_link(str(exe_path), str(link), icon_path)
        if self.create_startmenu:
            start = Path(winshell.programs()) / "Zametka"
            start.mkdir(parents=True, exist_ok=True)
            link = start / "Zametka.lnk"
            self._make_link(str(exe_path), str(link), icon_path)
            unlink = start / "Uninstall.lnk"
            uninst = Path(self.install_dir) / "uninstall.cmd"
            self._make_link(str(uninst), str(unlink), str(uninst))

    def _make_link(self, target, link_path, icon_path):
        import pythoncom
        from win32com.client import Dispatch
        pythoncom.CoInitialize()
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(link_path))
        shortcut.TargetPath = target
        shortcut.IconLocation = icon_path
        shortcut.WorkingDirectory = str(Path(target).parent)
        shortcut.Save()

    def _register_file_assoc(self, exe_path):
        import winreg
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Zametka") as key:
                winreg.SetValue(key, "", winreg.REG_SZ, "Zametka Note")
                with winreg.CreateKey(key, r"shell\open\command") as cmd:
                    winreg.SetValue(cmd, "", winreg.REG_SZ, f'"{exe_path}" "%1"')
            for ext in (".md", ".markdown", ".mdown"):
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}") as key:
                    winreg.SetValue(key, "", winreg.REG_SZ, "Zametka")
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}\\OpenWithProgids") as key:
                    winreg.SetValue(key, "Zametka", winreg.REG_SZ, "")
        except Exception:
            pass

    def _write_uninstall(self, exe_path):
        import winreg
        install_dir = self.install_dir
        uninst_cmd = os.path.join(install_dir, "uninstall.cmd")
        with open(uninst_cmd, "w", encoding="utf-8") as f:
            f.write(f'@echo off\n"{exe_path}" --unregister\n')
            f.write(f'rd /s /q "{install_dir}"\n')
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Zametka"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValue(key, "DisplayName", winreg.REG_SZ, "Zametka")
                winreg.SetValue(key, "UninstallString", winreg.REG_SZ, f'"{uninst_cmd}"')
                winreg.SetValue(key, "DisplayIcon", winreg.REG_SZ, str(exe_path))
                winreg.SetValue(key, "DisplayVersion", winreg.REG_SZ, "0.1.0")
                winreg.SetValue(key, "Publisher", winreg.REG_SZ, "Zametka Team")
        except Exception:
            pass


class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Установка Zametka")
        self.setSubTitle("Заметки с Rust-ядром")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Этот установщик скачает последнюю версию Zametka с GitHub и установит её на ваш компьютер."))
        layout.addWidget(QLabel("Нажмите Далее, чтобы выбрать папку установки."))
        layout.addStretch()


class InstallDirPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Выбор папки установки")
        layout = QVBoxLayout(self)
        self._path = QLineEdit(os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Program Files"), "Zametka"))
        browse = QPushButton("Обзор...")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self._path, 1)
        row.addWidget(browse)
        layout.addLayout(row)
        self._desktop_cb = QCheckBox("Создать ярлык на рабочем столе")
        self._desktop_cb.setChecked(True)
        layout.addWidget(self._desktop_cb)
        self._startmenu_cb = QCheckBox("Добавить в меню Пуск")
        self._startmenu_cb.setChecked(True)
        layout.addWidget(self._startmenu_cb)
        layout.addStretch()
        self.registerField("install_dir*", self._path)
        self.registerField("desktop_shortcut", self._desktop_cb)
        self.registerField("start_menu", self._startmenu_cb)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Выберите папку установки", self._path.text())
        if d:
            self._path.setText(d)


class InstallPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Установка")
        self.setCommitPage(True)
        layout = QVBoxLayout(self)
        self._status = QLabel("Подготовка...")
        layout.addWidget(self._status)
        self._bar = QProgressBar()
        layout.addWidget(self._bar)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(120)
        layout.addWidget(self._log)

    def initializePage(self):
        self._bar.setValue(0)
        self._status.setText("Получение информации о последней версии...")
        self._log.append("Соединение с GitHub...")
        QApplication.processEvents()
        try:
            data = _get_latest_release()
            tag = data.get("tag_name", "latest")
            self._log.append(f"Найдена версия: {tag}")
            url = ""
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".zip"):
                    url = asset["browser_download_url"]
                    break
            if not url:
                url = data.get("zipball_url", "")
            if not url:
                self._status.setText("Не найден архив для скачивания")
                self.wizard().button(QWizard.WizardButton.CommitButton).setEnabled(False)
                return
            tmp = tempfile.gettempdir()
            zip_dest = os.path.join(tmp, "Zametka-Latest.zip")
            self._log.append(f"Скачивание: {url}")
            self._status.setText("Скачивание...")
            self._dl_thread = DownloadThread(url, zip_dest)
            self._dl_thread.progress.connect(self._bar.setValue)
            self._dl_thread.status.connect(self._log.append)
            self._dl_thread.finished.connect(lambda p: self._start_install(zip_dest))
            self._dl_thread.error.connect(lambda e: self._status.setText(f"Ошибка: {e}"))
            self._dl_thread.start()
        except Exception as e:
            self._status.setText(f"Ошибка: {e}")

    def _start_install(self, zip_path):
        self._log.append("Архив загружен, начинаю установку...")
        self._status.setText("Установка...")
        install_dir = self.field("install_dir")
        desktop = self.field("desktop_shortcut")
        startmenu = self.field("start_menu")
        self._install_thread = InstallThread(zip_path, install_dir, desktop, startmenu)
        self._install_thread.status.connect(self._log.append)
        self._install_thread.progress.connect(self._bar.setValue)
        self._install_thread.finished.connect(self._on_done)
        self._install_thread.error.connect(lambda e: self._status.setText(f"Ошибка: {e}"))
        self._install_thread.start()

    def _on_done(self):
        self._status.setText("Установка завершена!")
        self._log.append("Готово!")
        self.wizard().button(QWizard.WizardButton.CommitButton).setEnabled(True)


class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Установка завершена")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Zametka успешно установлена!"))
        self._run_cb = QCheckBox("Запустить Zametka")
        self._run_cb.setChecked(True)
        layout.addWidget(self._run_cb)
        layout.addStretch()
        self.registerField("run_app", self._run_cb)

    def on_finish(self):
        if self.field("run_app"):
            install_dir = self.field("install_dir")
            exe = os.path.join(install_dir, "Zametka.exe")
            if os.path.isfile(exe):
                subprocess.Popen([exe])


class InstallerWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Установка Zametka")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(600, 450)
        ico = os.path.join(os.path.dirname(__file__), "..", "assets", "app_icon.ico")
        if os.path.isfile(ico):
            self.setWindowIcon(QIcon(ico))
        self.addPage(WelcomePage())
        self.addPage(InstallDirPage())
        self.addPage(InstallPage())
        self.addPage(FinishPage())

    def accept(self):
        from PyQt6.QtWidgets import QMessageBox
        install_dir = self.field("install_dir")
        run_app = self.field("run_app")
        if run_app:
            exe = os.path.join(install_dir, "Zametka.exe")
            if os.path.isfile(exe):
                subprocess.Popen([exe])
        QMessageBox.information(self, "Готово", "Zametka установлена!")
        super().accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Zametka Installer")
    wiz = InstallerWizard()
    wiz.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
