import json
import logging
from pathlib import Path

from src.models import FieldValue, RawRecord
from src.normalize.emails import normalize_email

logger = logging.getLogger(__name__)

ATS_MAP = {
    "candidate_name": "full_name",
    "contact_email": "email",
    "contact_phone": "phone",
    "employer": "current_company",
    "job_title": "current_title",
    "github_url": "github_url",
    "linkedin_url": "linkedin_url",
    "headline": "headline",
}


def parse_ats(path: str | Path) -> list[RawRecord]:
    path = Path(path)
    if not path.is_file():
        logger.error("ATS file not found: %s", path)
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed to parse ATS file %s: %s", path, exc)
        return []

    records: list[RawRecord] = []
    for entry in data.get("candidates", []):
        name = entry.get("candidate_name")
        if not name or not str(name).strip():
            logger.warning("Skipping ATS entry with no name: %s", entry)
            continue

        email_raw = entry.get("contact_email")
        if email_raw is not None and str(email_raw).strip():
            if normalize_email(str(email_raw)) is None:
                logger.warning(
                    "Skipping ATS entry with invalid email: %s",
                    entry.get("candidate_name"),
                )
                continue

        fields: dict[str, FieldValue] = {}
        for src, dst in ATS_MAP.items():
            val = entry.get(src)
            if val is not None and str(val).strip():
                fields[dst] = FieldValue(
                    value=val.strip() if isinstance(val, str) else val,
                    method="direct",
                )

        loc = entry.get("location")
        if isinstance(loc, dict):
            for part, dst in (
                ("city", "city"),
                ("region", "region"),
                ("country", "country"),
            ):
                val = loc.get(part)
                if val is not None and str(val).strip():
                    fields[dst] = FieldValue(value=str(val).strip(), method="direct")

        education = entry.get("education")
        if isinstance(education, list) and education:
            fields["education"] = FieldValue(value=education, method="direct")

        if "full_name" not in fields:
            continue

        records.append(RawRecord(source="ats", fields=fields))

    return records
