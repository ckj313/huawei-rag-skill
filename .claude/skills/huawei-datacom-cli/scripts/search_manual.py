from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "scripts" / (Path(__file__).stem + ".py")


def main() -> int:
    cmd = [sys.executable, str(TARGET), *sys.argv[1:]]
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
