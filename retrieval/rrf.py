"""Reciprocal rank fusion.

Combines several ranked lists into one without needing their scores to be on a
comparable scale. Each list contributes 1 / (c + rank) to every id it ranks;
sum across lists and re-sort. The constant c (default 60, the value from the
original Cormack et al. paper) damps the influence of the very top ranks so a
single list cannot dominate the fusion.

This is the whole point of the hybrid branch: BM25 and dense scores are not
comparable, but their *ranks* are, so RRF fuses them cleanly.
"""


def reciprocal_rank_fusion(
    rankings: list[list[tuple[str, float]]],
    k: int = 10,
    c: int = 60,
) -> list[tuple[str, float]]:
    """Fuse ranked (id, score) lists into one top-k (id, fused_score) list.

    Only ranks are used; incoming scores are ignored by design.
    """
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, (cid, _score) in enumerate(ranking):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (c + rank + 1)
    ordered = sorted(fused.items(), key=lambda pair: pair[1], reverse=True)
    return ordered[:k]
