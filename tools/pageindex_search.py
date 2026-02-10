from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pageindex_toolchain import search_pageindex_tree


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Search local PageIndex tree artifacts. "
            "Mode auto prefers LLM tree search and falls back to lexical BM25."
        )
    )
    parser.add_argument("--tree-dir", required=True, help="Directory containing manifest/nodes/bm25/trees")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--topk", type=int, default=8)
    parser.add_argument(
        "--mode",
        choices=["auto", "llm", "lexical"],
        default="auto",
        help="Search mode",
    )
    parser.add_argument(
        "--model",
        default="gpt-4.1",
        help="LLM model for tree search mode",
    )
    parser.add_argument(
        "--prefilter-k",
        type=int,
        default=50,
        help="Prefilter node count before LLM tree search",
    )
    parser.add_argument(
        "--out",
        default="artifacts/pageindex_results.json",
        help="Result JSON output path",
    )
    args = parser.parse_args()

    try:
        result = search_pageindex_tree(
            tree_dir=Path(args.tree_dir),
            query=args.query,
            topk=args.topk,
            mode=args.mode,
            model=args.model,
            prefilter_k=args.prefilter_k,
        )
    except Exception as exc:  # pragma: no cover - CLI guard
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
