"""Config-driven projection from CanonicalRecord to output dict."""

from __future__ import annotations

from typing import Any

from src.models import CanonicalRecord, ProjectionConfig
from src.normalize.phones import normalize_phone
from src.normalize.skills import canonicalize_skill
from src.project.paths import resolve_path


def project_record(
    canonical: CanonicalRecord,
    config: ProjectionConfig | None = None,
) -> dict[str, Any]:
    if config is None or config.use_canonical_schema or not config.fields:
        return canonical.model_dump()

    data = canonical.model_dump()
    out: dict[str, Any] = {}

    for spec in config.fields:
        source_path = spec.from_ or spec.path
        value = resolve_path(data, source_path)

        if value is None or value == "" or value == []:
            if spec.required and config.on_missing == "error":
                raise ValueError(f"Required field missing: {spec.path}")
            if config.on_missing == "omit":
                continue
            value = None

        if spec.type == "string[]" and isinstance(value, list):
            value = [str(v) for v in value if v is not None and str(v).strip() != ""]
            if not value:
                if spec.required and config.on_missing == "error":
                    raise ValueError(f"Required field missing: {spec.path}")
                if config.on_missing == "omit":
                    continue
                value = None

        if value is not None and spec.normalize:
            value = _apply_normalize(value, spec.normalize)

        out[spec.path] = value

    if config.include_confidence:
        out["overall_confidence"] = canonical.overall_confidence
    if config.include_provenance:
        out["provenance"] = [p.model_dump() for p in canonical.provenance]

    return out


def _apply_normalize(value: Any, mode: str) -> Any:
    if mode == "E164":
        if isinstance(value, str):
            return normalize_phone(value)
        return value
    if mode == "canonical":
        if isinstance(value, list):
            return [canonicalize_skill(str(v)) for v in value]
        if isinstance(value, str):
            return canonicalize_skill(value)
    return value
