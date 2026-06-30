# Candidate Data Transformer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full Eightfold multi-source candidate transformer — CLI in, `{ "profiles": [...] }` JSON out, default + custom config, tests, committed output.

**Architecture:** Linear pure-function pipeline (adapters → normalize → match → merge → project → validate). Pydantic models at stage boundaries. GitHub enrichment conditional on detected links + `GITHUB_TOKEN`.

**Tech Stack:** Python 3.12+, Pydantic v2, `phonenumbers`, `httpx` (GitHub API), `pytest`, `slugify` (or simple slug fn)

**Spec:** `docs/superpowers/specs/2026-06-30-candidate-transformer-design.md`  
**Scenarios:** `docs/scenario_map.md`

---

## File map

| File                             | Responsibility                                                   |
| -------------------------------- | ---------------------------------------------------------------- |
| `src/models.py`                  | `RawRecord`, `CanonicalRecord`, `ProjectionConfig`, shared types |
| `src/normalize/*.py`             | Per-field normalization utilities                                |
| `src/adapters/csv_adapter.py`    | CSV → `RawRecord[]`                                              |
| `src/adapters/ats_adapter.py`    | ATS JSON → `RawRecord[]`                                         |
| `src/adapters/notes_adapter.py`  | Notes txt → `RawRecord[]`                                        |
| `src/adapters/link_detector.py`  | Extract GitHub handle from text/fields                           |
| `src/adapters/github_adapter.py` | GitHub API → `RawRecord`                                         |
| `src/match/identity.py`          | Union-find grouping by email/phone/name                          |
| `src/merge/survivorship.py`      | Build `CanonicalRecord` from group                               |
| `src/merge/confidence.py`        | Deterministic confidence scoring                                 |
| `src/project/paths.py`           | Resolve `emails[0]`, `skills[].name`                             |
| `src/project/projector.py`       | Config-driven output shaping                                     |
| `src/validate/validator.py`      | Post-projection validation                                       |
| `src/pipeline.py`                | Orchestrate all stages                                           |
| `src/cli.py`                     | argparse entrypoint                                              |
| `configs/custom.json`            | Demo custom config                                               |
| `tests/gold/*.json`              | Expected profiles for Dan + Ryan                                 |

---

### Task 1: Project scaffolding

**Files:**

- Create: `requirements.txt`, `pyproject.toml`, `src/__init__.py`, `tests/conftest.py`, `pytest.ini`

- [ ] **Step 1: Create requirements.txt**

```
pydantic>=2.0
phonenumbers>=8.13
httpx>=0.27
python-slugify>=8.0
pytest>=8.0
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "candidate-data-transformer"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "pydantic>=2.0",
  "phonenumbers>=8.13",
  "httpx>=0.27",
  "python-slugify>=8.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
markers = [
  "github: live GitHub API tests (requires GITHUB_TOKEN)",
]
```

- [ ] **Step 3: Create tests/conftest.py**

```python
import os
import pytest

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data")


@pytest.fixture
def sample_csv():
    return os.path.join(SAMPLE_DIR, "recruiter_export.csv")


@pytest.fixture
def sample_ats():
    return os.path.join(SAMPLE_DIR, "ats_export.json")


@pytest.fixture
def sample_notes():
    return os.path.join(SAMPLE_DIR, "recruiter_notes.txt")


def pytest_configure(config):
    config.addinivalue_line("markers", "github: live GitHub API tests")
```

- [ ] **Step 4: Install and verify**

Run: `pip install -e ".[dev]"`  
Expected: success

- [ ] **Step 5: Commit**

```bash
git add requirements.txt pyproject.toml src/__init__.py tests/conftest.py
git commit -m "chore: project scaffolding with pytest and dependencies"
```

---

### Task 2: Core models

**Files:**

- Create: `src/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_models.py
from src.models import RawRecord, FieldValue, CanonicalRecord, ProjectionConfig


def test_raw_record_roundtrip():
    rec = RawRecord(
        source="csv",
        fields={"full_name": FieldValue(value="Linus Torvalds", method="direct")},
    )
    assert rec.source == "csv"
    assert rec.fields["full_name"].value == "Linus Torvalds"


def test_projection_config_parses_from_alias():
    cfg = ProjectionConfig.model_validate({
        "fields": [{"path": "primary_email", "from": "emails[0]", "type": "string"}],
        "on_missing": "null",
    })
    assert cfg.fields[0].from_ == "emails[0]"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`  
Expected: FAIL `ModuleNotFoundError: src.models`

- [ ] **Step 3: Implement src/models.py**

```python
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class FieldValue(BaseModel):
    value: Any
    method: Literal["direct", "extracted", "inferred"]


class RawRecord(BaseModel):
    source: Literal["csv", "ats", "recruiter_notes", "github"]
    fields: dict[str, FieldValue]


class Location(BaseModel):
    city: str | None = None
    region: str | None = None
    country: str | None = None


class LinkSet(BaseModel):
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    other: list[str] = Field(default_factory=list)


class SkillEntry(BaseModel):
    name: str
    confidence: float
    sources: list[str]


class ExperienceEntry(BaseModel):
    company: str
    title: str
    start: str | None = None
    end: str | None = None
    summary: str | None = None


class EducationEntry(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    end_year: int | None = None


class ProvenanceEntry(BaseModel):
    field: str
    source: str
    method: str


class CanonicalRecord(BaseModel):
    candidate_id: str
    full_name: str
    emails: list[str]
    phones: list[str]
    location: Location = Field(default_factory=Location)
    links: LinkSet = Field(default_factory=LinkSet)
    headline: str | None = None
    years_experience: int | None = None
    skills: list[SkillEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    provenance: list[ProvenanceEntry] = Field(default_factory=list)
    overall_confidence: float = 0.0
    matched_by: Literal["email", "phone", "name"] = "email"


class FieldSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    path: str
    from_: str | None = Field(None, alias="from")
    type: Literal["string", "string[]", "number", "object", "null"]
    required: bool = False
    normalize: Literal["E164", "canonical"] | None = None


class ProjectionConfig(BaseModel):
    fields: list[FieldSpec] = Field(default_factory=list)
    include_confidence: bool = True
    include_provenance: bool = True
    on_missing: Literal["null", "omit", "error"] = "null"


class CandidateGroup(BaseModel):
    records: list[RawRecord]
    matched_by: Literal["email", "phone", "name"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add core Pydantic models for pipeline stages"
```

---

### Task 3: Phone and email normalization

**Files:**

- Create: `src/normalize/__init__.py`, `src/normalize/phones.py`, `src/normalize/emails.py`
- Test: `tests/test_normalize.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_normalize.py
from src.normalize.phones import normalize_phone
from src.normalize.emails import normalize_email


def test_normalize_phone_e164_us():
    assert normalize_phone("+1-650-555-0101") == "+16505550101"
    assert normalize_phone("650-555-0101") == "+16505550101"


def test_normalize_phone_invalid_returns_none():
    assert normalize_phone("not-a-phone") is None


def test_normalize_email_lowercase():
    assert normalize_email("Linus.Torvalds@Example.COM") == "linus.torvalds@example.com"


def test_normalize_email_invalid_returns_none():
    assert normalize_email("not-an-email") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalize.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement**

```python
# src/normalize/phones.py
import phonenumbers


def normalize_phone(raw: str | None, default_region: str = "US") -> str | None:
    if not raw or not str(raw).strip():
        return None
    try:
        parsed = phonenumbers.parse(str(raw).strip(), default_region)
        if not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        return None
```

```python
# src/normalize/emails.py
import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(raw: str | None) -> str | None:
    if not raw:
        return None
    email = str(raw).strip().lower()
    if not _EMAIL_RE.match(email):
        return None
    return email
```

```python
# src/normalize/__init__.py
from .phones import normalize_phone
from .emails import normalize_email
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_normalize.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/normalize tests/test_normalize.py
git commit -m "feat: add phone E.164 and email normalization"
```

---

### Task 4: Names and skills normalization

**Files:**

- Create: `src/normalize/names.py`, `src/normalize/skills.py`
- Modify: `tests/test_normalize.py`

- [ ] **Step 1: Write failing tests**

```python
from src.normalize.names import normalize_name
from src.normalize.skills import canonicalize_skill, extract_skills_from_text


def test_normalize_name_title_case():
    assert normalize_name("  linus torvalds ") == "Linus Torvalds"


def test_canonicalize_skill_aliases():
    assert canonicalize_skill("JS") == "javascript"
    assert canonicalize_skill("Golang") == "go"
    assert canonicalize_skill("Rust") == "rust"


def test_extract_skills_from_notes():
    text = "mostly frontend - React, JavaScript, TypeScript"
    found = extract_skills_from_text(text)
    assert "javascript" in found
    assert "typescript" in found
    assert "react" in found
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalize.py::test_canonicalize_skill_aliases -v`  
Expected: FAIL

- [ ] **Step 3: Implement**

```python
# src/normalize/names.py
def normalize_name(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    return " ".join(part.capitalize() for part in str(raw).strip().split())
```

```python
# src/normalize/skills.py
import re

SKILL_ALIASES: dict[str, str] = {
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "golang": "go",
    "go": "go",
    "react": "react",
    "vue": "vue",
    "rust": "rust",
    "python": "python",
    "c": "c",
    "svg": "svg",
}

_SKILL_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(SKILL_ALIASES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def canonicalize_skill(raw: str) -> str:
    key = raw.strip().lower()
    return SKILL_ALIASES.get(key, key)


def extract_skills_from_text(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in _SKILL_PATTERN.finditer(text):
        skill = canonicalize_skill(match.group(0))
        if skill not in seen:
            seen.add(skill)
            out.append(skill)
    return out
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_normalize.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/normalize/names.py src/normalize/skills.py tests/test_normalize.py
git commit -m "feat: add name and skill canonicalization"
```

---

### Task 5: CSV adapter

**Files:**

- Create: `src/adapters/__init__.py`, `src/adapters/csv_adapter.py`
- Test: `tests/test_adapters.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_adapters.py
from src.adapters.csv_adapter import parse_csv


def test_parse_csv_emits_one_record_per_row(sample_csv):
    records = parse_csv(sample_csv)
    names = [r.fields["full_name"].value for r in records]
    assert names.count("Linus Torvalds") == 1  # duplicate row deduped
    assert "Dan Abramov" in names
    assert len(records) == 5


def test_parse_csv_maps_columns():
    records = parse_csv("sample_data/recruiter_export.csv")
    linus = next(r for r in records if r.fields["full_name"].value == "Linus Torvalds")
    assert linus.source == "csv"
    assert linus.fields["email"].value == "linus.torvalds@example.com"
    assert linus.fields["current_company"].value == "Linux Foundation"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapters.py::test_parse_csv_emits_one_record_per_row -v`  
Expected: FAIL

- [ ] **Step 3: Implement csv_adapter.py**

```python
# src/adapters/csv_adapter.py
import csv
import logging
from pathlib import Path
from src.models import RawRecord, FieldValue

logger = logging.getLogger(__name__)

COLUMN_MAP = {
    "name": "full_name",
    "email": "email",
    "phone": "phone",
    "current_company": "current_company",
    "title": "current_title",
}


def parse_csv(path: str | Path) -> list[RawRecord]:
    records: list[RawRecord] = []
    seen: set[tuple] = set()
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row.get("name", "").strip():
                logger.warning("Skipping CSV row with no name: %s", row)
                continue
            key = tuple(row.get(k, "") for k in ("name", "email", "phone", "current_company", "title"))
            if key in seen:
                continue
            seen.add(key)
            fields = {}
            for src_col, dst in COLUMN_MAP.items():
                val = row.get(src_col)
                if val is not None and str(val).strip():
                    fields[dst] = FieldValue(value=str(val).strip(), method="direct")
            records.append(RawRecord(source="csv", fields=fields))
    return records
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_adapters.py -v`  
Expected: PASS (only csv tests for now)

- [ ] **Step 5: Commit**

```bash
git add src/adapters tests/test_adapters.py
git commit -m "feat: add CSV adapter with within-source dedup"
```

---

### Task 6: ATS adapter

**Files:**

- Create: `src/adapters/ats_adapter.py`
- Modify: `tests/test_adapters.py`

- [ ] **Step 1: Write failing tests**

```python
from src.adapters.ats_adapter import parse_ats


def test_parse_ats_maps_fields(sample_ats):
    records = parse_ats(sample_ats)
    linus = next(r for r in records if r.fields.get("full_name") and r.fields["full_name"].value == "Linus Torvalds")
    assert linus.fields["email"].value == "linus.torvalds@example.com"
    assert linus.fields["github_url"].value == "https://github.com/torvalds"


def test_parse_ats_skips_glitch_entry(sample_ats):
    records = parse_ats(sample_ats)
    names = [r.fields["full_name"].value for r in records if "full_name" in r.fields]
    assert "Glitch Entry" not in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapters.py::test_parse_ats_maps_fields -v`  
Expected: FAIL

- [ ] **Step 3: Implement ats_adapter.py**

```python
# src/adapters/ats_adapter.py
import json
import logging
from pathlib import Path
from src.models import RawRecord, FieldValue
from src.normalize.emails import normalize_email

logger = logging.getLogger(__name__)

ATS_MAP = {
    "candidate_name": "full_name",
    "contact_email": "email",
    "contact_phone": "phone",
    "employer": "current_company",
    "job_title": "current_title",
    "github_url": "github_url",
}


def parse_ats(path: str | Path) -> list[RawRecord]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to parse ATS file %s: %s", path, exc)
        return []

    records: list[RawRecord] = []
    for entry in data.get("candidates", []):
        name = entry.get("candidate_name")
        if not name or not str(name).strip():
            logger.warning("Skipping ATS entry with no name: %s", entry)
            continue
        email_raw = entry.get("contact_email")
        if email_raw is not None and normalize_email(str(email_raw)) is None:
            logger.warning("Skipping ATS entry with invalid email: %s", entry.get("candidate_name"))
            continue
        fields: dict[str, FieldValue] = {}
        for src, dst in ATS_MAP.items():
            val = entry.get(src)
            if val is not None and str(val).strip():
                fields[dst] = FieldValue(value=val if not isinstance(val, str) else val.strip(), method="direct")
        if not fields.get("full_name"):
            continue
        records.append(RawRecord(source="ats", fields=fields))
    return records
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_adapters.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/ats_adapter.py tests/test_adapters.py
git commit -m "feat: add ATS JSON adapter with glitch row rejection"
```

---

### Task 7: Recruiter notes adapter

**Files:**

- Create: `src/adapters/notes_adapter.py`
- Modify: `tests/test_adapters.py`

- [ ] **Step 1: Write failing tests**

```python
from src.adapters.notes_adapter import parse_notes


def test_parse_notes_splits_sections(sample_notes):
    records = parse_notes(sample_notes)
    names = {r.fields["full_name"].value for r in records}
    assert "Sarah Drasner" in names
    assert "Jane Doe" in names


def test_parse_notes_extracts_skills_and_years(sample_notes):
    records = parse_notes("sample_data/recruiter_notes.txt")
    dan = next(r for r in records if r.fields["full_name"].value == "Dan Abramov")
    skill_vals = [fv.value for k, fv in dan.fields.items() if k.startswith("skill_")]
    assert "javascript" in skill_vals or any("javascript" in str(v) for v in skill_vals)
    assert dan.fields.get("years_experience") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapters.py::test_parse_notes_splits_sections -v`  
Expected: FAIL

- [ ] **Step 3: Implement notes_adapter.py**

```python
# src/adapters/notes_adapter.py
import re
import logging
from pathlib import Path
from src.models import RawRecord, FieldValue
from src.normalize.skills import extract_skills_from_text, canonicalize_skill
from src.adapters.link_detector import find_github_handle

logger = logging.getLogger(__name__)

SECTION_RE = re.compile(r"^=== Candidate:\s*(.+?)\s*===$", re.MULTILINE)
YEARS_RE = re.compile(r"(\d+)\+?\s*years?", re.IGNORECASE)


def parse_notes(path: str | Path) -> list[RawRecord]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        logger.error("Failed to read notes file %s: %s", path, exc)
        return []

    records: list[RawRecord] = []
    matches = list(SECTION_RE.finditer(text))
    for i, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        fields: dict[str, FieldValue] = {
            "full_name": FieldValue(value=name, method="direct"),
        }
        years = YEARS_RE.search(body)
        if years:
            fields["years_experience"] = FieldValue(value=int(years.group(1)), method="extracted")
        for skill in extract_skills_from_text(body):
            fields[f"skill_{skill}"] = FieldValue(value=skill, method="extracted")
        handle = find_github_handle(body)
        if handle:
            fields["github_url"] = FieldValue(value=f"https://github.com/{handle}", method="extracted")
        records.append(RawRecord(source="recruiter_notes", fields=fields))
    return records
```

Also create minimal `link_detector.py` stub used above:

```python
# src/adapters/link_detector.py
import re

GITHUB_RE = re.compile(r"(?:https?://)?github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))", re.IGNORECASE)


def find_github_handle(text: str) -> str | None:
    m = GITHUB_RE.search(text or "")
    return m.group(1) if m else None


def find_github_from_record_fields(fields: dict) -> str | None:
    for key in ("github_url",):
        fv = fields.get(key)
        if fv and fv.value:
            return find_github_handle(str(fv.value))
    for fv in fields.values():
        if isinstance(fv.value, str):
            handle = find_github_handle(fv.value)
            if handle:
                return handle
    return None
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_adapters.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/notes_adapter.py src/adapters/link_detector.py tests/test_adapters.py
git commit -m "feat: add recruiter notes adapter with skill and github extraction"
```

---

### Task 8: Identity matching

**Files:**

- Create: `src/match/__init__.py`, `src/match/identity.py`
- Test: `tests/test_match.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_match.py
from src.models import RawRecord, FieldValue, CandidateGroup
from src.match.identity import group_records


def _rec(source, name, email=None, phone=None):
    fields = {"full_name": FieldValue(value=name, method="direct")}
    if email:
        fields["email"] = FieldValue(value=email, method="direct")
    if phone:
        fields["phone"] = FieldValue(value=phone, method="direct")
    return RawRecord(source=source, fields=fields)


def test_group_by_email():
    records = [
        _rec("csv", "Linus Torvalds", "linus@example.com"),
        _rec("ats", "Linus Torvalds", "linus@example.com"),
    ]
    groups = group_records(records)
    assert len(groups) == 1
    assert groups[0].matched_by == "email"


def test_group_by_name_fallback():
    records = [
        _rec("csv", "Ryan Carniato", "ryan.carniato@example.com"),
        _rec("ats", "Ryan Carniato", "ryan.carniatto@example.com"),
    ]
    groups = group_records(records)
    assert len(groups) == 1
    assert groups[0].matched_by == "name"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_match.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement identity.py**

Use union-find with three passes:

1. Join records sharing normalized email
2. Join records sharing normalized phone (among unjoined or within components)
3. Join records sharing exact normalized name

Track weakest tier used to merge each component.

```python
# src/match/identity.py
from src.models import RawRecord, CandidateGroup
from src.normalize.emails import normalize_email
from src.normalize.phones import normalize_phone
from src.normalize.names import normalize_name

TIER_RANK = {"email": 3, "phone": 2, "name": 1}


class _UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _record_keys(rec: RawRecord) -> dict[str, set[str]]:
    keys: dict[str, set[str]] = {"email": set(), "phone": set(), "name": set()}
    email = rec.fields.get("email")
    if email:
        norm = normalize_email(str(email.value))
        if norm:
            keys["email"].add(norm)
    phone = rec.fields.get("phone")
    if phone:
        norm = normalize_phone(str(phone.value))
        if norm:
            keys["phone"].add(norm)
    name = rec.fields.get("full_name")
    if name:
        norm = normalize_name(str(name.value))
        if norm:
            keys["name"].add(norm)
    return keys


def group_records(records: list[RawRecord]) -> list[CandidateGroup]:
    if not records:
        return []
    n = len(records)
    uf = _UnionFind(n)
    component_tier: dict[int, str] = {i: "email" for i in range(n)}
    all_keys = [_record_keys(r) for r in records]

    def merge_by(tier: str):
        bucket: dict[str, list[int]] = {}
        for idx, keys in enumerate(all_keys):
            for key in keys[tier]:
                bucket.setdefault(key, []).append(idx)
        for indices in bucket.values():
            if len(indices) < 2:
                continue
            root = indices[0]
            for other in indices[1:]:
                uf.union(root, other)
                r = uf.find(root)
                if TIER_RANK[tier] < TIER_RANK[component_tier.get(r, "email")]:
                    component_tier[r] = tier

    merge_by("email")
    merge_by("phone")
    merge_by("name")

    groups_map: dict[int, list[RawRecord]] = {}
    tier_map: dict[int, str] = {}
    for i, rec in enumerate(records):
        root = uf.find(i)
        groups_map.setdefault(root, []).append(rec)
        tier_map[root] = component_tier.get(root, "email")

    return [
        CandidateGroup(records=recs, matched_by=tier_map[root])  # type: ignore[arg-type]
        for root, recs in groups_map.items()
    ]
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_match.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/match tests/test_match.py
git commit -m "feat: add tiered identity matching with union-find"
```

---

### Task 9: Merge and confidence

**Files:**

- Create: `src/merge/__init__.py`, `src/merge/survivorship.py`, `src/merge/confidence.py`
- Test: `tests/test_merge.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_merge.py
from src.models import RawRecord, FieldValue, CandidateGroup
from src.merge.survivorship import merge_group


def test_merge_csv_wins_title_conflict():
    group = CandidateGroup(
        matched_by="email",
        records=[
            RawRecord(source="csv", fields={
                "full_name": FieldValue(value="Dan Abramov", method="direct"),
                "email": FieldValue(value="dan.abramov@example.com", method="direct"),
                "current_title": FieldValue(value="Engineer", method="direct"),
                "current_company": FieldValue(value="Bluesky", method="direct"),
            }),
            RawRecord(source="ats", fields={
                "full_name": FieldValue(value="Dan Abramov", method="direct"),
                "email": FieldValue(value="dan.abramov@example.com", method="direct"),
                "current_title": FieldValue(value="Staff Software Engineer", method="direct"),
                "current_company": FieldValue(value="Bluesky", method="direct"),
            }),
        ],
    )
    profile = merge_group(group)
    assert profile.experience[0].title == "Engineer"
    sources = {p.source for p in profile.provenance if p.field == "experience[0].title"}
    assert "csv" in sources
    assert "ats" in sources
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_merge.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement survivorship.py and confidence.py**

Implement `merge_group(group: CandidateGroup) -> CanonicalRecord` per spec §8:

- Union emails/phones with normalization
- Scalar survivorship trust orders
- Build `experience[0]` from winning company/title
- Collect skills from all `skill_*` fields
- Call `compute_confidence(profile, group)` from `confidence.py`

`confidence.py` implements deterministic formula from spec.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_merge.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/merge tests/test_merge.py
git commit -m "feat: add merge survivorship and confidence scoring"
```

---

### Task 10: Path resolver and projector

**Files:**

- Create: `src/project/__init__.py`, `src/project/paths.py`, `src/project/projector.py`, `configs/custom.json`
- Test: `tests/test_project.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_project.py
from src.project.paths import resolve_path
from src.project.projector import project_record
from src.models import CanonicalRecord, ProjectionConfig, FieldSpec, SkillEntry, LinkSet, Location


def test_resolve_path_index_and_array():
    data = {"emails": ["a@x.com", "b@x.com"], "skills": [{"name": "go"}, {"name": "rust"}]}
    assert resolve_path(data, "emails[0]") == "a@x.com"
    assert resolve_path(data, "skills[].name") == ["go", "rust"]


def test_project_custom_config_omits_provenance():
    canonical = CanonicalRecord(
        candidate_id="dan",
        full_name="Dan Abramov",
        emails=["dan.abramov@example.com"],
        phones=[],
        location=Location(),
        links=LinkSet(),
        headline=None,
        skills=[SkillEntry(name="javascript", confidence=0.9, sources=["recruiter_notes"])],
        overall_confidence=0.85,
        matched_by="email",
    )
    cfg = ProjectionConfig.model_validate({
        "fields": [
            {"path": "name", "from": "full_name", "type": "string", "required": True},
            {"path": "skill_names", "from": "skills[].name", "type": "string[]"},
        ],
        "include_provenance": False,
        "on_missing": "omit",
    })
    out = project_record(canonical, cfg)
    assert "name" in out
    assert "provenance" not in out
    assert out["skill_names"] == ["javascript"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_project.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement paths.py and projector.py**

`resolve_path` handles `field`, `field[0]`, `field[].subfield`.

`project_record`:

- No config → `canonical.model_dump()`
- With config → build dict per `FieldSpec`, apply `on_missing`, attach confidence/provenance flags

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_project.py -v`  
Expected: PASS

- [ ] **Step 5: Create configs/custom.json** (from spec) and commit

```bash
git add src/project configs/custom.json tests/test_project.py
git commit -m "feat: add projection layer with path resolver and custom config"
```

---

### Task 11: Validator

**Files:**

- Create: `src/validate/__init__.py`, `src/validate/validator.py`
- Test: `tests/test_project.py` (add validation tests)

- [ ] **Step 1: Write failing test**

```python
import pytest
from src.validate.validator import validate_output
from src.models import ProjectionConfig, FieldSpec


def test_validate_required_field_missing_raises():
    cfg = ProjectionConfig(fields=[FieldSpec(path="primary_email", type="string", required=True)], on_missing="error")
    with pytest.raises(ValueError, match="primary_email"):
        validate_output({}, cfg)
```

- [ ] **Step 2–4: Implement, test, pass**

`validate_output(output: dict, config: ProjectionConfig) -> dict` checks required + types.

- [ ] **Step 5: Commit**

```bash
git add src/validate tests/test_project.py
git commit -m "feat: add post-projection output validation"
```

---

### Task 12: GitHub adapter

**Files:**

- Create: `src/adapters/github_adapter.py`
- Test: `tests/test_github.py`

- [ ] **Step 1: Write test (skipped without token)**

```python
# tests/test_github.py
import os
import pytest
from src.adapters.github_adapter import fetch_github_record

@pytest.mark.github
def test_fetch_torvalds():
    if not os.environ.get("GITHUB_TOKEN"):
        pytest.skip("GITHUB_TOKEN not set")
    rec = fetch_github_record("torvalds")
    assert rec.source == "github"
    assert "full_name" in rec.fields
```

- [ ] **Step 2: Implement github_adapter.py**

Use `httpx` + `Authorization: Bearer {token}`. On 404/HTTP error → log + return `None`.

Map: name, bio→headline, html*url→github_url, repo languages→skill*\* fields.

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_github.py -v`  
Expected: SKIPPED (no token) or PASS (with token)

- [ ] **Step 4: Commit**

```bash
git add src/adapters/github_adapter.py tests/test_github.py
git commit -m "feat: add GitHub enrichment adapter with soft failure"
```

---

### Task 13: Pipeline orchestrator

**Files:**

- Create: `src/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing integration test (no github)**

```python
# tests/test_pipeline.py
from src.pipeline import run_pipeline


def test_pipeline_produces_profiles_without_github(sample_csv, sample_ats, sample_notes):
    result = run_pipeline(csv_path=sample_csv, ats_path=sample_ats, notes_path=sample_notes, enrich_github=False)
    assert "profiles" in result
    names = {p["full_name"] for p in result["profiles"]}
    assert "Linus Torvalds" in names
    assert "Dan Abramov" in names
    assert "Sarah Drasner" in names
    ryan = next(p for p in result["profiles"] if p["full_name"] == "Ryan Carniato")
    assert ryan["matched_by"] == "name"
```

- [ ] **Step 2: Implement pipeline.py**

```python
def run_pipeline(
    csv_path=None,
    ats_path=None,
    notes_path=None,
    config=None,
    enrich_github=True,
) -> dict:
    # 1. parse all sources -> records[]
    # 2. group_records
    # 3. per group: detect github handle, optionally fetch and append record, re-normalize
    # 4. merge_group -> canonical
    # 5. project_record -> dict
    # 6. validate_output
    # 7. return {"profiles": [...]}
```

- [ ] **Step 3: Run test**

Run: `pytest tests/test_pipeline.py -v`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/pipeline.py tests/test_pipeline.py
git commit -m "feat: add end-to-end pipeline orchestrator"
```

---

### Task 14: CLI

**Files:**

- Create: `src/cli.py`
- Test: manual + `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI test**

```python
# tests/test_cli.py
import json
import subprocess
import sys


def test_cli_writes_profiles(tmp_path, sample_csv, sample_ats, sample_notes):
    out = tmp_path / "out.json"
    cmd = [
        sys.executable, "-m", "src.cli",
        "--csv", sample_csv,
        "--ats", sample_ats,
        "--notes", sample_notes,
        "--out", str(out),
    ]
    subprocess.run(cmd, check=True, cwd=".")
    data = json.loads(out.read_text())
    assert "profiles" in data
    assert len(data["profiles"]) >= 8
```

- [ ] **Step 2: Implement cli.py**

argparse with `--csv`, `--ats`, `--notes`, `--config`, `--out`. Load config JSON if provided. Call `run_pipeline`. Write pretty JSON.

- [ ] **Step 3: Run test**

Run: `pytest tests/test_cli.py -v`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/cli.py tests/test_cli.py
git commit -m "feat: add CLI entrypoint with explicit file flags"
```

---

### Task 15: Gold profile tests

**Files:**

- Create: `tests/gold/dan_abramov.json`, `tests/gold/ryan_carniato.json`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Generate gold files**

Run pipeline without github, extract Dan + Ryan profiles, save key assertions to gold JSON (title, matched_by, provenance sources).

- [ ] **Step 2: Write assertion tests**

```python
def test_dan_survivorship_matches_gold(sample_csv, sample_ats, sample_notes):
    result = run_pipeline(csv_path=sample_csv, ats_path=sample_ats, notes_path=sample_notes, enrich_github=False)
    dan = next(p for p in result["profiles"] if p["full_name"] == "Dan Abramov")
    assert dan["experience"][0]["title"] == "Engineer"
```

- [ ] **Step 3: Commit**

```bash
git add tests/gold tests/test_pipeline.py
git commit -m "test: add gold profile assertions for survivorship and name match"
```

---

### Task 16: Committed output + README

**Files:**

- Create: `output/default_profiles.json`, `output/custom_profiles.json`, `README.md`

- [ ] **Step 1: Generate default output**

```bash
python -m src.cli --csv sample_data/recruiter_export.csv --ats sample_data/ats_export.json --notes sample_data/recruiter_notes.txt --out output/default_profiles.json
```

With `GITHUB_TOKEN` set for full enrichment in committed artifact.

- [ ] **Step 2: Generate custom output**

```bash
python -m src.cli --csv sample_data/recruiter_export.csv --ats sample_data/ats_export.json --notes sample_data/recruiter_notes.txt --config configs/custom.json --out output/custom_profiles.json
```

- [ ] **Step 3: Write README.md**

Sections: Overview, Requirements, Install, `GITHUB_TOKEN`, Run (default + custom), Test (`pytest`, `pytest -m github`), Project structure, Assumptions/descoped items, link to `docs/scenario_map.md`.

- [ ] **Step 4: Run full test suite**

Run: `pytest -v`  
Expected: all pass (github tests skip without token)

- [ ] **Step 5: Commit**

```bash
git add output README.md
git commit -m "docs: add README and committed pipeline output artifacts"
```

---

## Plan self-review

| Spec section       | Task                             |
| ------------------ | -------------------------------- |
| Pipeline stages    | Task 13                          |
| All 4 adapters     | Tasks 5–7, 12                    |
| Normalization      | Tasks 3–4                        |
| Identity match     | Task 8                           |
| Merge/survivorship | Task 9                           |
| Confidence         | Task 9                           |
| Projection         | Task 10                          |
| Validation         | Task 11                          |
| CLI                | Task 14                          |
| 10 scenarios       | Tasks 6–9, 13, 15 + scenario_map |
| GitHub live API    | Task 12                          |
| Committed output   | Task 16                          |

No TBD placeholders. Type names consistent with `src/models.py` Task 2.

---

## Execution handoff

**Plan saved to `docs/superpowers/plans/2026-06-30-candidate-transformer.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks
2. **Inline Execution** — implement tasks in this session with checkpoints

Which approach do you want?
