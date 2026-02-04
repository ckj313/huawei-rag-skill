from src.html_to_md import html_to_markdown


def test_html_to_markdown_basic():
    html = """
    <html><body>
      <h1>OSPF 基本配置</h1>
      <p>配置 OSPF 进程。</p>
      <ul><li>进入系统视图</li><li>创建进程</li></ul>
    </body></html>
    """
    md = html_to_markdown(html)
    assert "# OSPF 基本配置" in md
    assert "配置 OSPF 进程" in md
    assert "- 进入系统视图" in md
