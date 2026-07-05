#!/usr/bin/env python3
"""
Build script: compile Rust core → build .exe with PyInstaller.

Usage:
    python build.py          # normal build
    python build.py --debug  # debug build (no UPX, console visible)
"""

import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)


def step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def run(cmd, cwd=None):
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or str(ROOT))
    if result.returncode != 0:
        print(f"  FAILED with code {result.returncode}")
        sys.exit(result.returncode)
    return result


def main():
    debug = "--debug" in sys.argv

    step("1. Build Rust core (zametka_core)")
    run(
        f'"{VENV_PYTHON}" -m maturin develop --release --manifest-path zametka-core\\Cargo.toml',
        cwd=str(ROOT),
    )

    step("2. Build .exe with PyInstaller")
    args = ["--clean"]
    if debug:
        args.append("--debug")
        args.append("--console")
    run(
        f'"{VENV_PYTHON}" -m PyInstaller Zametka.spec {" ".join(args)}',
        cwd=str(ROOT),
    )

    exe_path = ROOT / "dist" / "Zametka" / "Zametka.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n  Done! {exe_path} ({size_mb:.1f} MB)")
    else:
        print(f"\n  Done! Check dist/Zametka/")

    build_installer = "--installer" in sys.argv
    if build_installer:
        step("3. Build installer .exe")
        run(
            f'"{VENV_PYTHON}" -m PyInstaller installer/installer.py --onefile --windowed '
            f'--icon=assets/app_icon.ico --name Zametka-Installer --distpath dist',
            cwd=str(ROOT),
        )
        inst_path = ROOT / "dist" / "Zametka-Installer.exe"
        if inst_path.exists():
            size_mb = inst_path.stat().st_size / (1024 * 1024)
            print(f"\n  Done! {inst_path} ({size_mb:.1f} MB)")

if __name__ == "__main__":
    main()
