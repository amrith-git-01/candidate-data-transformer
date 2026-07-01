from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class GenerateSampleRequest(BaseModel):
    count: int = 500
    seed: int = 42


class PaginatedRows(BaseModel):
    rows: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


SourceName = Literal["csv", "ats", "notes"]
