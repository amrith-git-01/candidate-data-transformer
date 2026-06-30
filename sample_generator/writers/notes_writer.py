"""Write recruiter notes text export."""

from __future__ import annotations

from pathlib import Path

from sample_generator.models import SourceAssignment


def _notes_body(assignment: SourceAssignment) -> str:
    p = assignment.persona
    o = assignment.notes_overrides

    if "body" in o:
        return str(o["body"])

    parts: list[str] = []
    if p.notes_template:
        parts.append(p.notes_template)
    else:
        years = p.years_experience or 5
        skills = ", ".join(p.skills[:4]) if p.skills else "software development"
        parts.append(
            f"Candidate has {years} years experience with {skills}."
        )

    if p.city and p.region and "Based in" not in " ".join(parts):
        country = p.country or ""
        parts.append(f"Based in {p.city}, {p.region}, {country}.".replace(", ,", ","))

    handle = o.get("github_handle", p.github_handle)
    if assignment.embed_github_in_notes and handle:
        if f"github.com/{handle}" not in " ".join(parts):
            parts.append(f"See github.com/{handle} for open source work.")

    if p.education and "Studied at" not in " ".join(parts):
        inst = p.education[0].get("institution")
        if inst:
            parts.append(f"Degree from {inst}.")

    return " ".join(parts)


def write_notes(assignments: list[SourceAssignment], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    sections: list[str] = []
    count = 0
    for assignment in assignments:
        if not assignment.in_notes:
            continue
        p = assignment.persona
        body = _notes_body(assignment)
        sections.append(f"=== Candidate: {p.full_name} ===\n{body}\n")
        count += 1
    path.write_text("\n".join(sections), encoding="utf-8")
    return count
