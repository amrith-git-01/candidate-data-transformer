"""Deterministic output for fixed seed."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from sample_generator.orchestrator import generate

OUTPUT_FILES = (
    "recruiter_export.csv",
    "ats_export.json",
    "recruiter_notes.txt",
    "manifest.json",
)


def _dir_fingerprint(out_dir: Path) -> str:
    h = hashlib.sha256()
    for name in OUTPUT_FILES:
        h.update(name.encode())
        h.update((out_dir / name).read_bytes())
    return h.hexdigest()


@pytest.fixture
def generated_dir(tmp_path: Path) -> Path:
    out = tmp_path / "samples"
    generate(count=50, seed=1, out_dir=out)
    return out


def test_same_seed_produces_identical_output(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    generate(count=50, seed=99, out_dir=a)
    generate(count=50, seed=99, out_dir=b)
    assert _dir_fingerprint(a) == _dir_fingerprint(b)


def test_different_seed_produces_different_output(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    generate(count=50, seed=1, out_dir=a)
    generate(count=50, seed=2, out_dir=b)
    assert _dir_fingerprint(a) != _dir_fingerprint(b)


def test_manifest_matches_generation_params(generated_dir: Path) -> None:
    import json

    manifest = json.loads((generated_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == 1
    assert manifest["count"] == 50
    assert manifest["source_counts"]["csv_rows"] >= 1
    assert manifest["source_counts"]["ats_candidates"] >= 1
    assert manifest["source_counts"]["notes_sections"] >= 1
    assert sum(manifest["github_stats"].values()) == 50
