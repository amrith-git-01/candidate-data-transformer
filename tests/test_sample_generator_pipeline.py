"""Pipeline smoke test on generated sample data."""

from __future__ import annotations

from pathlib import Path

import pytest

from sample_generator.orchestrator import generate
from src.pipeline import run_pipeline


@pytest.fixture
def generated_dir(tmp_path: Path) -> Path:
    out = tmp_path / "samples"
    generate(count=100, seed=3, out_dir=out)
    return out


def test_pipeline_runs_on_generated_data(generated_dir: Path) -> None:
    result = run_pipeline(
        csv_path=str(generated_dir / "recruiter_export.csv"),
        ats_path=str(generated_dir / "ats_export.json"),
        notes_path=str(generated_dir / "recruiter_notes.txt"),
        enrich_github=False,
    )
    assert "profiles" in result
    assert len(result["profiles"]) >= 5
    for profile in result["profiles"]:
        assert profile.get("full_name")
