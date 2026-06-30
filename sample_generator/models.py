"""Data models for sample data generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Persona:
    person_id: str
    full_name: str
    email: str | None
    phone: str | None
    company: str
    title: str
    city: str | None
    region: str | None
    country: str | None
    linkedin_url: str | None
    github_handle: str | None
    github_is_real: bool = False
    headline: str | None = None
    years_experience: int | None = None
    skills: list[str] = field(default_factory=list)
    education: list[dict[str, Any]] = field(default_factory=list)
    notes_template: str | None = None


@dataclass
class SourceAssignment:
    persona: Persona
    scenario_tags: list[str] = field(default_factory=list)
    in_csv: bool = True
    in_ats: bool = True
    in_notes: bool = True
    csv_row_extra: int = 0
    csv_overrides: dict[str, Any] = field(default_factory=dict)
    ats_overrides: dict[str, Any] = field(default_factory=dict)
    notes_overrides: dict[str, Any] = field(default_factory=dict)
    suppress_ats_github: bool = False
    embed_github_in_notes: bool = False


@dataclass
class GenerationManifest:
    seed: int
    count: int
    generated_at: str
    scenario_histogram: dict[str, int]
    source_counts: dict[str, int]
    github_stats: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "count": self.count,
            "generated_at": self.generated_at,
            "scenario_histogram": self.scenario_histogram,
            "source_counts": self.source_counts,
            "github_stats": self.github_stats,
        }
