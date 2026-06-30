# Multi-Source Candidate Data Transformer — Design Spec

**Date:** 2026-06-30  
**Status:** Approved  
**Goal:** Full Eightfold Step 2 submission — end-to-end pipeline from multi-source inputs to schema-valid JSON (default + custom config).

---

## 1. Problem & success criteria

Build a deterministic transformer that ingests messy candidate data from multiple sources and emits one canonical JSON profile per person, with provenance and confidence. Wrong-but-confident is worse than honestly empty.

**Submission must include:**

- Runnable public repo with README, tests, and committed output artifacts
- Default schema output and custom-config output from `sample_data/`
- CLI with explicit file flags
- Live GitHub enrichment when `GITHUB_TOKEN` is set
- ~2 min demo video (script in plan doc)

**Success =** all 10 scenarios in `docs/scenario_map.md` produce expected behavior; custom config reshapes merged data without re-running merge logic.

---

## 2. Decisions (brainstorming outcomes)

| Decision             | Choice                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Scope                | Full submission end-to-end                                                               |
| Implementation style | Layered pure pipeline + Pydantic boundaries                                              |
| Sample data          | `sample_data/` (user-provided); see `docs/scenario_map.md`                               |
| GitHub API           | Live REST only via `GITHUB_TOKEN`; tests marked `@pytest.mark.github` skip without token |
| CLI input            | Explicit flags: `--csv`, `--ats`, `--notes`, `--config`, `--out`                         |
| CLI output           | Single JSON file: `{ "profiles": [ ... ] }`                                              |
| No `--config`        | Emit full default canonical schema                                                       |
| Language             | Python 3.12+                                                                             |
| Storage              | In-memory only; no database                                                              |
| UI                   | CLI only                                                                                 |

---

## 3. Pipeline architecture

```
CLI args
  → adapters (csv, ats, notes)     → RawRecord[]
  → link_detector                  → GitHub handle per logical candidate context
  → github_adapter (optional)      → additional RawRecord[] per handle
  → normalize (per record)         → RawRecord[]
  → identity_match                 → CandidateGroup[]
  → merge/survivorship             → CanonicalRecord per group
  → project (config or default)    → dict per candidate
  → validate                       → dict per candidate
  → write { "profiles": [...] }
```

Each stage is a **pure function** on the previous stage's output. No stage reaches backward. Same inputs → same outputs.

### Multi-candidate flow

1. Each adapter emits **many** `RawRecord`s (one per person per source).
2. Notes adapter splits on `=== Candidate: (.+) ===` headers.
3. CSV: one record per row; skip malformed rows, log warning.
4. ATS: one record per `candidates[]` entry; skip entries with unrecoverable identity (no email, phone, or name).
5. Identity matcher groups **all** records across **all** sources.
6. Unmatched singletons (e.g. notes-only Sarah) still become profiles.
7. GitHub enrichment runs **per group** after initial grouping attempt, using link found in any group member's records; re-group if enrichment adds join keys (not expected in sample data).

### `candidate_id`

- Primary: slug from first normalized email (`linus.torvalds@example.com` → `linus-torvalds-example-com`)
- Fallback: slugify normalized `full_name`

---

## 4. Data models

### 4.1 RawRecord (adapter output)

```python
class FieldValue(BaseModel):
    value: Any
    method: Literal["direct", "extracted", "inferred"]

class RawRecord(BaseModel):
    source: Literal["csv", "ats", "recruiter_notes", "github"]
    fields: dict[str, FieldValue]
```

Adapters are the **only** modules that know source-specific formats.

**ATS field mapping:**

| ATS key          | Canonical field   |
| ---------------- | ----------------- |
| `candidate_name` | `full_name`       |
| `contact_email`  | `email`           |
| `contact_phone`  | `phone`           |
| `employer`       | `current_company` |
| `job_title`      | `current_title`   |
| `github_url`     | `github_url`      |

**CSV columns:** `name`, `email`, `phone`, `current_company`, `title` → same canonical keys.

**Notes extraction:** `full_name` from section header; skills via keyword dict; `years_experience` via regex `(\d+)\+?\s*years`; `github_url` via link-detector regex on section body.

### 4.2 CanonicalRecord (merge output, internal)

```python
class Location(BaseModel):
    city: str | None = None
    region: str | None = None
    country: str | None = None  # ISO-3166 alpha-2 when resolvable

class LinkSet(BaseModel):
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    other: list[str] = []

class SkillEntry(BaseModel):
    name: str
    confidence: float
    sources: list[str]

class ExperienceEntry(BaseModel):
    company: str
    title: str
    start: str | None = None  # YYYY-MM
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
    location: Location
    links: LinkSet
    headline: str | None
    years_experience: int | None
    skills: list[SkillEntry]
    experience: list[ExperienceEntry]
    education: list[EducationEntry]
    provenance: list[ProvenanceEntry]
    overall_confidence: float
    matched_by: Literal["email", "phone", "name"]
```

### 4.3 Projection config

```python
class FieldSpec(BaseModel):
    path: str
    from_: str | None = Field(None, alias="from")
    type: Literal["string", "string[]", "number", "object", "null"]
    required: bool = False
    normalize: Literal["E164", "canonical"] | None = None

class ProjectionConfig(BaseModel):
    fields: list[FieldSpec]
    include_confidence: bool = True
    include_provenance: bool = True
    on_missing: Literal["null", "omit", "error"] = "null"
```

Example custom config (`configs/custom.json`):

```json
{
  "fields": [
    { "path": "name", "from": "full_name", "type": "string", "required": true },
    {
      "path": "primary_email",
      "from": "emails[0]",
      "type": "string",
      "required": true
    },
    {
      "path": "phone",
      "from": "phones[0]",
      "type": "string",
      "normalize": "E164"
    },
    {
      "path": "skill_names",
      "from": "skills[].name",
      "type": "string[]",
      "normalize": "canonical"
    }
  ],
  "include_confidence": true,
  "include_provenance": false,
  "on_missing": "omit"
}
```

---

## 5. Source adapters

| Source | File                   | Behavior                                                                      |
| ------ | ---------------------- | ----------------------------------------------------------------------------- |
| CSV    | `recruiter_export.csv` | `csv.DictReader`; skip rows missing name; dedupe identical rows within source |
| ATS    | `ats_export.json`      | Parse `candidates[]`; skip Glitch Entry (invalid email, no phone/name usable) |
| Notes  | `recruiter_notes.txt`  | Split sections; extract fields heuristically                                  |
| GitHub | REST API               | Conditional; only if link detected in group's records                         |

### Link detection priority (per record text fields)

1. ATS `github_url` field (direct)
2. Notes body regex: `(?:https?://)?github\.com/([A-Za-z0-9-]+)`
3. CSV link-shaped columns (if any)

First valid handle wins for that record. Enrichment fetches `/users/{handle}` and `/users/{handle}/repos`; maps to `full_name`, `headline` (bio), `skills` (from repo languages), `links.github`.

**GitHub failure policy:** 404 / rate limit / no token → log warning, skip enrichment for that handle, continue pipeline. No crash.

---

## 6. Normalization

Applied per-field on each `RawRecord` before identity matching:

| Type    | Rule                                                                                |
| ------- | ----------------------------------------------------------------------------------- |
| Dates   | `YYYY-MM`                                                                           |
| Phones  | E.164 via `phonenumbers` lib; invalid → drop field                                  |
| Names   | strip + title-case                                                                  |
| Emails  | lowercase strip; invalid format → drop                                              |
| Skills  | canonical dict (`JS`→`javascript`, `Golang`→`go`); unknown → lowercase pass-through |
| Country | ISO-3166 alpha-2 when resolvable; else keep raw                                     |

---

## 7. Identity matching

Exact match only (no fuzzy), and **cross-source joins only on email or
phone** — name is never used to join records from different sources, only
as a fallback label for confidence weighting on otherwise-unjoined
singletons. Tier order for joins:

1. **Email** — normalized email intersection
2. **Phone** — normalized E.164 intersection

Record `matched_by` on each `CanonicalRecord` reflects the **weakest** tier used to join any pair in the group (email < phone). For a singleton record (no join happened), `matched_by` reflects the best identity key present on that record — `email` > `phone` > `name` — which is a confidence signal, not evidence of a cross-source match.

**Union-find** (or equivalent) to build groups transitively.

**Explicit scope cut:** no name-based identity joins across sources, and no fuzzy matching (Jaro-Winkler, nicknames). A wrong merge silently pollutes the profile; a duplicate, lower-confidence profile is the safer failure mode. See `architecture.md` §6 for the full rationale.

### Expected sample outcomes (curated fixtures)

| Candidate | Match tier                                                                                                  |
| --------- | ----------------------------------------------------------------------------------------------------------- |
| Linus     | email                                                                                                       |
| Dan       | email (CSV+ATS); separate low-confidence singleton from notes-only mention                                  |
| Sindre    | phone (CSV email + ATS null email)                                                                          |
| Addy      | singleton (CSV only), matched_by: email                                                                     |
| Evan      | email (ATS + notes both carry email)                                                                        |
| Glitch    | skipped (invalid email, no phone, unrecoverable identity)                                                   |
| Sarah     | singleton (notes only), matched_by: name                                                                    |
| Jane      | singleton (notes only), matched_by: name                                                                    |
| Ryan      | **stays as two singletons** (email/phone typo prevents join) — not merged, see `scenario_map.md` scenario 9 |

---

## 8. Merge & survivorship

### Array fields (`emails`, `phones`, `skills`)

Union across all sources in group, dedupe after normalization. Each skill tracks `sources[]`.

### Scalar fields — trust order

| Field                                                 | Trust order                              |
| ----------------------------------------------------- | ---------------------------------------- |
| `full_name`                                           | csv → ats → recruiter_notes → github     |
| `current_company` / `current_title` → `experience[0]` | csv → ats                                |
| `headline`                                            | recruiter_notes (extracted) → github bio |
| `education`                                           | ats → null                               |
| `years_experience`                                    | ats → recruiter_notes (extracted) → null |

Fall through to next source only when higher-trust source lacks a value.

**Provenance:** every winning value gets `{ field, source, method }`. Losing scalar values for same field are still logged in provenance with note of survivorship (field `title` from ats when csv wins).

### Confidence formula (deterministic)

```
base = MATCH_TIER_WEIGHT[matched_by] * SOURCE_TRUST[winning_source]

MATCH_TIER_WEIGHT: email=1.0, phone=0.85, name=0.6
SOURCE_TRUST: csv=0.95, ats=0.90, recruiter_notes=0.70, github=0.75

agreement_bonus = 0.05 per field where 2+ sources agree on normalized value
overall_confidence = clamp(mean(per-field scores) + agreement_bonus, 0, 1)
```

Per-skill confidence = `SOURCE_TRUST[primary_source]` for that skill mention.

---

## 9. Projection layer

Canonical record is **never mutated** by config. Projector:

1. Walks `config.fields[]`
2. Resolves `from` path (or `path` if `from` omitted) against canonical dict
3. Applies `normalize` if specified
4. Applies `on_missing` when value absent
5. Adds `overall_confidence` / `provenance` per flags

### Path resolver (no JSONPath library)

Supported patterns:

- `full_name`
- `emails[0]`
- `skills[].name`
- `links.github`

### Default projection (no config)

Serialize `CanonicalRecord.model_dump()` as-is (all canonical fields).

---

## 10. Validation

Post-projection checks against **requested** config shape:

- `required: true` fields must be present and non-null
- Types must match `FieldSpec.type`
- `on_missing: "error"` raises `ValidationError` with field path

Malformed source files: log error, treat as empty for that source (file-level degrade). Row-level: skip row, continue.

---

## 11. CLI

```bash
python -m src.cli \
  --csv sample_data/recruiter_export.csv \
  --ats sample_data/ats_export.json \
  --notes sample_data/recruiter_notes.txt \
  --out output/default_profiles.json

python -m src.cli \
  --csv sample_data/recruiter_export.csv \
  --ats sample_data/ats_export.json \
  --notes sample_data/recruiter_notes.txt \
  --config configs/custom.json \
  --out output/custom_profiles.json
```

All source flags optional (at least one required). Writes pretty-printed JSON.

Exit codes: `0` success, `1` validation error, `2` usage error.

---

## 12. Repo layout

```
src/
  __init__.py
  models.py
  pipeline.py
  cli.py
  normalize/
    __init__.py
    phones.py
    dates.py
    names.py
    skills.py
    emails.py
  adapters/
    __init__.py
    csv_adapter.py
    ats_adapter.py
    notes_adapter.py
    github_adapter.py
    link_detector.py
  match/
    __init__.py
    identity.py
  merge/
    __init__.py
    survivorship.py
    confidence.py
  project/
    __init__.py
    projector.py
    paths.py
  validate/
    __init__.py
    validator.py
configs/
  custom.json
tests/
  conftest.py
  test_normalize.py
  test_adapters.py
  test_match.py
  test_merge.py
  test_project.py
  test_pipeline.py
  gold/
    dan_abramov.json
    ryan_carniato.json
sample_data/          # existing
output/               # committed run artifacts
docs/
  architecture.md
  scenario_map.md
requirements.txt
pyproject.toml
README.md
```

---

## 13. Testing strategy

| Layer              | Coverage                                                            |
| ------------------ | ------------------------------------------------------------------- |
| Unit               | normalize, path resolver, confidence math, survivorship             |
| Adapter            | CSV row, ATS entry, notes section parsing                           |
| Integration        | Full pipeline on `sample_data/` without GitHub (enrichment skipped) |
| Gold profiles      | Dan (survivorship), Ryan (name fallback) — exact field assertions   |
| GitHub live        | `@pytest.mark.github` — Linus enrichment when token present         |
| File-level garbage | CLI pointed at truncated JSON → log + continue                      |

---

## 14. Edge cases & out of scope

**Handled:** see `docs/architecture.md` §11 and `docs/scenario_map.md`.

**Out of scope:**

- Fuzzy identity matching
- Recency-based survivorship
- Human review queue
- Persistent storage
- UI
- LinkedIn / resume parsing

---

## 15. Submission artifacts checklist

- [ ] `output/default_profiles.json` — committed
- [ ] `output/custom_profiles.json` — committed
- [ ] `README.md` — install, env, run, test
- [ ] `requirements.txt` / `pyproject.toml`
- [ ] Tests passing (`pytest`; github tests skip without token)
- [ ] `design_doc.pdf` — 1-page export from `docs/architecture.md`
- [ ] Demo video script (in implementation plan)

---

## 16. Demo video script (~2 min)

1. Show `sample_data/` three files (15s)
2. Run default CLI → open `output/default_profiles.json` → highlight Linus high confidence + provenance (30s)
3. Show Dan title conflict — CSV wins, both in provenance (20s)
4. Show Ryan `matched_by: "name"` lower confidence (15s)
5. Run custom config → show slim output, no provenance, renamed fields (25s)
6. Verbal: proud of canonical/projection separation; edge case = Jane GitHub 404 soft fail (15s)
