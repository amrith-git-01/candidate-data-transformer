import csv
import logging
from pathlib import Path

from src.models import FieldValue, RawRecord

logger = logging.getLogger(__name__)

COLUMN_MAP = {
    "name": "full_name",
    "email": "email",
    "phone": "phone",
    "current_company": "current_company",
    "title": "current_title",
    "city": "city",
    "region": "region",
    "country": "country",
    "linkedin_url": "linkedin_url",
}


def parse_csv(path: str | Path) -> list[RawRecord]:
    path = Path(path)
    if not path.is_file():
        logger.error("CSV file not found: %s", path)
        return []

    records: list[RawRecord] = []
    seen: set[tuple[str, ...]] = set()

    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not (row.get("name") or "").strip():
                    logger.warning("Skipping CSV row with no name: %s", row)
                    continue

                dedupe_key = tuple((row.get(k) or "").strip() for k in COLUMN_MAP)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                fields: dict[str, FieldValue] = {}
                for src_col, dst in COLUMN_MAP.items():
                    val = row.get(src_col)
                    if val is not None and str(val).strip():
                        fields[dst] = FieldValue(value=str(val).strip(), method="direct")

                records.append(RawRecord(source="csv", fields=fields))
    except OSError as exc:
        logger.error("Failed to read CSV %s: %s", path, exc)
        return []

    return records
