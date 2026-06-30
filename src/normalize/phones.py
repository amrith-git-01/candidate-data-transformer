"""E.164 phone normalization. Invalid input -> None (honestly empty)."""

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

def normalize_phone(raw: str | None, default_region: str = "US") -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        parsed = phonenumbers.parse(text, default_region)
    except NumberParseException:
        return None
    if not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)