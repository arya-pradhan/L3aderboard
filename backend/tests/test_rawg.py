"""Unit tests for RAWG response normalization."""
from datetime import date

from app.services.rawg import _normalize, _normalize_detail


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


def test_normalize_detail_ratings_and_screenshots():
    raw = {
        "id": 9743,
        "name": "Hollow Knight",
        "rating": 4.4,
        "ratings_count": 3000,
        "ratings": [
            {"id": 5, "title": "exceptional", "count": 2000, "percent": 66.7},
            {"id": 4, "title": "recommended", "count": 900, "percent": 30.0},
        ],
        "metacritic": 87,
        "playtime": 24,
        "description_raw": "Bugs.",
    }
    shots = {"results": [{"image": "https://a.jpg"}, {"image": None}, {"image": "https://b.jpg"}]}
    d = _normalize_detail(raw, shots)
    assert d.title == "Hollow Knight" and d.description == "Bugs."
    assert d.screenshots == ["https://a.jpg", "https://b.jpg"]
    assert [r.title for r in d.ratings] == ["exceptional", "recommended"]
    assert (d.rating, d.ratings_count, d.metacritic, d.playtime) == (4.4, 3000, 87, 24)


def test_normalize_detail_unrated_game():
    d = _normalize_detail({"id": 1, "name": "New", "rating": 0, "playtime": 0}, None)
    assert d.rating is None and d.playtime is None
    assert d.screenshots == [] and d.ratings == [] and d.ratings_count == 0
