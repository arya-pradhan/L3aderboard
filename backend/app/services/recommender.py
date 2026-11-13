"""Content-based recommendations.

Builds a taste profile from the genres/tags of a user's highly-rated games and
scores candidate games by cosine similarity to that profile (TF-IDF over the
genre/tag "vocabulary"). Pure and framework-agnostic: it takes plain feature
lists and returns ranked keys, so it's easy to unit-test and reuse.

Works with sparse data — a single liked game already yields useful neighbours.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

@dataclass
class LikedItem:
    features: list[str]
    weight: float = 1.0


@dataclass
class CandidateItem:
    key: int
    features: list[str]


@dataclass
class ScoredItem:
    key: int
    score: float


def extract_features(genres: list[str] | None, tags: list[str] | None) -> list[str]:
    """Normalize genres + tags into single-word tokens (so multi-word genres
    like "Action RPG" stay one feature: "action_rpg")."""
    tokens: list[str] = []
    for value in (genres or []) + (tags or []):
        if not value:
            continue
        tokens.append(value.strip().lower().replace(" ", "_"))
    return tokens


def _norm(vec: dict[str, float]) -> dict[str, float]:
    length = math.sqrt(sum(v * v for v in vec.values()))
    return {k: v / length for k, v in vec.items()} if length else vec


def recommend(
    liked: list[LikedItem],
    candidates: list[CandidateItem],
    *,
    limit: int = 12,
) -> list[ScoredItem]:
    """Rank candidates by similarity to the weighted profile of liked items."""
    liked = [item for item in liked if item.features]
    candidates = [c for c in candidates if c.features]
    if not liked or not candidates:
        return []

    # TF-IDF with sklearn's defaults: smoothed idf, L2-normalized rows.
    docs = [Counter(item.features) for item in liked] + [
        Counter(c.features) for c in candidates
    ]
    df = Counter(token for doc in docs for token in doc)
    idf = {t: math.log((1 + len(docs)) / (1 + n)) + 1 for t, n in df.items()}
    vecs = [_norm({t: tf * idf[t] for t, tf in doc.items()}) for doc in docs]

    # Weighted average of the liked vectors = the user's taste profile.
    weights = [item.weight for item in liked]
    if sum(weights) <= 0:
        weights = [1.0] * len(liked)
    profile: Counter[str] = Counter()
    for w, vec in zip(weights, vecs):
        for t, v in vec.items():
            profile[t] += w * v
    profile = _norm(profile)

    scored = (
        ScoredItem(key=c.key, score=sum(profile.get(t, 0.0) * v for t, v in vec.items()))
        for c, vec in zip(candidates, vecs[len(liked):])
    )
    ranked = sorted(scored, key=lambda x: x.score, reverse=True)
    return [item for item in ranked if item.score > 0][:limit]
