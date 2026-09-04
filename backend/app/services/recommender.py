"""Content-based recommendations.

Builds a taste profile from the genres/tags of a user's highly-rated games and
scores candidate games by cosine similarity to that profile (TF-IDF over the
genre/tag "vocabulary"). Pure and framework-agnostic: it takes plain feature
lists and returns ranked keys, so it's easy to unit-test and reuse.

Works with sparse data — a single liked game already yields useful neighbours.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


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

    corpus = [item.features for item in liked] + [c.features for c in candidates]
    # analyzer=identity: each document is already a list of feature tokens.
    vectorizer = TfidfVectorizer(analyzer=lambda toks: toks)
    try:
        matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        # Empty vocabulary (no usable features anywhere).
        return []

    n_liked = len(liked)
    liked_matrix = matrix[:n_liked]
    candidate_matrix = matrix[n_liked:]

    # Weighted average of the liked vectors = the user's taste profile.
    weights = np.array([[item.weight for item in liked]], dtype=float)
    total = weights.sum()
    if total <= 0:
        weights = np.ones_like(weights)
        total = weights.sum()
    profile = (weights @ liked_matrix) / total  # (1, vocab)

    scores = cosine_similarity(np.asarray(profile), candidate_matrix)[0]

    ranked = sorted(
        (ScoredItem(key=candidates[i].key, score=float(s)) for i, s in enumerate(scores)),
        key=lambda x: x.score,
        reverse=True,
    )
    return [item for item in ranked if item.score > 0][:limit]
