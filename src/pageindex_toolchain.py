from __future__ import annotations

import asyncio
from collections import Counter
from datetime import UTC, datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import pickle
import re
import sys
from typing import Any

import openai

from src.bm25 import BM25Index
from src.html_to_md import decode_html_bytes, html_to_markdown


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _snippet(text: str, max_chars: int = 260) -> str:
    single_line = " ".join(text.split())
    if len(single_line) <= max_chars:
        return single_line
    return single_line[: max_chars - 3] + "..."


def _doc_id(source: str) -> str:
    return hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]


def _ensure_markdown_heading(text: str, source: str) -> str:
    if re.search(r"(?m)^\s*#{1,6}\s+\S+", text):
        return text
    title = Path(source).stem.replace("_", " ").strip() or "Document"
    return f"# {title}\n\n{text}"


def _iter_manual_docs(
    manual_dir: Path,
    include_glob: str | None = None,
    max_docs: int | None = None,
) -> list[tuple[str, str]]:
    docs: list[tuple[str, str]] = []

    md_files = sorted(manual_dir.rglob("*.md"))
    if include_glob:
        md_files = [path for path in md_files if path.match(include_glob)]

    for path in md_files:
        rel = str(path.relative_to(manual_dir))
        docs.append((rel, _safe_read_text(path)))
        if max_docs and len(docs) >= max_docs:
            return docs

    if docs:
        return docs

    html_files = sorted(manual_dir.rglob("*.htm")) + sorted(manual_dir.rglob("*.html"))
    if include_glob:
        html_files = [path for path in html_files if path.match(include_glob)]

    for path in html_files:
        rel = str(path.relative_to(manual_dir).with_suffix(".md"))
        html = decode_html_bytes(path.read_bytes())
        docs.append((rel, html_to_markdown(html)))
        if max_docs and len(docs) >= max_docs:
            break
    return docs


def _save_bm25(index: BM25Index, path: Path) -> None:
    with path.open("wb") as f:
        pickle.dump(
            {
                "docs": index.docs,
                "doc_freq": dict(index.doc_freq),
                "avgdl": index.avgdl,
                "k1": index.k1,
                "b": index.b,
            },
            f,
        )


def _load_bm25(path: Path) -> BM25Index:
    data = pickle.loads(path.read_bytes())
    return BM25Index(
        docs=data["docs"],
        doc_freq=Counter(data["doc_freq"]),
        avgdl=data["avgdl"],
        k1=data.get("k1", 1.5),
        b=data.get("b", 0.75),
    )


def _default_pageindex_repo() -> Path | None:
    env = os.getenv("PAGEINDEX_REPO")
    if env:
        return Path(env).expanduser().resolve()

    # Typical sibling layout:
    # /Users/xxx/code/PageIndex
    # /Users/xxx/code/huawei-rag-skill
    repo_root = Path(__file__).resolve().parent.parent
    sibling = (repo_root.parent / "PageIndex").resolve()
    if sibling.exists():
        return sibling
    return None


def _load_pageindex_md_builder(pageindex_repo: Path | None):
    repo = pageindex_repo or _default_pageindex_repo()
    if not repo:
        raise FileNotFoundError(
            "未找到 VectifyAI/PageIndex 仓库。请通过 --pageindex-repo 或环境变量 PAGEINDEX_REPO 指定路径。"
        )
    repo = repo.expanduser().resolve()
    module_path = repo / "pageindex" / "page_index_md.py"
    if not module_path.exists():
        raise FileNotFoundError(f"无效的 PageIndex 仓库路径: {repo}")

    # Ensure local repo version takes precedence over pip `pageindex` API client.
    for name in list(sys.modules.keys()):
        if name == "pageindex" or name.startswith("pageindex."):
            del sys.modules[name]
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))

    module = importlib.import_module("pageindex.page_index_md")
    if not hasattr(module, "md_content_to_tree"):
        raise RuntimeError("PageIndex 模块缺少 `md_content_to_tree`")
    return module.md_content_to_tree, repo


def _flatten_tree_nodes(
    doc_id: str,
    source: str,
    tree_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    structure = tree_payload.get("structure", [])
    if not isinstance(structure, list):
        return nodes

    def walk(node: dict[str, Any], path_titles: list[str]) -> None:
        title = str(node.get("title") or "").strip() or "Untitled"
        local_node_id = str(node.get("node_id") or "")
        path = path_titles + [title]
        text = str(node.get("text") or "")
        if not local_node_id:
            local_node_id = str(len(nodes)).zfill(4)
        global_node_id = f"{doc_id}:{local_node_id}"

        nodes.append(
            {
                "node_id": global_node_id,
                "doc_id": doc_id,
                "local_node_id": local_node_id,
                "path": path,
                "source": source,
                "title": title,
                "line_num": int(node.get("line_num") or 0),
                "text": text,
                "snippet": _snippet(text) if text else _snippet(" > ".join(path)),
            }
        )

        child_nodes = node.get("nodes") or []
        if isinstance(child_nodes, list):
            for child in child_nodes:
                if isinstance(child, dict):
                    walk(child, path)

    for root in structure:
        if isinstance(root, dict):
            walk(root, [])
    return nodes


def _compact_tree_for_prompt(tree_payload: dict[str, Any]) -> list[dict[str, Any]]:
    structure = tree_payload.get("structure", [])
    if not isinstance(structure, list):
        return []

    def compact(node: dict[str, Any]) -> dict[str, Any]:
        children = node.get("nodes") or []
        result: dict[str, Any] = {
            "title": str(node.get("title") or ""),
            "node_id": str(node.get("node_id") or ""),
        }
        if isinstance(children, list) and children:
            result["nodes"] = [compact(child) for child in children if isinstance(child, dict)]
        return result

    return [compact(node) for node in structure if isinstance(node, dict)]


def _extract_json_obj(content: str) -> dict[str, Any]:
    content = content.strip()
    if not content:
        return {}

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _resolve_openai_api_key() -> str | None:
    return os.getenv("CHATGPT_API_KEY") or os.getenv("OPENAI_API_KEY")


def build_pageindex_tree(
    manual_dir: Path,
    tree_dir: Path,
    *,
    pageindex_repo: Path | None = None,
    include_glob: str | None = None,
    max_docs: int | None = None,
    model: str = "gpt-4o-2024-11-20",
) -> dict[str, Any]:
    manual_root = Path(manual_dir).expanduser().resolve()
    tree_root = Path(tree_dir).expanduser().resolve()
    if not manual_root.exists():
        raise FileNotFoundError(f"manual_dir not found: {manual_root}")

    docs = _iter_manual_docs(manual_root, include_glob=include_glob, max_docs=max_docs)
    if not docs:
        raise ValueError(f"No markdown/html files found in {manual_root}")

    md_content_to_tree, repo_used = _load_pageindex_md_builder(pageindex_repo)
    tree_root.mkdir(parents=True, exist_ok=True)
    trees_root = tree_root / "trees"
    trees_root.mkdir(parents=True, exist_ok=True)

    all_nodes: list[dict[str, Any]] = []
    doc_records: list[dict[str, Any]] = []

    for source, text in docs:
        doc_id = _doc_id(source)
        markdown_text = _ensure_markdown_heading(text, source)
        tree_payload = asyncio.run(
            md_content_to_tree(
                markdown_content=markdown_text,
                if_thinning=False,
                min_token_threshold=5000,
                if_add_node_summary="no",
                summary_token_threshold=200,
                model=model,
                if_add_doc_description="no",
                if_add_node_text="yes",
                if_add_node_id="yes",
                doc_name=Path(source).stem,
            )
        )
        tree_file = trees_root / f"{doc_id}.json"
        tree_file.write_text(
            json.dumps(tree_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        nodes = _flatten_tree_nodes(doc_id, source, tree_payload)
        all_nodes.extend(nodes)
        doc_records.append(
            {
                "doc_id": doc_id,
                "source": source,
                "tree_file": str(tree_file.relative_to(tree_root)),
                "node_count": len(nodes),
            }
        )

    if not all_nodes:
        raise ValueError(f"PageIndex generated no nodes from {manual_root}")

    bm25 = BM25Index.build(node["text"] or " ".join(node["path"]) for node in all_nodes)
    _save_bm25(bm25, tree_root / "bm25.pkl")
    (tree_root / "nodes.json").write_text(
        json.dumps(all_nodes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (tree_root / "docs.json").write_text(
        json.dumps(doc_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    generated_at = _utc_now_iso()
    summary: dict[str, Any] = {
        "status": "ok",
        "manual_dir": str(manual_root),
        "tree_dir": str(tree_root),
        "pageindex_repo": str(repo_used),
        "file_count": len(docs),
        "node_count": len(all_nodes),
        "generated_at": generated_at,
    }
    (tree_root / "manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def _lexical_hits(
    nodes: list[dict[str, Any]],
    scores: list[float],
    topk: int,
) -> list[dict[str, Any]]:
    ranked = sorted(range(len(nodes)), key=lambda i: scores[i], reverse=True)
    hits: list[dict[str, Any]] = []
    for idx in ranked[: max(0, topk)]:
        node = nodes[idx]
        hits.append(
            {
                "node_id": node["node_id"],
                "path": node["path"],
                "score": round(float(scores[idx]), 6),
                "snippet": _snippet(node.get("text") or node.get("snippet") or ""),
                "source": node["source"],
            }
        )
    return hits


def _llm_tree_search_hits(
    *,
    tree_root: Path,
    query: str,
    nodes: list[dict[str, Any]],
    lexical_scores: list[float],
    model: str,
    prefilter_k: int,
    topk: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    docs = json.loads((tree_root / "docs.json").read_text(encoding="utf-8"))
    doc_map = {str(doc["doc_id"]): doc for doc in docs if isinstance(doc, dict)}
    node_map: dict[tuple[str, str], dict[str, Any]] = {}
    score_map: dict[str, float] = {}
    for node, score in zip(nodes, lexical_scores):
        key = (str(node["doc_id"]), str(node["local_node_id"]))
        node_map[key] = node
        score_map[str(node["node_id"])] = float(score)

    ranked = sorted(range(len(nodes)), key=lambda i: lexical_scores[i], reverse=True)
    doc_score: dict[str, float] = {}
    for idx in ranked[: max(prefilter_k, topk)]:
        doc_id = str(nodes[idx]["doc_id"])
        doc_score[doc_id] = max(doc_score.get(doc_id, float("-inf")), float(lexical_scores[idx]))
    candidate_docs = [doc_id for doc_id, _ in sorted(doc_score.items(), key=lambda x: x[1], reverse=True)[:5]]

    api_key = _resolve_openai_api_key()
    if not api_key:
        raise RuntimeError("LLM tree search 需要设置 CHATGPT_API_KEY 或 OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    client = openai.OpenAI(api_key=api_key, base_url=base_url or None)

    selected: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    seen_node_ids: set[str] = set()

    for doc_id in candidate_docs:
        doc = doc_map.get(doc_id)
        if not doc:
            continue
        tree_file = tree_root / str(doc.get("tree_file"))
        if not tree_file.exists():
            continue
        tree_payload = json.loads(tree_file.read_text(encoding="utf-8"))
        compact_tree = _compact_tree_for_prompt(tree_payload)
        prompt = f"""
You are given a query and the tree structure of a document.
You need to find all nodes that are likely to contain the answer.

Query: {query}

Document tree structure: {json.dumps(compact_tree, ensure_ascii=False)}

Reply in the following JSON format:
{{
  "thinking": "<reasoning>",
  "node_list": ["0001", "0002"]
}}

Return JSON only.
""".strip()
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        content = completion.choices[0].message.content or ""
        payload = _extract_json_obj(content)
        local_ids = payload.get("node_list") if isinstance(payload.get("node_list"), list) else []
        trace.append(
            {
                "doc_id": doc_id,
                "source": doc.get("source"),
                "node_list": local_ids,
                "thinking": payload.get("thinking", ""),
            }
        )

        for local_id in local_ids:
            key = (doc_id, str(local_id))
            node = node_map.get(key)
            if not node:
                continue
            node_id = str(node["node_id"])
            if node_id in seen_node_ids:
                continue
            seen_node_ids.add(node_id)
            selected.append(
                {
                    "node_id": node_id,
                    "path": node["path"],
                    "score": round(score_map.get(node_id, 0.0), 6),
                    "snippet": _snippet(node.get("text") or node.get("snippet") or ""),
                    "source": node["source"],
                }
            )
            if len(selected) >= topk:
                break
        if len(selected) >= topk:
            break

    return selected[:topk], trace


def search_pageindex_tree(
    tree_dir: Path,
    query: str,
    topk: int = 8,
    *,
    mode: str = "auto",
    model: str = "gpt-4.1",
    prefilter_k: int = 50,
) -> dict[str, Any]:
    if not query or not query.strip():
        raise ValueError("query cannot be empty")
    if mode not in {"auto", "llm", "lexical"}:
        raise ValueError("mode must be one of: auto, llm, lexical")

    tree_root = Path(tree_dir).expanduser().resolve()
    nodes_path = tree_root / "nodes.json"
    bm25_path = tree_root / "bm25.pkl"
    if not nodes_path.exists() or not bm25_path.exists():
        raise FileNotFoundError(f"tree artifacts not found in {tree_root}")

    nodes = json.loads(nodes_path.read_text(encoding="utf-8"))
    if not isinstance(nodes, list) or not nodes:
        return {"query": query, "hits": []}

    bm25 = _load_bm25(bm25_path)
    scores = bm25.score(query)
    if len(scores) != len(nodes):
        raise RuntimeError("nodes.json and bm25.pkl are inconsistent")

    should_use_llm = mode == "llm" or (mode == "auto" and _resolve_openai_api_key() is not None)
    if should_use_llm:
        try:
            hits, trace = _llm_tree_search_hits(
                tree_root=tree_root,
                query=query,
                nodes=nodes,
                lexical_scores=scores,
                model=model,
                prefilter_k=prefilter_k,
                topk=topk,
            )
            if hits:
                return {
                    "query": query,
                    "mode": "llm_tree_search",
                    "hits": hits,
                    "trace": trace,
                }
        except Exception as exc:
            if mode == "llm":
                raise
            fallback = _lexical_hits(nodes, scores, topk=topk)
            return {
                "query": query,
                "mode": "bm25_fallback",
                "warning": f"llm_tree_search_failed: {exc}",
                "hits": fallback,
            }

    hits = _lexical_hits(nodes, scores, topk=topk)
    return {
        "query": query,
        "mode": "bm25_lexical",
        "hits": hits,
    }
