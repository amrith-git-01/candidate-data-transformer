import pytest

from src.models import (
    CanonicalRecord,
    EducationEntry,
    ExperienceEntry,
    FieldSpec,
    LinkSet,
    Location,
    ProjectionConfig,
    SkillEntry,
)
from src.project.paths import resolve_path
from src.project.projector import project_record
from src.validate.validator import ValidationError, validate_output


def _sample_canonical() -> CanonicalRecord:
    return CanonicalRecord(
        candidate_id="dan-abramov-at-example-com",
        full_name="Dan Abramov",
        emails=["dan.abramov@example.com"],
        phones=["+14155550102"],
        location=Location(city="San Francisco", region="California", country="US"),
        links=LinkSet(github="https://github.com/gaearon"),
        skills=[
            SkillEntry(name="javascript", confidence=0.9, sources=["recruiter_notes"]),
            SkillEntry(name="react", confidence=0.85, sources=["recruiter_notes"]),
        ],
        overall_confidence=0.88,
        matched_by="email",
    )


def test_resolve_path_scalar_index_array_and_nested():
    data = {
        "full_name": "Dan",
        "emails": ["a@x.com", "b@x.com"],
        "skills": [{"name": "go"}, {"name": "rust"}],
        "links": {"github": "https://github.com/x"},
        "location": {"country": "US"},
    }
    assert resolve_path(data, "full_name") == "Dan"
    assert resolve_path(data, "emails[0]") == "a@x.com"
    assert resolve_path(data, "skills[].name") == ["go", "rust"]
    assert resolve_path(data, "links.github") == "https://github.com/x"
    assert resolve_path(data, "location.country") == "US"
    assert resolve_path(data, "emails[9]") is None


def test_default_projection_returns_full_canonical():
    cfg = ProjectionConfig.model_validate({
        "use_canonical_schema": True,
        "include_confidence": True,
        "include_provenance": True,
    })
    out = project_record(_sample_canonical(), config=cfg)
    assert out["full_name"] == "Dan Abramov"
    assert out["location"]["country"] == "US"
    assert "provenance" in out


def test_default_config_file_loads():
    from pathlib import Path
    import json

    path = Path(__file__).resolve().parents[1] / "configs" / "default.json"
    cfg = ProjectionConfig.model_validate(json.loads(path.read_text(encoding="utf-8")))
    assert cfg.use_canonical_schema is True
    assert cfg.include_provenance is True


def test_custom_config_reshapes_output():
    cfg = ProjectionConfig.model_validate({
        "fields": [
            {"path": "name", "from": "full_name", "type": "string", "required": True},
            {"path": "primary_email", "from": "emails[0]", "type": "string", "required": True},
            {"path": "country", "from": "location.country", "type": "string"},
            {"path": "skill_names", "from": "skills[].name", "type": "string[]"},
        ],
        "include_provenance": False,
        "on_missing": "omit",
    })
    out = project_record(_sample_canonical(), cfg)
    assert out["name"] == "Dan Abramov"
    assert out["country"] == "US"
    assert out["skill_names"] == ["javascript", "react"]
    assert "provenance" not in out


def test_comprehensive_custom_config_file():
    from pathlib import Path
    import json

    path = Path(__file__).resolve().parents[1] / "configs" / "custom.json"
    cfg = ProjectionConfig.model_validate(json.loads(path.read_text(encoding="utf-8")))
    canonical = _sample_canonical()
    canonical = canonical.model_copy(update={
        "experience": [
            ExperienceEntry(company="Meta", title="Engineer"),
        ],
        "education": [
            EducationEntry(institution="MIT", degree="BS", field="CS", end_year=2010),
        ],
    })
    out = project_record(canonical, cfg)
    assert out["name"] == "Dan Abramov"
    assert out["companies"] == ["Meta"]
    assert out["schools"] == ["MIT"]
    assert "provenance" in out


def test_on_missing_omit_skips_empty_phone():
    cfg = ProjectionConfig(
        fields=[
            FieldSpec(path="name", from_="full_name", type="string", required=True),
            FieldSpec(path="phone", from_="phones[0]", type="string"),
        ],
        on_missing="omit",
    )
    canonical = CanonicalRecord(candidate_id="x", full_name="Solo", phones=[])
    out = project_record(canonical, cfg)
    assert "phone" not in out


def test_validate_required_field_raises():
    cfg = ProjectionConfig(
        fields=[FieldSpec(path="primary_email", type="string", required=True)],
        on_missing="error",
    )
    with pytest.raises(ValidationError):
        validate_output({}, cfg)


def test_validate_passes_typed_output():
    cfg = ProjectionConfig(
        fields=[
            FieldSpec(path="name", type="string", required=True),
            FieldSpec(path="skill_names", type="string[]"),
        ],
    )
    out = {"name": "Dan", "skill_names": ["javascript"]}
    assert validate_output(out, cfg) == out
