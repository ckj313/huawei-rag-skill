from __future__ import annotations

from bs4 import BeautifulSoup


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup
    blocks: list[str] = []

    for child in body.children:
        if getattr(child, "name", None) is None:
            continue
        name = child.name.lower()
        if name in {"h1", "h2", "h3", "h4"}:
            level = int(name[1])
            heading = _text(child)
            if heading:
                blocks.append("#" * level + " " + heading)
        elif name == "p":
            text = _text(child)
            if text:
                blocks.append(text)
        elif name in {"ul", "ol"}:
            for li in child.find_all("li", recursive=False):
                text = _text(li)
                if text:
                    blocks.append("- " + text)
        elif name == "pre":
            code = child.get_text("\n", strip=True)
            if code:
                blocks.append("```\n" + code + "\n```")
        elif name == "table":
            rows = []
            for tr in child.find_all("tr", recursive=False):
                cells = [
                    _text(td)
                    for td in tr.find_all(["th", "td"], recursive=False)
                ]
                if cells:
                    rows.append(cells)
            if rows:
                header = rows[0]
                blocks.append("| " + " | ".join(header) + " |")
                blocks.append("| " + " | ".join(["---"] * len(header)) + " |")
                for row in rows[1:]:
                    blocks.append("| " + " | ".join(row) + " |")
        else:
            text = _text(child)
            if text:
                blocks.append(text)

    return "\n\n".join(blocks).strip() + "\n"
