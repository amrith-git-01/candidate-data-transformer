"""Thin wrapper around src.pipeline — the webapp never re-implements pipeline
logic, it only calls the same functions the CLI calls."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from src.env import load_project_env
from src.models import ProjectionConfig
from src.pipeline import run_pipeline

from app.core.config import ATS_PATH, CSV_PATH, NOTES_PATH, WEBAPP_RUN_PATH

load_project_env()


class ConfigValidationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def run_and_persist(config_dict: dict[str, Any], enrich_github: bool) -> dict[str, Any]:
    try:
        config = ProjectionConfig.model_validate(config_dict) if config_dict else None
    except ValidationError as exc:
        raise ConfigValidationError(str(exc)) from exc

    result = run_pipeline(
        csv_path=CSV_PATH,
        ats_path=ATS_PATH,
        notes_path=NOTES_PATH,
        config=config,
        enrich_github=enrich_github,
    )

    WEBAPP_RUN_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEBAPP_RUN_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {"profile_count": len(result["profiles"]), "wrote_to": str(WEBAPP_RUN_PATH)}


def read_latest_run(page: int, page_size: int) -> dict[str, Any]:
    if not WEBAPP_RUN_PATH.is_file():
        return {"profiles": [], "total": 0, "page": page, "page_size": page_size}

    data = json.loads(WEBAPP_RUN_PATH.read_text(encoding="utf-8"))
    profiles = data.get("profiles", [])

    page = max(page, 1)
    page_size = max(1, min(page_size, 200))
    start = (page - 1) * page_size
    page_profiles = profiles[start : start + page_size]

    return {
        "profiles": page_profiles,
        "total": len(profiles),
        "page": page,
        "page_size": page_size,
    }
