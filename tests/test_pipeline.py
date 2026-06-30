import json
from pathlib import Path

from src.adapters.ats_adapter import parse_ats
from src.adapters.csv_adapter import parse_csv
from src.adapters.notes_adapter import parse_notes
from src.match.identity import group_records
from src.merge.survivorship import merge_group
from src.models import ProjectionConfig
from src.pipeline import run_pipeline


def test_pipeline_produces_profiles_without_github(sample_csv, sample_ats, sample_notes):
    result = run_pipeline(
        csv_path=sample_csv,
        ats_path=sample_ats,
        notes_path=sample_notes,
        enrich_github=False,
    )
    assert "profiles" in result
    assert len(result["profiles"]) >= 490
    for profile in result["profiles"]:
        assert profile.get("full_name")


def test_title_survivorship_in_pipeline(sample_csv, sample_ats, sample_notes):
    result = run_pipeline(
        csv_path=sample_csv,
        ats_path=sample_ats,
        notes_path=sample_notes,
        enrich_github=False,
    )
    with_experience = [
        p for p in result["profiles"]
        if p.get("experience") and p["experience"][0].get("title")
    ]
    assert len(with_experience) >= 100
    sample = with_experience[0]
    assert sample["experience"][0]["company"]


def test_singleton_without_email_uses_name_tier(sample_csv, sample_ats, sample_notes):
    result = run_pipeline(
        csv_path=sample_csv,
        ats_path=sample_ats,
        notes_path=sample_notes,
        enrich_github=False,
    )
    name_tier = [p for p in result["profiles"] if p.get("matched_by") == "name"]
    # Notes-only / no-email singletons — not cross-source name joins
    assert len(name_tier) >= 1
    assert all(len(p.get("emails") or []) == 0 for p in name_tier)


def test_custom_config_projection(sample_csv, sample_ats, sample_notes):
    cfg_path = Path(__file__).resolve().parents[1] / "configs" / "custom.json"
    config = ProjectionConfig.model_validate(json.loads(cfg_path.read_text(encoding="utf-8")))
    result = run_pipeline(
        csv_path=sample_csv,
        ats_path=sample_ats,
        notes_path=sample_notes,
        config=config,
        enrich_github=False,
    )
    assert len(result["profiles"]) >= 400
    profile = result["profiles"][0]
    assert "name" in profile
    assert "primary_email" in profile
    assert "full_name" not in profile
    assert "provenance" in profile
    prov_fields = {e["field"] for e in profile["provenance"]}
    assert "emails[0]" in prov_fields
    assert "education[0].institution" in prov_fields or "experience[0].company" in prov_fields


def test_end_to_end_record_counts(sample_csv, sample_ats, sample_notes):
    records = (
        parse_csv(sample_csv)
        + parse_ats(sample_ats)
        + parse_notes(sample_notes)
    )
    groups = group_records(records)
    assert len(groups) >= 490
    merged = [merge_group(g) for g in groups]
    assert all(m.full_name for m in merged)
