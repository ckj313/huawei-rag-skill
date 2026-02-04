from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.bm25 import BM25Index
from src.chunking import chunk_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Build BM25 index from Markdown manuals")
    parser.add_argument("--manual", required=True, help="Markdown root directory")
    parser.add_argument("--out", required=True, help="Output index directory")
    parser.add_argument("--max-chars", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=100)
    args = parser.parse_args()

    manual_root = Path(args.manual).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    md_files = list(manual_root.rglob("*.md"))
    chunks = []
    chunk_id = 0
    for md_path in md_files:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        for chunk in chunk_markdown(text, source=str(md_path.relative_to(manual_root)), max_chars=args.max_chars, overlap=args.overlap):
            chunk_id += 1
            chunk["chunk_id"] = f"{chunk_id:06d}"
            chunks.append(chunk)

    texts = [c["text"] for c in chunks]
    bm25 = BM25Index.build(texts)

    meta_path = out_dir / "meta.json"
    meta_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

    bm25_path = out_dir / "bm25.pkl"
    with bm25_path.open("wb") as f:
        pickle.dump({
            "docs": bm25.docs,
            "doc_freq": dict(bm25.doc_freq),
            "avgdl": bm25.avgdl,
            "k1": bm25.k1,
            "b": bm25.b,
        }, f)

    print(f"Indexed {len(chunks)} chunks -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
