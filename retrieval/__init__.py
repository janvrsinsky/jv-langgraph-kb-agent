"""Retrieval package: lexical (BM25), dense, and RRF fusion over the knowledge base.

This is the same retrieval stack that is measured and CI-gated in
jv-podcast-rag, ported here so the agent's tool does real hybrid retrieval
instead of a toy keyword match. Pure standard library: no dependency, no
download, no API key.
"""

from .bm25 import BM25Index
from .dense import DenseIndex
from .pipeline import DENSE_ABSTAIN_FLOOR, MODES, Retrievers, load_kb
from .rrf import reciprocal_rank_fusion

__all__ = [
    "BM25Index",
    "DenseIndex",
    "Retrievers",
    "MODES",
    "DENSE_ABSTAIN_FLOOR",
    "load_kb",
    "reciprocal_rank_fusion",
]
