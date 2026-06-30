"""Orchestrate the full candidate transformer pipeline."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.env import load_project_env
from src.adapters.ats_adapter import parse_ats
from src.adapters.csv_adapter import parse_csv
from src.adapters.github_adapter import fetch_github_record
from src.adapters.link_detector import find_github_from_fields
from src.adapters.notes_adapter import parse_notes
from src.match.identity import group_records
from src.merge.survivorship import merge_group
from src.models import CandidateGroup, PipelineResult, ProjectionConfig
from src.project.projector import project_record
from src.validate.validator import ValidationError, validate_output

logger = logging.getLogger(__name__)

_CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"
DEFAULT_CONFIG_PATH = _CONFIGS_DIR / "default.json"


def default_config_path() -> Path:
    return DEFAULT_CONFIG_PATH


def load_config(path: str | Path | None = None) -> ProjectionConfig:
    resolved = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not resolved.is_file():
        raise FileNotFoundError(f"Config file not found: {resolved}")
    data = json.loads(resolved.read_text(encoding="utf-8"))
    return ProjectionConfig.model_validate(data)


def _parse_sources(
    csv_path: str | Path | None,
    ats_path: str | Path | None,
    notes_path: str | Path | None,
) -> list:
    from src.models import RawRecord

    records: list[RawRecord] = []
    if csv_path:
        records.extend(parse_csv(csv_path))
    if ats_path:
        records.extend(parse_ats(ats_path))
    if notes_path:
        records.extend(parse_notes(notes_path))
    if not records:
        raise ValueError("At least one source file must be provided")
    return records


def _github_handle_for_group(group: CandidateGroup) -> str | None:
    for rec in group.records:
        if handle := find_github_from_fields(rec.fields):
            return handle
    return None


def _enrich_group_with_github(group: CandidateGroup, enrich_github: bool) -> CandidateGroup:
    if not enrich_github:
        return group
    handle = _github_handle_for_group(group)
    if not handle:
        return group
    gh_record = fetch_github_record(handle)
    if gh_record is None:
        return group
    return CandidateGroup(
        records=[*group.records, gh_record],
        matched_by=group.matched_by,
    )


def run_pipeline(
    csv_path: str | Path | None = None,
    ats_path: str | Path | None = None,
    notes_path: str | Path | None = None,
    config: ProjectionConfig | None = None,
    enrich_github: bool = True,
) -> dict[str, Any]:
    if config is None:
        config = load_config()
    records = _parse_sources(csv_path, ats_path, notes_path)
    groups = group_records(records)

    profiles: list[dict[str, Any]] = []
    for group in groups:
        enriched = _enrich_group_with_github(group, enrich_github=enrich_github)
        canonical = merge_group(enriched)
        projected = project_record(canonical, config)
        try:
            validated = validate_output(projected, config)
        except ValidationError as exc:
            if config and config.on_missing == "error":
                logger.error("Validation failed for %s: %s", canonical.full_name, exc)
                raise
            logger.warning(
                "Skipping profile %s — does not match requested config: %s",
                canonical.full_name,
                exc,
            )
            continue
        profiles.append(validated)

    profiles.sort(key=lambda p: (p.get("full_name") or p.get("name") or "").lower())
    return PipelineResult(profiles=profiles).model_dump()


def run_pipeline_from_paths(
    csv_path: str | Path | None = None,
    ats_path: str | Path | None = None,
    notes_path: str | Path | None = None,
    config_path: str | Path | None = None,
    enrich_github: bool = True,
) -> dict[str, Any]:
    load_project_env()
    config = load_config(config_path)
    return run_pipeline(
        csv_path=csv_path,
        ats_path=ats_path,
        notes_path=notes_path,
        config=config,
        enrich_github=enrich_github,
    )
