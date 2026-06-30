import pytest

from src.models import (
    CanonicalRecord,
    CandidateGroup,
    FieldSpec,
    FieldValue,
    PipelineResult,
    ProjectionConfig,
    RawRecord,
)


def test_raw_record_is_immutable():
    rec = RawRecord(
        source="csv",
        fields={"full_name": FieldValue(value="Linus Torvalds", method="direct")},
    )
    with pytest.raises(Exception):
        rec.source = "ats"  # frozen model


def test_projection_config_parses_from_alias():
    cfg = ProjectionConfig.model_validate({
        "fields": [
            {"path": "primary_email", "from": "emails[0]", "type": "string", "required": True},
        ],
        "include_provenance": False,
        "on_missing": "omit",
    })
    assert cfg.fields[0].from_ == "emails[0]"
    assert cfg.on_missing == "omit"


def test_candidate_group_holds_multiple_sources():
    group = CandidateGroup(
        matched_by="email",
        records=[
            RawRecord(source="csv", fields={}),
            RawRecord(source="ats", fields={}),
        ],
    )
    assert len(group.records) == 2


def test_pipeline_result_envelope():
    result = PipelineResult(profiles=[{"full_name": "Test"}])
    dumped = result.model_dump()
    assert "profiles" in dumped
    assert dumped["profiles"][0]["full_name"] == "Test"


def test_canonical_record_defaults_are_safe():
    rec = CanonicalRecord(candidate_id="x", full_name="X")
    assert rec.emails == []
    assert rec.skills == []
    assert rec.overall_confidence == 0.0