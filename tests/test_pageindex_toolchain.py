from __future__ import annotations

import json
from pathlib import Path

from src.pageindex_toolchain import build_pageindex_tree, search_pageindex_tree


def _seed_manuals(manual_dir: Path) -> None:
    (manual_dir / "routing").mkdir(parents=True, exist_ok=True)
    (manual_dir / "routing" / "isis.md").write_text(
        "# ISIS 配置\n\n## 基础\n\n进入 ISIS 进程：isis <process-id>\n\n## NET\n\n配置 network-entity。\n",
        encoding="utf-8",
    )
    (manual_dir / "routing" / "ospf.md").write_text(
        "# OSPF 配置\n\n## 基础\n\n进入 OSPF 进程：ospf <process-id>\n",
        encoding="utf-8",
    )


def test_build_pageindex_tree_writes_expected_artifacts(tmp_path: Path) -> None:
    manual_dir = tmp_path / "manuals"
    _seed_manuals(manual_dir)
    tree_dir = tmp_path / "data" / "pageindex" / "usg"

    summary = build_pageindex_tree(manual_dir, tree_dir, max_docs=10)

    assert summary["status"] == "ok"
    assert summary["node_count"] > 0
    assert (tree_dir / "nodes.json").exists()
    assert (tree_dir / "bm25.pkl").exists()
    assert (tree_dir / "manifest.json").exists()

    tree_payload = json.loads((tree_dir / "nodes.json").read_text(encoding="utf-8"))
    first = tree_payload[0]
    assert {"node_id", "path", "source", "text", "snippet", "local_node_id"} <= set(first)


def test_search_pageindex_tree_returns_ranked_hits(tmp_path: Path) -> None:
    manual_dir = tmp_path / "manuals"
    _seed_manuals(manual_dir)
    tree_dir = tmp_path / "data" / "pageindex" / "usg"
    build_pageindex_tree(manual_dir, tree_dir, max_docs=10)

    result = search_pageindex_tree(tree_dir, query="isis network-entity", topk=3, mode="lexical")

    assert result["query"] == "isis network-entity"
    assert result["hits"]
    first = result["hits"][0]
    assert {"node_id", "path", "score", "snippet", "source"} <= set(first)
    assert all(first["score"] >= hit["score"] for hit in result["hits"][1:])
    text = first["snippet"].lower()
    assert "isis" in text or "network-entity" in text
