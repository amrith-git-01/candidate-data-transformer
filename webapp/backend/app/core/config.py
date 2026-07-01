"""Shared filesystem paths. The webapp never mutates src/ or sample_generator/ —
it only reads/writes the same data files the CLI already uses."""

from __future__ import annotations

from pathlib import Path

# webapp/backend/app/core/config.py -> repo root is 4 levels up
PROJECT_ROOT = Path(__file__).resolve().parents[4]

SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"
CONFIGS_DIR = PROJECT_ROOT / "configs"
OUTPUT_DIR = PROJECT_ROOT / "output"

CSV_PATH = SAMPLE_DATA_DIR / "recruiter_export.csv"
ATS_PATH = SAMPLE_DATA_DIR / "ats_export.json"
NOTES_PATH = SAMPLE_DATA_DIR / "recruiter_notes.txt"

WEBAPP_RUN_PATH = OUTPUT_DIR / "webapp_run.json"
