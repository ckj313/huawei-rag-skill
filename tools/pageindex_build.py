from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.chm_extract import resolve_manual_input, resolve_tree_dir
from src.pageindex_toolchain import build_pageindex_tree


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build PageIndex tree artifacts from a manual directory or CHM file "
            "using VectifyAI/PageIndex."
        )
    )
    parser.add_argument("--manual-dir", help="Manual source directory (markdown or html)")
    parser.add_argument("--chm-file", help="CHM file path, e.g. ~/Downloads/HUAWEI_usg.chm")
    parser.add_argument("--tree-dir", help="Explicit output tree directory")
    parser.add_argument(
        "--tree-root",
        default="data/pageindex",
        help="Tree root when --tree-dir is not set",
    )
    parser.add_argument(
        "--extract-root",
        default="manuals/chm",
        help="CHM extraction cache root",
    )
    parser.add_argument(
        "--cache-strategy",
        choices=["stem", "hash"],
        default="stem",
        help="CHM cache naming strategy",
    )
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help="Force re-extraction when CHM cache already exists",
    )
    parser.add_argument(
        "--pageindex-repo",
        help="Path to local VectifyAI/PageIndex repository",
    )
    parser.add_argument(
        "--include-glob",
        help="Optional glob filter for manual files, e.g. '*isis*'",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=0,
        help="Optional max documents to process (0 means no limit)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-2024-11-20",
        help="Model name passed to PageIndex (used when summaries are enabled in upstream code)",
    )
    parser.add_argument(
        "--out",
        default="artifacts/pageindex_build.json",
        help="JSON summary output path",
    )
    args = parser.parse_args()

    try:
        manual_dir, input_meta = resolve_manual_input(
            manual_dir=Path(args.manual_dir).expanduser().resolve() if args.manual_dir else None,
            chm_file=Path(args.chm_file).expanduser().resolve() if args.chm_file else None,
            extract_root=Path(args.extract_root).expanduser().resolve(),
            cache_strategy=args.cache_strategy,
            force_extract=args.force_extract,
        )
        tree_dir = resolve_tree_dir(
            explicit_tree_dir=Path(args.tree_dir).expanduser().resolve() if args.tree_dir else None,
            tree_root=Path(args.tree_root).expanduser().resolve(),
            source_key=str(input_meta["source_key"]),
        )
        summary = build_pageindex_tree(
            manual_dir=manual_dir,
            tree_dir=tree_dir,
            pageindex_repo=Path(args.pageindex_repo).expanduser().resolve() if args.pageindex_repo else None,
            include_glob=args.include_glob,
            max_docs=args.max_docs or None,
            model=args.model,
        )
    except Exception as exc:  # pragma: no cover - CLI guard
        print(
            json.dumps(
                {"status": "error", "error": str(exc)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    payload = {
        **summary,
        "input_type": input_meta["input_type"],
        "source_key": input_meta["source_key"],
    }
    if input_meta.get("chm_file"):
        payload["chm_file"] = input_meta["chm_file"]
    if input_meta.get("extract_status"):
        payload["extract_status"] = input_meta["extract_status"]
    if input_meta.get("extractor"):
        payload["extractor"] = input_meta["extractor"]
    if input_meta.get("extracted_file_count") is not None:
        payload["extracted_file_count"] = input_meta["extracted_file_count"]
    if args.include_glob:
        payload["include_glob"] = args.include_glob
    if args.max_docs:
        payload["max_docs"] = args.max_docs

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
