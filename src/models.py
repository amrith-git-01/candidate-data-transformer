"""
Stage boundary types for the candidate transformer pipeline.

Design rules:
- Adapters emit RawRecord (source-specific parsing stops here).
- Match emits CandidateGroup (identity resolution boundary).
- Merge emits CanonicalRecord (single source of truth before projection).
- Projector reads ProjectionConfig (output shape is config-driven).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict

SourceType = Literal["csv", "ats", "recruiter_notes", "github"]
FieldMethod = Literal["direct", "extracted", "inferred"]
MatchTier = Literal["email", "phone", "name"]

class FieldValue(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: Any
    method: FieldMethod

class RawRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: SourceType
    fields: dict[str, FieldValue]

class CandidateGroup(BaseModel):
    records: list[RawRecord]
    matched_by: MatchTier

class Location(BaseModel):
    city: str | None = None
    region: str | None = None
    country: str | None = None

class LinkSet(BaseModel):
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    other: list[str] = Field(default_factory=list)

class SkillEntry(BaseModel):
    name: str
    confidence: float
    sources: list[str]

class ExperienceEntry(BaseModel):
    company: str
    title: str
    start: str | None = None
    end: str | None = None
    summary: str | None = None

class EducationEntry(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    end_year: int | None = None

class ProvenanceEntry(BaseModel):
    field: str
    source: str
    method: str

class CanonicalRecord(BaseModel):
    candidate_id: str
    full_name: str
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    location: Location = Field(default_factory=Location)
    links: LinkSet = Field(default_factory=LinkSet)
    headline: str | None = None
    years_experience: int | None = None
    skills: list[SkillEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    provenance: list[ProvenanceEntry] = Field(default_factory=list)
    overall_confidence: float = 0.0
    matched_by: MatchTier = "email"

class FieldSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    path: str
    from_: str | None = Field(None, alias="from")
    type: Literal["string", "string[]", "number", "object", "null"]
    required: bool = False
    normalize: Literal["E164", "canonical"] | None = None

class ProjectionConfig(BaseModel):
    use_canonical_schema: bool = False
    fields: list[FieldSpec] = Field(default_factory=list)
    include_confidence: bool = True
    include_provenance: bool = True
    on_missing: Literal["null", "omit", "error"] = "null"

class PipelineResult(BaseModel):
    profiles: list[dict[str, Any]]