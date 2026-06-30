"""Email normalization. Invalid format -> None."""

import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def normalize_email(raw: str | None) -> str | None:
    if raw is None:
        return None
    email = str(raw).strip().lower()
    if not email:
        return None
    if not _EMAIL_RE.match(email):
        return None
    return email