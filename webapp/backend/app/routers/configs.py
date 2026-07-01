from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from app.core.config import CONFIGS_DIR

router = APIRouter(prefix="/api/configs", tags=["configs"])


@router.get("")
def list_configs() -> list[str]:
    if not CONFIGS_DIR.is_dir():
        return []
    return sorted(p.stem for p in CONFIGS_DIR.glob("*.json"))


@router.get("/{name}")
def get_config(name: str) -> dict:
    path = CONFIGS_DIR / f"{name}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Config not found: {name}")
    return json.loads(path.read_text(encoding="utf-8"))
