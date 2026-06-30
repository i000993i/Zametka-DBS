# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

BLOCK_CIPHER = None

ROOT = Path(os.getcwd())

# Locate the Rust core .pyd file
_venv_site = Path(sys.prefix) / "Lib" / "site-packages"
_rust_pkg = _venv_site / "zametka_core"
_rust_binaries = []
if _rust_pkg.exists():
    for f in _rust_pkg.iterdir():
        if f.suffix in (".pyd", ".dll"):
            _rust_binaries.append((str(f), "zametka_core"))

a = Analysis(
    ["app.py"],
    pathex=[str(ROOT)],
    binaries=_rust_binaries,
    datas=[
        (str(ROOT / "assets" / "icons"), "assets/icons"),
        (str(ROOT / "assets" / "app_icon.ico"), "assets"),
    ],
    hiddenimports=[
        "PyQt6.QtSvg",
        "watchdog.observers",
        "watchdog.observers.read_directory_changes",
        "zametka_core",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Zametka",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "app_icon.ico"),
)
