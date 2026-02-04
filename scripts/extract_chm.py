from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract CHM to HTML using 7z")
    parser.add_argument("--input", required=True, help="CHM file path")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["7z", "x", str(input_path), f"-o{out_dir}", "-y"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        return result.returncode
    print(f"Extracted to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
