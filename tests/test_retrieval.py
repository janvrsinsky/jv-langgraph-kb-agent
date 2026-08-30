"""Offline tests for the retrieval stack behind the agent's tool.

These import nothing but the retrieval package, which is standard library only.
CI runs this file with pytest and nothing else installed, so the "no dependency"
claim is proven by a job rather than asserted in a README.

The load-bearing test is test_dense_branch_rescues_a_lexical_miss: it is the one
that shows the second branch is doing real work.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from retrieval import (
    DENSE_ABSTAIN_FLOOR,
    Retrievers,
    load_kb,
    reciprocal_rank_fusion,
)


@pytest.fixture(scope="module")
def retrievers():
    return Retrievers(load_kb())


def _sources(retrievers, mode, query, k=4):
    return [retrievers.by_id[pid]["source"] for pid, _ in retrievers.search(mode, query, k)]


# ---------- the corpus itself ----------

def test_corpus_loads_with_unique_ids(retrievers):
    ids = [p["id"] for p in retrievers.passages]
    assert len(ids) == len(set(ids))
    assert len(retrievers.passages) > 50, "corpus too small for retrieval to discriminate"
    assert len({p["source"] for p in retrievers.passages}) >= 10


# ---------- each branch on its own ----------

def test_lexical_branch_finds_an_exact_term(retrievers):
    assert "hr-policies.md" in _sources(retrievers, "bm25_stem", "vacation days")


def test_stemming_matches_an_inflected_form(retrievers):
    """'batteries' must reach the passage that says 'battery'."""
    raw = _sources(retrievers, "bm25_raw", "swapping batteries", k=3)
    stemmed = _sources(retrievers, "bm25_stem", "swapping batteries", k=3)
    assert "acmecart-service-manual.md" in stemmed
    assert stemmed != raw or "acmecart-service-manual.md" in raw


def test_dense_branch_returns_something_for_anything(retrievers):
    """The property that makes the abstain floor necessary, stated as a test."""
    assert retrievers.dense.search("recipe for lasagne", 1)


# ---------- fusion ----------

def test_rrf_uses_ranks_not_scores():
    a = [("x", 1000.0), ("y", 999.0)]
    b = [("y", 0.02), ("x", 0.01)]
    fused = dict(reciprocal_rank_fusion([a, b], k=2))
    # x is rank 1 in a and rank 2 in b, y the other way round: a dead heat.
    assert fused["x"] == pytest.approx(fused["y"])


def test_hybrid_keeps_a_result_both_branches_agree_on(retrievers):
    assert "acmearm-service-manual.md" in _sources(retrievers, "hybrid", "maximum joint torque")


def test_dense_branch_rescues_a_lexical_miss(retrievers):
    """A real question in words that appear nowhere in the knowledge base.

    'phone', 'stolen' and 'do' are not KB vocabulary, so BM25 returns nothing at
    all. The dense branch still lands on the lost-device passage, and the hybrid
    result carries it. This is the case the old keyword-only tool got wrong.
    """
    query = "what do I do when my phone is stolen"
    assert retrievers.bm25_stem.search(query, 1) == []
    assert "security-policy.md" in _sources(retrievers, "dense", query)
    assert "security-policy.md" in _sources(retrievers, "hybrid", query)


# ---------- abstaining ----------

def test_abstains_on_a_query_with_no_evidence(retrievers):
    assert retrievers.has_evidence("xyzzy quux frobnicate") is False


def test_does_not_abstain_on_the_lexical_miss(retrievers):
    assert retrievers.has_evidence("what do I do when my phone is stolen") is True


def test_abstain_floor_sits_in_a_real_gap(retrievers):
    """The floor is measured, so the margin it was measured on is a test.

    If a corpus change closes this gap the build fails here rather than silently
    letting unanswerable questions through with four plausible passages.
    """
    def dense_top(query):
        hits = retrievers.dense.search(query, 1)
        return hits[0][1] if hits else 0.0

    unanswerable = max(dense_top(q) for q in (
        "recipe for lasagne", "xyzzy quux frobnicate", "quantum foam relativistic jam",
    ))
    answerable = dense_top("what do I do when my phone is stolen")

    assert unanswerable < DENSE_ABSTAIN_FLOOR <= answerable


def test_fallback_dense_branch_is_sensitive_to_phrasing(retrievers):
    """A known limitation, pinned so it stays visible.

    The offline dense branch is a hashed character n-gram vector, so it measures
    surface overlap. It carries "what do I do when my phone is stolen" to the
    right document, and it loses "stolen phone what to do", which is the same
    question with the words moved. A real embedding model (USE_ST=1) is what
    closes that gap; this test records where the stand-in stops.
    """
    def sources(query):
        return [retrievers.by_id[pid]["source"] for pid, _ in retrievers.search("hybrid", query, 4)]

    assert "security-policy.md" in sources("what do I do when my phone is stolen")
    assert "security-policy.md" not in sources("stolen phone what to do")
