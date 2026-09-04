"""Unit tests for RAWG response normalization."""
from datetime import date

from app.services.rawg import _normalize


def test_normalize_handles_null_lists():
    # RAWG returns null (not absent) for these on some games.
    raw = {
        "id": 42,
        "name": "Nully Game",
        "genres": None,
        "tags": None,
        "platforms": None,
        "background_image": None,
        "released": None,
    }
    g = _normalize(raw)
    assert g.rawg_id == 42
    assert g.title == "Nully Game"
    assert g.genres == []
    assert g.tags == []
    assert g.platforms == []
    assert g.cover_url is None
    assert g.release_date is None


def test_normalize_extracts_fields_and_filters_tags():
    raw = {
        "id": 9743,
        "name": "Hollow Knight",
        "genres": [{"name": "Indie"}, {"name": "Action"}],
        "tags": [
            {"name": "Metroidvania", "language": "eng"},
            {"name": "Метроидвания", "language": "rus"},
        ],
        "platforms": [{"platform": {"name": "PC"}}, {"platform": {"name": "Switch"}}],
        "background_image": "https://media.rawg.io/hk.jpg",
        "released": "2017-02-23",
    }
    g = _normalize(raw)
    assert g.genres == ["Indie", "Action"]
    assert g.tags == ["Metroidvania"]  # non-English filtered out
    assert g.platforms == ["PC", "Switch"]
    assert g.cover_url == "https://media.rawg.io/hk.jpg"
    assert g.release_date == date(2017, 2, 23)
