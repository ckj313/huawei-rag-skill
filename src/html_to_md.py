from __future__ import annotations

import re

from bs4 import BeautifulSoup

_META_CHARSET_RE = re.compile(r"charset=([A-Za-z0-9_-]+)", re.IGNORECASE)


def _detect_meta_charset(data: bytes) -> str | None:
    head = data[:4096].decode("latin-1", errors="ignore")
    match = _META_CHARSET_RE.search(head)
    if not match:
        return None
    return match.group(1).strip().lower()


def decode_html_bytes(data: bytes) -> str:
    charset = _detect_meta_charset(data)
    candidates = []
    if charset:
        candidates.append(charset)
    candidates.extend(["utf-8", "gb18030", "gbk", "gb2312"])

    for enc in candidates:
        try:
            return data.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("latin-1", errors="replace")


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
