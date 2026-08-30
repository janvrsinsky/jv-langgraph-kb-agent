"""Tokenization and a light, language-agnostic stemmer.

A real deployment would lemmatize with a morphological analyzer. That is a
dependency and, for an inflected language, a download; neither is needed to
show the architecture, so this module ships a small suffix-stripping stemmer
instead. It is a deliberate stand-in: it reproduces the effect that matters
here, matching inflected surface forms to a shared stem, with nothing
installed.
"""

import re

# A tiny stopword list. Kept short on purpose: enough to stop the most common
# function words from dominating BM25 term frequencies, not a full linguistic set.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "at", "is", "are",
    "was", "were", "be", "do", "does", "did", "how", "what", "why", "it", "its",
    "that", "this", "these", "those", "as", "for", "with", "into", "down", "up",
    "you", "your", "they", "their", "when", "can", "not", "but",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Ordered longest-first so multi-character suffixes strip before their subsets.
_SUFFIXES = ("ations", "ation", "edly", "ings", "ness", "ment",
             "ing", "ies", "ers", "est", "ed", "es", "ly", "s")


def tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumeric, drop stopwords."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


def light_stem(token: str) -> str:
    """Strip one common suffix, guarding against over-shortening.

    'electrons' -> 'electron', 'oscillation' -> 'oscill', 'slowed' -> 'slow'.
    Guard: never reduce a token below four characters, so short words survive.
    """
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    for suf in _SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 4:
            return token[: -len(suf)]
    return token


def tokenize_stem(text: str) -> list[str]:
    """Tokenize then stem each token."""
    return [light_stem(t) for t in tokenize(text)]
