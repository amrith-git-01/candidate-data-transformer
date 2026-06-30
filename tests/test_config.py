import json
from pathlib import Path

from src.pipeline import default_config_path, load_config, run_pipeline


def test_default_config_path_exists():
    path = default_config_path()
    assert path.is_file()
    cfg = load_config()
    assert cfg.use_canonical_schema is True


def test_pipeline_uses_default_config_when_none(sample_csv, sample_ats, sample_notes):
    cfg = load_config()
    result = run_pipeline(
        csv_path=sample_csv,
        ats_path=sample_ats,
        notes_path=sample_notes,
        config=cfg,
        enrich_github=False,
    )
    assert result["profiles"][0]["full_name"]
    assert "provenance" in result["profiles"][0]


def test_load_config_explicit_custom():
    path = Path(__file__).resolve().parents[1] / "configs" / "custom.json"
    cfg = load_config(path)
    assert cfg.use_canonical_schema is False
    assert len(cfg.fields) >= 15
    paths = {f.path for f in cfg.fields}
    assert {"name", "primary_email", "skill_names", "companies", "schools"} <= paths
