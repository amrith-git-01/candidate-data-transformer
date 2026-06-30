"""Shared scenario mutation helpers."""

from __future__ import annotations

import random

from sample_generator import config
from sample_generator.models import SourceAssignment


def typo_email(email: str, rng: random.Random) -> str:
    if "@" not in email:
        return email + "x"
    local, domain = email.split("@", 1)
    if len(local) > 3 and rng.random() < 0.5:
        idx = rng.randint(1, len(local) - 2)
        local = local[:idx] + local[idx + 1] + local[idx] + local[idx + 1 :]
    else:
        domain = domain.replace(".", "x.", 1) if "." in domain else domain + "x"
    return f"{local}@{domain}"


def alt_title(title: str, rng: random.Random) -> str:
    suffix = rng.choice(config.ALT_TITLE_SUFFIXES)
    if suffix.lower() == title.lower():
        return title + " II"
    return suffix


def apply_happy_path(a: SourceAssignment) -> None:
    a.in_csv = True
    a.in_ats = True
    a.in_notes = True


def apply_title_conflict(a: SourceAssignment, rng: random.Random) -> None:
    a.in_csv = True
    a.in_ats = True
    a.csv_overrides["title"] = a.persona.title
    a.ats_overrides["job_title"] = alt_title(a.persona.title, rng)


def apply_email_typo(a: SourceAssignment, rng: random.Random) -> None:
    a.in_csv = True
    a.in_ats = True
    if a.persona.email:
        a.csv_overrides["email"] = a.persona.email
        a.ats_overrides["contact_email"] = typo_email(a.persona.email, rng)


def apply_phone_join(a: SourceAssignment) -> None:
    a.in_csv = True
    a.in_ats = True
    a.in_notes = False
    if a.persona.email:
        a.csv_overrides["email"] = a.persona.email
        a.csv_overrides["phone"] = ""
    if a.persona.phone:
        a.ats_overrides["contact_phone"] = a.persona.phone
        a.ats_overrides["contact_email"] = None


def apply_csv_only(a: SourceAssignment) -> None:
    a.in_csv = True
    a.in_ats = False
    a.in_notes = False


def apply_ats_notes_only(a: SourceAssignment) -> None:
    a.in_csv = False
    a.in_ats = True
    a.in_notes = True


def apply_notes_only(a: SourceAssignment) -> None:
    a.in_csv = False
    a.in_ats = False
    a.in_notes = True


def apply_glitch_email(a: SourceAssignment) -> None:
    a.in_csv = False
    a.in_ats = True
    a.ats_overrides["contact_email"] = "not-an-email"
    a.ats_overrides["job_title"] = None


def apply_github_text_only(a: SourceAssignment, rng: random.Random) -> None:
    a.in_notes = True
    a.in_ats = True
    a.suppress_ats_github = True
    a.embed_github_in_notes = True
    if not a.persona.github_handle:
        handle = rng.choice(config.REAL_GITHUB_HANDLES)
        a.notes_overrides["github_handle"] = handle


def apply_github_404(a: SourceAssignment) -> None:
    a.in_notes = True
    fake = f"jane-doe-nonexistent-handle-{a.persona.person_id}"
    a.notes_overrides["github_handle"] = fake
    a.persona.github_handle = fake
    a.persona.github_is_real = False


def apply_csv_duplicate(a: SourceAssignment) -> None:
    a.in_csv = True
    a.csv_row_extra = 1
