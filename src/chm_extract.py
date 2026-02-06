from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path


def _install_extract_tool() -> None:
    system = platform.system().lower()
    if system == "darwin":
        if not shutil.which("brew"):
            raise SystemExit("brew not found. Please install Homebrew first.")
        cmd = ["brew", "install", "chmlib"]
    elif system == "linux":
        if shutil.which("apt-get"):
            cmd = ["sudo", "apt-get", "-y", "install", "chmlib-tools"]
        elif shutil.which("dnf"):
            cmd = ["sudo", "dnf", "-y", "install", "chmlib"]
        elif shutil.which("yum"):
            cmd = ["sudo", "yum", "-y", "install", "chmlib"]
        elif shutil.which("pacman"):
            cmd = ["sudo", "pacman", "-S", "--noconfirm", "chmlib"]
        elif shutil.which("zypper"):
            cmd = ["sudo", "zypper", "-n", "install", "chmlib"]
        else:
            raise SystemExit("No supported package manager found (apt/dnf/yum/pacman/zypper).")
    else:
        raise SystemExit(f"Unsupported OS for auto-install: {system}")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        details = "\n".join([result.stdout.strip(), result.stderr.strip()]).strip()
        raise SystemExit(f"Auto-install failed: {details}")


def extract_chm(input_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    if not shutil.which("extract_chmLib"):
        _install_extract_tool()
        if not shutil.which("extract_chmLib"):
            raise SystemExit("extract_chmLib still missing after auto-install.")

    cmd = ["extract_chmLib", str(input_path), str(out_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        details = "\n".join([result.stdout.strip(), result.stderr.strip()]).strip()
        raise SystemExit(f"Failed to extract CHM (extract_chmLib): {details}")
