import os
from pathlib import Path

import pytest

from src.env import load_project_env

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "sample_data"
CURATED_DIR = Path(__file__).resolve().parent / "fixtures" / "curated"


def pytest_configure(config):
    load_project_env()
    config.addinivalue_line("markers", "github: live GitHub API tests")


@pytest.fixture
def sample_csv() -> str:
    return str(SAMPLE_DIR / "recruiter_export.csv")


@pytest.fixture
def sample_ats() -> str:
    return str(SAMPLE_DIR / "ats_export.json")


@pytest.fixture
def sample_notes() -> str:
    return str(SAMPLE_DIR / "recruiter_notes.txt")


@pytest.fixture
def curated_csv() -> str:
    return str(CURATED_DIR / "recruiter_export.csv")


@pytest.fixture
def curated_ats() -> str:
    return str(CURATED_DIR / "ats_export.json")


@pytest.fixture
def curated_notes() -> str:
    return str(CURATED_DIR / "recruiter_notes.txt")