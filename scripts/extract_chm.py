from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract CHM to HTML using extract_chmLib")
    parser.add_argument("--input", required=True, help="CHM file path")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from src.chm_extract import extract_chm

    input_path = Path(args.input).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    extract_chm(input_path, out_dir)
    print(f"Extracted to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
