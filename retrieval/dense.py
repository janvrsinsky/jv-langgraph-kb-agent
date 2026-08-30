"""Semantic (dense) retrieval with a light offline fallback.

Real embeddings are a large download, so this module keeps them *optional*:

  * If sentence-transformers is installed and USE_ST=1 is set, real embeddings
    are used.
  * Otherwise it falls back to a hashed character-n-gram vector. That fallback
    is NOT a neural embedding and is clearly not one; it is a deterministic
    surface-similarity vector whose only job is to let this repo run end to end
    with zero downloads and no API key. It captures sub-word overlap, so it is
    robust to the inflection that trips exact-token BM25, which is enough for
    the fusion to have two genuinely different branches to combine.

The fallback is labeled at every boundary so nobody mistakes it for the model,
and the agent prints which backend is live when it starts.
"""

import hashlib
import math
import os

_DIM = 512
_NGRAM = 3


def _hash_bucket(gram: str) -> int:
    digest = hashlib.md5(gram.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % _DIM


def _char_ngram_vector(text: str) -> dict[int, float]:
    """L2-normalized hashed char-n-gram term vector (sparse dict)."""
    s = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    s = " ".join(s.split())
    counts: dict[int, float] = {}
    for token in s.split():
        padded = f" {token} "
        for i in range(len(padded) - _NGRAM + 1):
            bucket = _hash_bucket(padded[i : i + _NGRAM])
            counts[bucket] = counts.get(bucket, 0.0) + 1.0
    norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
    return {k: v / norm for k, v in counts.items()}


def _cosine_sparse(a: dict[int, float], b: dict[int, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


class DenseIndex:
    """Dense retrieval over a fixed document list, addressed by external id."""

    def __init__(self, ids: list[str], texts: list[str]):
        self.ids = list(ids)
        self.backend = "fallback-char-ngram"
        self._model = None

        if os.environ.get("USE_ST") == "1":
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore

                self._model = SentenceTransformer(
                    os.environ.get("ST_MODEL", "intfloat/multilingual-e5-small")
                )
                self.backend = "sentence-transformers"
            except Exception:
                # Any failure (missing package, no network) drops to fallback.
                self._model = None
                self.backend = "fallback-char-ngram"

        if self._model is not None:
            self._dense = self._model.encode(
                [f"passage: {t}" for t in texts], normalize_embeddings=True
            )
        else:
            self._sparse = [_char_ngram_vector(t) for t in texts]

    def _encode_query(self, query: str):
        if self._model is not None:
            return self._model.encode(
                [f"query: {query}"], normalize_embeddings=True
            )[0]
        return _char_ngram_vector(query)

    def search(self, query: str, k: int = 10) -> list[tuple[str, float]]:
        """Return the top-k (chunk_id, score) pairs, highest score first."""
        q = self._encode_query(query)
        scored: list[tuple[str, float]] = []

        if self._model is not None:
            for cid, vec in zip(self.ids, self._dense):
                scored.append((cid, float(sum(a * b for a, b in zip(q, vec)))))
        else:
            for cid, vec in zip(self.ids, self._sparse):
                sim = _cosine_sparse(q, vec)
                if sim > 0.0:
                    scored.append((cid, sim))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]
