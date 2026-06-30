"""Resolve JSONPath-like expressions against a canonical dict."""

from __future__ import annotations

import re
from typing import Any

_INDEX_RE = re.compile(r"^([^\[]+)(?:\[(\d+)\])?$")
_ARRAY_RE = re.compile(r"^([^\[]+)\[\]\.(.+)$")


def resolve_path(data: dict[str, Any], path: str) -> Any:
    if not path:
        return None

    if "." in path and "[" not in path:
        current: Any = data
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    if m := _ARRAY_RE.match(path):
        array_key, subfield = m.group(1), m.group(2)
        items = data.get(array_key)
        if not isinstance(items, list):
            return None
        out: list[Any] = []
        for item in items:
            if isinstance(item, dict) and subfield in item:
                out.append(item[subfield])
        return out

    if m := _INDEX_RE.match(path):
        key, idx = m.group(1), m.group(2)
        if key not in data:
            return None
        val = data[key]
        if idx is None:
            return val
        if not isinstance(val, list):
            return None
        i = int(idx)
        return val[i] if 0 <= i < len(val) else None

    return data.get(path)
