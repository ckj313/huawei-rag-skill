from __future__ import annotations

import argparse
import json
import pickle
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.bm25 import BM25Index
from src.chunking import chunk_markdown
from src.html_to_md import decode_html_bytes, html_to_markdown

def _normalize_device(device: str) -> str:
    value = device.strip().lower()
    if "-v" in value and value.rsplit("-v", 1)[1].isdigit():
        return value.rsplit("-v", 1)[0]
    return value


def extract_chm(input_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["7z", "x", str(input_path), f"-o{out_dir}", "-y"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise SystemExit("7z not found. Please install p7zip first.") from exc

    if result.returncode != 0:
        details = "\n".join([result.stdout.strip(), result.stderr.strip()]).strip()
        raise SystemExit(f"Failed to extract CHM: {details}")


def convert_html_to_md(input_root: Path, out_root: Path) -> int:
    out_root.mkdir(parents=True, exist_ok=True)
    html_files = list(input_root.rglob("*.htm")) + list(input_root.rglob("*.html"))
    for html_path in html_files:
        rel = html_path.relative_to(input_root)
        out_path = out_root / rel.with_suffix(".md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        raw = html_path.read_bytes()
        html = decode_html_bytes(raw)
        md = html_to_markdown(html)
        out_path.write_text(md, encoding="utf-8")
    return len(html_files)


def build_index(manual_root: Path, out_dir: Path, max_chars: int, overlap: int) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)

    md_files = list(manual_root.rglob("*.md"))
    chunks = []
    chunk_id = 0
    for md_path in md_files:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        for chunk in chunk_markdown(
            text,
            source=str(md_path.relative_to(manual_root)),
            max_chars=max_chars,
            overlap=overlap,
        ):
            chunk_id += 1
            chunk["chunk_id"] = f"{chunk_id:06d}"
            chunks.append(chunk)

    texts = [c["text"] for c in chunks]
    bm25 = BM25Index.build(texts)

    meta_path = out_dir / "meta.json"
    meta_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

    bm25_path = out_dir / "bm25.pkl"
    with bm25_path.open("wb") as f:
        pickle.dump(
            {
                "docs": bm25.docs,
                "doc_freq": dict(bm25.doc_freq),
                "avgdl": bm25.avgdl,
                "k1": bm25.k1,
                "b": bm25.b,
            },
            f,
        )

    return len(chunks)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract CHM, convert HTML to Markdown, and build BM25 index in one command."
    )
    parser.add_argument(
        "--input",
        default="~/Downloads/HUAWEI_usg.chm",
        help="CHM file path (default: ~/Downloads/HUAWEI_usg.chm)",
    )
    parser.add_argument(
        "--device",
        default="usg",
        help="Device key used for output paths (default: usg)",
    )
    parser.add_argument("--html-out", help="HTML output directory override")
    parser.add_argument("--md-out", help="Markdown output directory override")
    parser.add_argument("--index-out", help="Index output directory override")
    parser.add_argument("--max-chars", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=100)
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"CHM not found: {input_path}")
    device = _normalize_device(args.device)

    html_out = (
        Path(args.html_out).expanduser().resolve()
        if args.html_out
        else (ROOT / "manuals" / device / "html")
    )
    md_out = (
        Path(args.md_out).expanduser().resolve()
        if args.md_out
        else (ROOT / "manuals" / device / "md")
    )
    index_out = (
        Path(args.index_out).expanduser().resolve()
        if args.index_out
        else (ROOT / "data" / device)
    )

    extract_chm(input_path, html_out)
    html_count = convert_html_to_md(html_out, md_out)
    chunk_count = build_index(md_out, index_out, args.max_chars, args.overlap)

    print(f"Extracted CHM -> {html_out}")
    print(f"Converted HTML to Markdown: {html_count} files -> {md_out}")
    print(f"Indexed {chunk_count} chunks -> {index_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
