"""Find GitHub handles in URLs or free text."""

import re

GITHUB_RE = re.compile(
    r"(?:https?://)?github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))",
    re.IGNORECASE,
)


def find_github_handle(text: str) -> str | None:
    if not text:
        return None
    match = GITHUB_RE.search(text)
    return match.group(1) if match else None


def find_github_from_fields(fields: dict) -> str | None:
    """Priority: explicit github_url field, then scan all string values."""
    url_field = fields.get("github_url")
    if url_field is not None and url_field.value:
        handle = find_github_handle(str(url_field.value))
        if handle:
            return handle
    for fv in fields.values():
        if fv.value is not None and isinstance(fv.value, str):
            handle = find_github_handle(fv.value)
            if handle:
                return handle
    return None