"""Sample-data generation + raw preview parsing.

Preview parsing here is deliberately separate from src/adapters/* — those
adapters return RawRecord objects tuned for pipeline consumption, not
display. Keeping a lightweight display-only parser here means a preview bug
can never affect real pipeline correctness, and vice versa.
"""

from __future__ import annotations

import csv
import json
import re
from typing import Any

from sample_generator.orchestrator import generate as generate_samples

from app.core.config import ATS_PATH, CSV_PATH, NOTES_PATH, SAMPLE_DATA_DIR

_SECTION_RE = re.compile(r"^=== Candidate:\s*(.+?)\s*===$", re.MULTILINE)


def generate_sample_data(count: int, seed: int) -> dict[str, Any]:
    manifest = generate_samples(count=count, seed=seed, out_dir=SAMPLE_DATA_DIR)
    return manifest.to_dict()


def _paginate(rows: list[dict[str, Any]], page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    total = len(rows)
    page = max(page, 1)
    page_size = max(1, min(page_size, 200))
    start = (page - 1) * page_size
    return rows[start : start + page_size], total


def _read_csv_rows() -> list[dict[str, Any]]:
    if not CSV_PATH.is_file():
        return []
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_ats_rows() -> list[dict[str, Any]]:
    if not ATS_PATH.is_file():
        return []
    try:
        data = json.loads(ATS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return list(data.get("candidates", []))


def _read_notes_rows() -> list[dict[str, Any]]:
    if not NOTES_PATH.is_file():
        return []
    text = NOTES_PATH.read_text(encoding="utf-8")
    matches = list(_SECTION_RE.finditer(text))
    rows: list[dict[str, Any]] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        rows.append({"candidate": m.group(1), "notes": body})
    return rows


_READERS = {
    "csv": _read_csv_rows,
    "ats": _read_ats_rows,
    "notes": _read_notes_rows,
}


def read_source_page(source: str, page: int, page_size: int) -> dict[str, Any]:
    reader = _READERS.get(source)
    if reader is None:
        raise ValueError(f"Unknown source: {source}")
    rows = reader()
    page_rows, total = _paginate(rows, page, page_size)
    return {"rows": page_rows, "total": total, "page": page, "page_size": page_size}
