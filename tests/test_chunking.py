from src.chunking import chunk_markdown


def test_chunk_markdown_keeps_section_title():
    text = """
# OSPF 配置

OSPF 配置说明第一段。

## 接口配置

接口配置说明。
"""
    chunks = chunk_markdown(text, source="doc.md", max_chars=50)
    assert any(c["section"].startswith("OSPF") for c in chunks)
    assert all("text" in c for c in chunks)
