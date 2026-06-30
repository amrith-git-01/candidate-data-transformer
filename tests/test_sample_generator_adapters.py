"""Generated files parse cleanly with pipeline adapters."""

from __future__ import annotations

from pathlib import Path

import pytest

from sample_generator.orchestrator import generate
from src.adapters.ats_adapter import parse_ats
from src.adapters.csv_adapter import parse_csv
from src.adapters.notes_adapter import parse_notes


@pytest.fixture
def generated_dir(tmp_path: Path) -> Path:
    out = tmp_path / "samples"
    generate(count=100, seed=7, out_dir=out)
    return out


def test_csv_parses_with_records(generated_dir: Path) -> None:
    records = parse_csv(generated_dir / "recruiter_export.csv")
    assert len(records) >= 10
    assert all(r.fields.get("full_name") for r in records)


def test_ats_parses_with_records(generated_dir: Path) -> None:
    records = parse_ats(generated_dir / "ats_export.json")
    assert len(records) >= 10
    assert all(r.fields.get("full_name") for r in records)


def test_notes_parses_with_records(generated_dir: Path) -> None:
    records = parse_notes(generated_dir / "recruiter_notes.txt")
    assert len(records) >= 5
    assert all(r.fields.get("full_name") for r in records)
