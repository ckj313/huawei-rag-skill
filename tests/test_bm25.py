from src.bm25 import BM25Index


def test_bm25_ranks_relevant_doc_higher():
    docs = [
        "ospf 基本配置 进入系统视图",
        "bgp 邻居配置 基本步骤",
    ]
    index = BM25Index.build(docs)
    scores = index.score("ospf 配置")
    assert scores[0] > scores[1]
