"""Validate projected output against requested config shape."""

from __future__ import annotations

from typing import Any

from src.models import ProjectionConfig


class ValidationError(Exception):
    pass


def validate_output(
    output: dict[str, Any],
    config: ProjectionConfig | None,
) -> dict[str, Any]:
    if config is None or config.use_canonical_schema:
        for key in ("candidate_id", "full_name"):
            if not output.get(key):
                raise ValidationError(f"Required canonical field missing: {key}")
        return output

    if not config.fields:
        return output

    for spec in config.fields:
        present = spec.path in output
        value = output.get(spec.path)

        if spec.required and (not present or value is None):
            raise ValidationError(f"Required field missing or null: {spec.path}")

        if not present or value is None:
            continue

        _check_type(spec.path, value, spec.type)

    return output


def _check_type(path: str, value: Any, expected: str) -> None:
    ok = (
        (expected == "string" and isinstance(value, str))
        or (
            expected == "string[]"
            and isinstance(value, list)
            and all(isinstance(v, str) for v in value)
        )
        or (
            expected == "number"
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        )
        or (expected == "object" and isinstance(value, dict))
        or (expected == "null" and value is None)
    )
    if not ok:
        raise ValidationError(
            f"Type mismatch for {path}: expected {expected}, got {type(value).__name__}"
        )
