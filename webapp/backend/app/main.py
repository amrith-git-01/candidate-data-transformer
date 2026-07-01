from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import configs, run, sample

app = FastAPI(title="Candidate Data Transformer — Web UI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sample.router)
app.include_router(configs.router)
app.include_router(run.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
