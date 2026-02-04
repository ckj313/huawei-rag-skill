from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.bm25 import BM25Index
from src.experience import load_protocol_profiles, detect_intent


def _load_bm25(path: Path) -> BM25Index:
    data = pickle.loads(path.read_bytes())
    return BM25Index(
        docs=data["docs"],
        doc_freq=Counter(data["doc_freq"]),
        avgdl=data["avgdl"],
        k1=data.get("k1", 1.5),
        b=data.get("b", 0.75),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Search manuals using BM25")
    parser.add_argument("--input", help="Raw user input")
    parser.add_argument("--query", help="Search query (optional override)")
    parser.add_argument("--device", default="usg-v8")
    parser.add_argument("--index", help="Index directory override")
    parser.add_argument("--topk", type=int, default=5)
    args = parser.parse_args()

    raw_input = args.input or args.query or ""
    if not raw_input:
        raise SystemExit("--input or --query is required")

    profiles = load_protocol_profiles(ROOT / "experience/protocols")
    intent = detect_intent(raw_input, profiles)

    queries = []
    if args.query:
        queries.append(args.query)
    else:
        queries.append(raw_input)
        profile = intent.get("profile") or {}
        for q in profile.get("search_queries", []):
            queries.append(q)

    if args.index:
        index_dir = Path(args.index).expanduser().resolve()
    else:
        index_dir = ROOT / "data" / args.device
    meta_path = index_dir / "meta.json"
    bm25_path = index_dir / "bm25.pkl"

    if not meta_path.exists() or not bm25_path.exists():
        raise SystemExit(f"Index not found in {index_dir}. Run build_index.py first.")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    bm25 = _load_bm25(bm25_path)

    combined_scores = [0.0] * len(meta)
    for q in queries:
        scores = bm25.score(q)
        combined_scores = [max(a, b) for a, b in zip(combined_scores, scores)]

    ranked = sorted(range(len(meta)), key=lambda i: combined_scores[i], reverse=True)
    hits = []
    for i in ranked[: args.topk]:
        chunk = meta[i]
        hits.append({
            "chunk_id": chunk.get("chunk_id"),
            "score": round(combined_scores[i], 6),
            "source": chunk.get("source"),
            "section": chunk.get("section"),
            "title": chunk.get("title"),
            "text": chunk.get("text"),
        })

    output = {
        "input": raw_input,
        "protocol": intent.get("protocol"),
        "packet": intent.get("packet"),
        "device": args.device,
        "required_fields": intent.get("required_fields", []),
        "placeholder_fields": intent.get("placeholder_fields", []),
        "hits": hits,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
