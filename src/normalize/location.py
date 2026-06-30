"""Location normalization — country to ISO-3166 alpha-2 via pycountry."""

from __future__ import annotations

import pycountry

from src.models import Location


def normalize_country(raw: str | None) -> str | None:
    if raw is None or not str(raw).strip():
        return None
    text = str(raw).strip()
    upper = text.upper()
    if len(upper) == 2:
        match = pycountry.countries.get(alpha_2=upper)
        if match:
            return match.alpha_2
    if len(upper) == 3:
        match = pycountry.countries.get(alpha_3=upper)
        if match:
            return match.alpha_2
    try:
        return pycountry.countries.lookup(text).alpha_2
    except LookupError:
        return None


def normalize_city_region(raw: str | None) -> str | None:
    if raw is None or not str(raw).strip():
        return None
    return " ".join(part.capitalize() for part in str(raw).strip().split())


def normalize_location(
    city: str | None = None,
    region: str | None = None,
    country: str | None = None,
) -> Location:
    return Location(
        city=normalize_city_region(city),
        region=normalize_city_region(region),
        country=normalize_country(country),
    )
