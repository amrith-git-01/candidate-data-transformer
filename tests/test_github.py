import os

import pytest

from src.adapters.github_adapter import fetch_github_record


@pytest.mark.github
def test_fetch_torvalds_live():
    if not os.environ.get("GITHUB_TOKEN"):
        pytest.skip("GITHUB_TOKEN not set")
    rec = fetch_github_record("torvalds")
    assert rec is not None
    assert rec.source == "github"


def test_fetch_nonexistent_returns_none():
    rec = fetch_github_record("jane-doe-nonexistent-handle-12345")
    assert rec is None
