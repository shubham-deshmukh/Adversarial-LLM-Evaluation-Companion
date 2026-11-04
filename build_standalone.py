"""
Production Build Script for Adversarial LLM Evaluation Companion.
Packages the PyQt6 application into a standalone Windows executable using PyInstaller.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"


def clean_previous_builds() -> None:
    """Removes previous build artifacts to ensure a clean compilation."""
    print("[*] Cleaning build artifacts...")
    for directory in (DIST_DIR, BUILD_DIR):
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)
            print(f"    Removed: {directory}")


def build_executable() -> bool:
    """Runs PyInstaller to compile the production binary."""
    print("[*] Compiling standalone Windows executable with PyInstaller...")

    # PyInstaller arguments
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=AdversarialCompanion",
        "--windowed",                 # Suppress black console window in production
        "--clean",                    # Clean cache before build
        "--onedir",                   # Folder-based distribution (fast launch, robust DLL resolution)
        "--noconfirm",                # Overwrite output directory without asking
        "--collect-all=PyQt6",        # Ensure all PyQt6 plugins/platforms are bundled
        "--collect-all=pynput",       # Ensure OS keyboard hooks are packaged
        "main.py",
    ]

    print(f"    Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(BASE_DIR), check=False)

    if result.returncode == 0:
        exe_path = DIST_DIR / "AdversarialCompanion" / "AdversarialCompanion.exe"
        print("\n[+] Build successful!")
        print(f"    Binary location: {exe_path}")
        return True
    else:
        print(f"\n[-] Build failed with exit code: {result.returncode}")
        return False


if __name__ == "__main__":
    clean_previous_builds()
    success = build_executable()
    sys.exit(0 if success else 1)
