"""Write ATS JSON export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sample_generator.models import SourceAssignment


def _ats_entry(assignment: SourceAssignment) -> dict[str, Any]:
    p = assignment.persona
    o = assignment.ats_overrides

    entry: dict[str, Any] = {
        "candidate_name": o.get("candidate_name", p.full_name),
        "contact_email": o.get("contact_email", p.email),
        "contact_phone": o.get("contact_phone", p.phone),
        "employer": o.get("employer", p.company),
        "job_title": o.get("job_title", p.title),
    }

    headline = o.get("headline", p.headline)
    if headline:
        entry["headline"] = headline

    linkedin = o.get("linkedin_url", p.linkedin_url)
    if linkedin:
        entry["linkedin_url"] = linkedin

    if not assignment.suppress_ats_github and p.github_handle:
        entry["github_url"] = f"https://github.com/{p.github_handle}"

    if p.city or p.region or p.country:
        entry["location"] = {
            "city": o.get("city", p.city),
            "region": o.get("region", p.region),
            "country": o.get("country", p.country),
        }

    education = o.get("education", p.education)
    if education:
        entry["education"] = education

    return entry


def write_ats(assignments: list[SourceAssignment], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    candidates = []
    for assignment in assignments:
        if assignment.in_ats:
            candidates.append(_ats_entry(assignment))
    path.write_text(
        json.dumps({"candidates": candidates}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return len(candidates)
