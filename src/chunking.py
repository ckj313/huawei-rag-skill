from __future__ import annotations

from typing import Iterable


def _split_into_chunks(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def chunk_markdown(text: str, source: str, max_chars: int = 800, overlap: int = 100) -> list[dict]:
    lines = text.splitlines()
    title = ""
    section = ""
    buffer: list[str] = []
    chunks: list[dict] = []

    def flush_buffer():
        nonlocal buffer
        content = "\n".join(buffer).strip()
        buffer = []
        if not content:
            return
        for part in _split_into_chunks(content, max_chars, overlap):
            chunks.append({
                "source": source,
                "title": title or section or source,
                "section": section or title or source,
                "text": part.strip(),
            })

    for line in lines:
        if line.startswith("#"):
            flush_buffer()
            heading = line.lstrip("#").strip()
            level = len(line) - len(line.lstrip("#"))
            if level == 1:
                title = heading
                section = heading
            else:
                section = (title + " / " + heading) if title else heading
            buffer.append(line)
        else:
            buffer.append(line)

    flush_buffer()
    return chunks
