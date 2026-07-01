from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.sample import GenerateSampleRequest
from app.services import sample_service

router = APIRouter(prefix="/api/sample", tags=["sample"])


@router.post("/generate")
def generate_sample(payload: GenerateSampleRequest) -> dict:
    if payload.count < 1 or payload.count > 5000:
        raise HTTPException(status_code=400, detail="count must be between 1 and 5000")
    return sample_service.generate_sample_data(count=payload.count, seed=payload.seed)


@router.get("/{source}")
def get_source_page(
    source: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> dict:
    try:
        return sample_service.read_source_page(source, page, page_size)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
