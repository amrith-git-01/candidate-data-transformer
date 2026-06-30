"""Parse recruiter notes into RawRecords — conservative extraction only."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.adapters.link_detector import find_github_handle
from src.models import FieldValue, RawRecord
from src.normalize.location import normalize_country
from src.normalize.skills import extract_skills_from_text

logger = logging.getLogger(__name__)

SECTION_RE = re.compile(r"^=== Candidate:\s*(.+?)\s*===$", re.MULTILINE)
YEARS_RE = re.compile(r"(\d+)\+?\s*years?", re.IGNORECASE)
LOCATION_RE = re.compile(
    r"(?:based in|currently in|located in|lives in|conference in)\s+"
    r"([^,\n]+)"
    r"(?:,\s*([^,\n]+))?"
    r"(?:,\s*([^.,\n]+))?",
    re.IGNORECASE,
)
END_YEAR_RE = re.compile(r"graduated\s+(\d{4})", re.IGNORECASE)

_MAX_LOCATION_PART_LEN = 80
_MIN_YEARS = 1
_MAX_YEARS = 60
_MIN_INSTITUTION_LEN = 3
_MAX_INSTITUTION_LEN = 120

_LOCATION_REJECT_SUBSTRINGS = (
    "degree",
    " years",
    " experience",
    "github.com",
    " open source",
)

_EDUCATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"degree in\s+([^.,\n]+?)\s+from\s+([^.,\n]+)",
            re.IGNORECASE,
        ),
        "field_from",
    ),
    (
        re.compile(r"degree from\s+([^.,\n]+)", re.IGNORECASE),
        "institution",
    ),
    (
        re.compile(r"studied at\s+([^.,\n]+)", re.IGNORECASE),
        "institution",
    ),
    (
        re.compile(r"graduated from\s+([^.,\n]+)", re.IGNORECASE),
        "institution",
    ),
    (
        re.compile(r"mba from\s+([^.,\n]+)", re.IGNORECASE),
        "institution",
    ),
]


def _clean_location_part(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = raw.strip().rstrip(".")
    if not text or len(text) > _MAX_LOCATION_PART_LEN:
        return None
    lower = text.lower()
    if any(bad in lower for bad in _LOCATION_REJECT_SUBSTRINGS):
        return None
    return text


def _extract_location(body: str) -> dict[str, str]:
    match = LOCATION_RE.search(body)
    if not match:
        return {}

    out: dict[str, str] = {}
    city = _clean_location_part(match.group(1))
    region = _clean_location_part(match.group(2))
    country_raw = _clean_location_part(match.group(3))

    if city:
        out["city"] = city
    if region:
        out["region"] = region
    if country_raw:
        country = normalize_country(country_raw)
        if country:
            out["country"] = country
    return out


def _valid_institution(name: str | None) -> bool:
    if name is None:
        return False
    text = name.strip()
    if len(text) < _MIN_INSTITUTION_LEN or len(text) > _MAX_INSTITUTION_LEN:
        return False
    lower = text.lower()
    if any(bad in lower for bad in _LOCATION_REJECT_SUBSTRINGS):
        return False
    return True


def _extract_education(body: str) -> list[dict] | None:
    for pattern, kind in _EDUCATION_PATTERNS:
        match = pattern.search(body)
        if not match:
            continue
        if kind == "field_from":
            field = match.group(1).strip()
            institution = match.group(2).strip()
            if not _valid_institution(institution):
                continue
            entry: dict = {"institution": institution, "field": field}
        else:
            institution = match.group(1).strip()
            if not _valid_institution(institution):
                continue
            entry = {"institution": institution}
        if yr := END_YEAR_RE.search(body):
            entry["end_year"] = int(yr.group(1))
        return [entry]
    return None


def _extract_years(body: str) -> int | None:
    match = YEARS_RE.search(body)
    if not match:
        return None
    years = int(match.group(1))
    if _MIN_YEARS <= years <= _MAX_YEARS:
        return years
    return None


def parse_notes(path: str | Path) -> list[RawRecord]:
    path = Path(path)
    if not path.is_file():
        logger.error("Notes file not found: %s", path)
        return []

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.error("Failed to read notes %s: %s", path, exc)
        return []

    records: list[RawRecord] = []
    matches = list(SECTION_RE.finditer(text))

    for i, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        fields: dict[str, FieldValue] = {
            "full_name": FieldValue(value=name, method="direct"),
        }

        if years := _extract_years(body):
            fields["years_experience"] = FieldValue(
                value=years,
                method="extracted",
            )

        for skill in extract_skills_from_text(body):
            fields[f"skill_{skill}"] = FieldValue(value=skill, method="extracted")

        handle = find_github_handle(body)
        if handle:
            fields["github_url"] = FieldValue(
                value=f"https://github.com/{handle}",
                method="extracted",
            )

        for key, value in _extract_location(body).items():
            fields[key] = FieldValue(value=value, method="extracted")

        if education := _extract_education(body):
            fields["education"] = FieldValue(
                value=education,
                method="extracted",
            )

        records.append(RawRecord(source="recruiter_notes", fields=fields))

    return records
