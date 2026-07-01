from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)
    enrich_github: bool = False


class RunResponse(BaseModel):
    profile_count: int
    wrote_to: str


class PaginatedProfiles(BaseModel):
    profiles: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
