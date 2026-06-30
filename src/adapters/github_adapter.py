"""Fetch GitHub profile + repo languages. Soft-fail on error."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from src.env import load_project_env
from src.models import FieldValue, RawRecord
from src.normalize.skills import canonicalize_skill

logger = logging.getLogger(__name__)

API_BASE = "https://api.github.com"


def fetch_github_record(handle: str, token: str | None = None) -> RawRecord | None:
    load_project_env()
    token = token or os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with httpx.Client(timeout=15.0, headers=headers) as client:
            user_resp = client.get(f"{API_BASE}/users/{handle}")
            if user_resp.status_code == 404:
                logger.warning("GitHub user not found: %s", handle)
                return None
            user_resp.raise_for_status()
            user: dict[str, Any] = user_resp.json()

            repos_resp = client.get(
                f"{API_BASE}/users/{handle}/repos",
                params={"per_page": 10, "sort": "updated"},
            )
            repos_resp.raise_for_status()
            repos: list[dict[str, Any]] = repos_resp.json()
    except httpx.HTTPError as exc:
        logger.warning("GitHub API error for %s: %s", handle, exc)
        return None

    fields: dict[str, FieldValue] = {}

    if name := user.get("name"):
        fields["full_name"] = FieldValue(value=name, method="direct")
    if bio := user.get("bio"):
        fields["headline"] = FieldValue(value=bio, method="direct")
    if url := user.get("html_url"):
        fields["github_url"] = FieldValue(value=url, method="direct")
    if email := user.get("email"):
        fields["email"] = FieldValue(value=email, method="direct")
    if location := user.get("location"):
        fields["city"] = FieldValue(value=location, method="inferred")

    languages: set[str] = set()
    for repo in repos:
        lang = repo.get("language")
        if lang:
            languages.add(canonicalize_skill(lang))

    for lang in sorted(languages):
        fields[f"skill_{lang}"] = FieldValue(value=lang, method="inferred")

    if not fields:
        return None

    return RawRecord(source="github", fields=fields)
