from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.html_to_md import html_to_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert HTML files to Markdown")
    parser.add_argument("--input", required=True, help="HTML root directory")
    parser.add_argument("--out", required=True, help="Markdown output directory")
    args = parser.parse_args()

    input_root = Path(args.input).expanduser().resolve()
    out_root = Path(args.out).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    html_files = list(input_root.rglob("*.htm")) + list(input_root.rglob("*.html"))
    for html_path in html_files:
        rel = html_path.relative_to(input_root)
        out_path = out_root / rel.with_suffix(".md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        html = html_path.read_text(encoding="utf-8", errors="ignore")
        md = html_to_markdown(html)
        out_path.write_text(md, encoding="utf-8")

    print(f"Converted {len(html_files)} files to {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
