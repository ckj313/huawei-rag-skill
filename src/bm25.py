from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text)
    return tokens


class BM25Index:
    def __init__(self, docs: list[list[str]], doc_freq: Counter, avgdl: float, k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.doc_freq = doc_freq
        self.avgdl = avgdl
        self.k1 = k1
        self.b = b
        self.N = len(docs)

    @classmethod
    def build(cls, texts: Iterable[str]) -> "BM25Index":
        docs: list[list[str]] = [tokenize(text) for text in texts]
        doc_freq: Counter = Counter()
        for doc in docs:
            for term in set(doc):
                doc_freq[term] += 1
        avgdl = (sum(len(doc) for doc in docs) / len(docs)) if docs else 0.0
        return cls(docs, doc_freq, avgdl)

    def score(self, query: str) -> list[float]:
        q_tokens = tokenize(query)
        scores = [0.0 for _ in self.docs]
        if not self.docs:
            return scores
        for i, doc in enumerate(self.docs):
            dl = len(doc)
            tf = Counter(doc)
            for term in q_tokens:
                if term not in tf:
                    continue
                df = self.doc_freq.get(term, 0)
                idf = math.log(1 + (self.N - df + 0.5) / (df + 0.5))
                denom = tf[term] + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                scores[i] += idf * (tf[term] * (self.k1 + 1) / denom)
        return scores
