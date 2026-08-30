"""Knowledge-base loading and the retrieval branches wired together.

One place builds every branch, so the agent's tool and any eval over this
corpus agree on exactly what 'bm25' / 'dense' / 'hybrid' mean. No hidden
divergence between what is measured and what is served.

The corpus is the markdown in kb/: each blank-line-separated paragraph becomes
one passage, addressed by an id that carries its source document, so a citation
never has to be reconstructed after the fact.
"""

import re
from pathlib import Path

from .bm25 import BM25Index
from .dense import DenseIndex
from .rrf import reciprocal_rank_fusion

MODES = ("bm25_raw", "bm25_stem", "dense", "hybrid")

# Abstain floor for the dense branch. A dense retriever always returns
# *something*, because surface similarity is never exactly zero, so without a
# floor the caller gets four plausible-looking passages for a question this
# corpus cannot answer. That is the failure mode a keyword tool did not have and
# a hybrid one does.
#
# Measured over this corpus (85 passages, 13 documents): queries the KB cannot
# answer and that match no term ("recipe for lasagne", "xyzzy quux frobnicate")
# top out at 0.259 on the dense branch, while a real question phrased in words
# that appear nowhere in the KB ("what do I do when my phone is stolen") reaches
# 0.323 and is answered correctly. 0.28 sits in that gap, and a test pins the
# gap so a corpus change that closes it fails the build. Re-measure when the
# corpus changes: this is a property of the corpus, not a constant.
DENSE_ABSTAIN_FLOOR = 0.28

_DEFAULT_KB = Path(__file__).resolve().parent.parent / "kb"
_MIN_PASSAGE_CHARS = 40


def load_kb(kb_dir: Path | str = _DEFAULT_KB) -> list[dict]:
    """Load kb/*.md into passages: [{id, source, text}, ...].

    Paragraphs shorter than _MIN_PASSAGE_CHARS are dropped: they are headings
    and list fragments, and they add noise to term statistics without ever
    being a useful answer on their own.
    """
    passages: list[dict] = []
    for doc in sorted(Path(kb_dir).glob("*.md")):
        for n, para in enumerate(re.split(r"\n\s*\n", doc.read_text(encoding="utf-8"))):
            para = para.strip()
            if len(para) > _MIN_PASSAGE_CHARS:
                passages.append({
                    "id": f"{doc.stem}#{n}",
                    "source": doc.name,
                    "text": para,
                })
    if not passages:
        raise ValueError(f"no passages loaded from {kb_dir}")
    return passages


class Retrievers:
    """Holds every retrieval branch over one corpus and dispatches by mode."""

    def __init__(self, passages: list[dict]):
        self.passages = passages
        self.by_id = {p["id"]: p for p in passages}
        ids = [p["id"] for p in passages]
        texts = [p["text"] for p in passages]

        self.bm25_raw = BM25Index(ids, texts, stem=False)
        self.bm25_stem = BM25Index(ids, texts, stem=True)
        self.dense = DenseIndex(ids, texts)

    @property
    def dense_backend(self) -> str:
        return self.dense.backend

    def has_evidence(self, query: str) -> bool:
        """True when at least one branch actually recognises the query.

        Lexical evidence is binary and trustworthy: BM25 scores above zero only
        when a query term is really in a passage. The dense branch has no such
        zero, so it is held to the measured floor above. Either one is enough,
        which is the point of running both.
        """
        if self.bm25_stem.search(query, 1):
            return True
        dense_top = self.dense.search(query, 1)
        return bool(dense_top) and dense_top[0][1] >= DENSE_ABSTAIN_FLOOR

    def search(self, mode: str, query: str, k: int = 4) -> list[tuple[str, float]]:
        """Return top-k (passage_id, score) for the requested mode."""
        if mode == "bm25_raw":
            return self.bm25_raw.search(query, k)
        if mode in ("bm25", "bm25_stem"):
            return self.bm25_stem.search(query, k)
        if mode == "dense":
            return self.dense.search(query, k)
        if mode == "hybrid":
            # Fuse the stronger lexical branch (stemmed) with the dense branch.
            lex = self.bm25_stem.search(query, max(k, 10))
            sem = self.dense.search(query, max(k, 10))
            return reciprocal_rank_fusion([lex, sem], k=k)
        raise ValueError(f"unknown retrieval mode: {mode}")
