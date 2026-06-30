"""Unit tests for scenario mutators."""

from __future__ import annotations

import random

import pytest

from sample_generator.models import Persona, SourceAssignment
from sample_generator.scenarios import mutators


def _persona(**kwargs) -> Persona:
    defaults = dict(
        person_id="test-person",
        full_name="Jane Doe",
        email="jane.doe@example.com",
        phone="+1-415-555-0100",
        company="Acme Corp",
        title="Software Engineer",
        city="San Francisco",
        region="CA",
        country="US",
        linkedin_url=None,
        github_handle="torvalds",
    )
    defaults.update(kwargs)
    return Persona(**defaults)


def _assignment(**persona_kwargs) -> SourceAssignment:
    return SourceAssignment(persona=_persona(**persona_kwargs))


def test_happy_path_forces_all_sources() -> None:
    a = _assignment()
    a.in_csv = a.in_ats = a.in_notes = False
    mutators.apply_happy_path(a)
    assert a.in_csv and a.in_ats and a.in_notes


def test_title_conflict_sets_different_titles() -> None:
    rng = random.Random(0)
    a = _assignment()
    mutators.apply_title_conflict(a, rng)
    assert a.csv_overrides["title"] == "Software Engineer"
    assert a.ats_overrides["job_title"] != a.csv_overrides["title"]


def test_email_typo_changes_ats_email_only() -> None:
    rng = random.Random(0)
    a = _assignment()
    mutators.apply_email_typo(a, rng)
    assert a.csv_overrides["email"] == "jane.doe@example.com"
    assert a.ats_overrides["contact_email"] != a.csv_overrides["email"]


def test_phone_join_splits_contact_fields() -> None:
    a = _assignment()
    mutators.apply_phone_join(a)
    assert a.csv_overrides["phone"] == ""
    assert a.ats_overrides["contact_phone"] == "+1-415-555-0100"
    assert a.ats_overrides["contact_email"] is None
    assert not a.in_notes


def test_csv_only() -> None:
    a = _assignment()
    mutators.apply_csv_only(a)
    assert a.in_csv and not a.in_ats and not a.in_notes


def test_ats_notes_only() -> None:
    a = _assignment()
    mutators.apply_ats_notes_only(a)
    assert not a.in_csv and a.in_ats and a.in_notes


def test_notes_only() -> None:
    a = _assignment()
    mutators.apply_notes_only(a)
    assert not a.in_csv and not a.in_ats and a.in_notes


def test_glitch_email_invalidates_ats_email() -> None:
    a = _assignment()
    mutators.apply_glitch_email(a)
    assert a.ats_overrides["contact_email"] == "not-an-email"
    assert not a.in_csv


def test_github_text_only_suppresses_ats_github() -> None:
    rng = random.Random(0)
    a = _assignment(github_handle=None)
    mutators.apply_github_text_only(a, rng)
    assert a.suppress_ats_github
    assert a.embed_github_in_notes
    assert a.notes_overrides.get("github_handle")


def test_github_404_sets_fake_handle() -> None:
    a = _assignment()
    mutators.apply_github_404(a)
    assert "nonexistent-handle" in a.notes_overrides["github_handle"]
    assert a.persona.github_is_real is False


def test_csv_duplicate_adds_extra_row() -> None:
    a = _assignment()
    mutators.apply_csv_duplicate(a)
    assert a.csv_row_extra == 1
