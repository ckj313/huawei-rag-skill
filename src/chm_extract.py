from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def extract_chm(input_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    if not shutil.which("extract_chmLib"):
        raise SystemExit("extract_chmLib not found. Please install chmlib tools.")

    cmd = ["extract_chmLib", str(input_path), str(out_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        details = "\n".join([result.stdout.strip(), result.stderr.strip()]).strip()
        raise SystemExit(f"Failed to extract CHM (extract_chmLib): {details}")
