import pytest

from src.normalize.location import (
    normalize_city_region,
    normalize_country,
    normalize_location,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("US", "US"),
        ("USA", "US"),
        ("United States", "US"),
        ("Canada", "CA"),
        ("CA", "CA"),
        ("Norway", "NO"),
        ("Singapore", "SG"),
    ],
)
def test_normalize_country_iso(raw, expected):
    assert normalize_country(raw) == expected


def test_normalize_country_invalid_returns_none():
    assert normalize_country("INVALID_COUNTRY") is None
    assert normalize_country("") is None


def test_normalize_city_region_title_case():
    assert normalize_city_region("san francisco") == "San Francisco"
    assert normalize_city_region("  new york ") == "New York"


def test_normalize_location_object():
    loc = normalize_location(city="portland", region="oregon", country="United States")
    assert loc.city == "Portland"
    assert loc.region == "Oregon"
    assert loc.country == "US"
