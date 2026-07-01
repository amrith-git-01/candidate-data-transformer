from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.run import RunRequest
from app.services import pipeline_service
from app.services.pipeline_service import ConfigValidationError

router = APIRouter(prefix="/api/run", tags=["run"])


@router.post("")
def run(payload: RunRequest) -> dict:
    try:
        return pipeline_service.run_and_persist(payload.config, payload.enrich_github)
    except ConfigValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/results")
def results(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> dict:
    return pipeline_service.read_latest_run(page, page_size)
