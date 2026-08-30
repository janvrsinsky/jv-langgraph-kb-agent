"""Okapi BM25 lexical retrieval.

Pure-Python implementation so the eval runs with nothing but the standard
library. There is deliberately no optional accelerated backend: at this corpus
size scoring is instant, and a second scoring path with its own IDF variant
would let local runs drift from the published table.

The `stem` flag toggles the light stemmer from text.py. Running the index once
raw and once stemmed is what surfaces the lemmatization lift in the eval table:
on an inflected corpus, matching stems recovers recall that exact tokens miss.
"""

import math

from .text import tokenize, tokenize_stem


class BM25Index:
    """BM25 over a fixed list of documents, addressed by external id."""

    def __init__(self, ids: list[str], texts: list[str], *, stem: bool = True,
                 k1: float = 1.5, b: float = 0.75):
        self.ids = list(ids)
        self.stem = stem
        self.k1 = k1
        self.b = b
        self._tok = tokenize_stem if stem else tokenize

        self.docs = [self._tok(t) for t in texts]
        self.doc_len = [len(d) for d in self.docs]
        self.avgdl = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 0.0
        self.n = len(self.docs)

        # Document frequency per term.
        df: dict[str, int] = {}
        for doc in self.docs:
            for term in set(doc):
                df[term] = df.get(term, 0) + 1
        self.df = df
        self.idf = {
            term: math.log(1.0 + (self.n - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

        # Term-frequency tables per document.
        self.tf: list[dict[str, int]] = []
        for doc in self.docs:
            counts: dict[str, int] = {}
            for term in doc:
                counts[term] = counts.get(term, 0) + 1
            self.tf.append(counts)

    def search(self, query: str, k: int = 10) -> list[tuple[str, float]]:
        """Return the top-k (chunk_id, score) pairs, highest score first."""
        q_terms = self._tok(query)

        scored: list[tuple[str, float]] = []
        for i, counts in enumerate(self.tf):
            dl = self.doc_len[i]
            score = 0.0
            for term in q_terms:
                f = counts.get(term)
                if not f:
                    continue
                idf = self.idf.get(term, 0.0)
                denom = f + self.k1 * (1.0 - self.b + self.b * dl / (self.avgdl or 1.0))
                score += idf * (f * (self.k1 + 1.0)) / denom
            if score > 0.0:
                scored.append((self.ids[i], score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]
