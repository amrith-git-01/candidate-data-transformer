"""Write recruiter CSV export."""

from __future__ import annotations

import csv
from pathlib import Path

from sample_generator.models import SourceAssignment

CSV_HEADER = [
    "name",
    "email",
    "phone",
    "current_company",
    "title",
    "city",
    "region",
    "country",
    "linkedin_url",
]


def _csv_row(assignment: SourceAssignment) -> dict[str, str]:
    p = assignment.persona
    overrides = assignment.csv_overrides
    return {
        "name": overrides.get("name", p.full_name),
        "email": overrides.get("email", p.email) or "",
        "phone": overrides.get("phone", p.phone) or "",
        "current_company": overrides.get("current_company", p.company),
        "title": overrides.get("title", p.title),
        "city": overrides.get("city", p.city) or "",
        "region": overrides.get("region", p.region) or "",
        "country": overrides.get("country", p.country) or "",
        "linkedin_url": overrides.get("linkedin_url", p.linkedin_url) or "",
    }


def write_csv(assignments: list[SourceAssignment], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        for assignment in assignments:
            if not assignment.in_csv:
                continue
            row = _csv_row(assignment)
            writer.writerow(row)
            rows_written += 1
            for _ in range(assignment.csv_row_extra):
                writer.writerow(row)
                rows_written += 1
    return rows_written
