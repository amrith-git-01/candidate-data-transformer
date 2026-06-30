"""Name normalization for identity matching. No fuzzy logic."""

def normalize_name(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = " ".join(str(raw).strip().split())
    if not text:
        return None
    return " ".join(part.capitalize() for part in text.split(" "))