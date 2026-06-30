# Candidate Data Transformer

> Multi-source candidate data transformer, built for the **Eightfold AI
> Engineering Intern (Jul–Dec 2026)** take-home assignment.

Recruiting data never arrives clean or in one place. A single candidate can
show up in a recruiter's CSV export, an ATS JSON blob with completely
different field names, a recruiter's free-text notes, and (optionally) a
public GitHub profile — each with its own gaps, typos, and conflicting
values. This project turns that mess into **one canonical, trustworthy JSON
profile per candidate**, where every field is traceable to the source that
produced it (`provenance`) and carries a deterministic confidence score
(`overall_confidence`).

The guiding principle, straight from the assignment brief: **wrong-but-confident
is worse than honestly-empty.** Nothing is invented. A missing or malformed
source degrades the run gracefully instead of crashing it, and unjoined
conflicting values are kept as separate, lower-confidence profiles rather
than guessed-merged.

The output shape itself is also runtime-configurable — a JSON config can
select fields, rename them, normalize them differently, and decide what
happens on a missing value, **with no code changes**.

---

## Table of contents

- [Architecture](#architecture)
- [Canonical schema](#canonical-schema)
- [Identity matching](#identity-matching)
- [Merge, survivorship & confidence](#merge-survivorship--confidence)
- [Configurable projection layer](#configurable-projection-layer)
- [Setup](#setup)
- [Getting a GitHub token](#getting-a-github-token-optional)
- [Commands](#commands)
- [Tests](#tests)
- [Repo layout](#repo-layout)
- [Known limitations](#known-limitations-deliberate-scope-cuts)

---

## Architecture

Every stage is a **pure function** over the previous stage's output. No
stage reaches backward or sideways — same inputs always produce the same
output, and every value in the final profile can be traced back through
exactly the stages that touched it.

```mermaid
flowchart TD
    CSV["Recruiter CSV\n(structured)"]
    ATS["ATS JSON blob\n(structured)"]
    NOTES["Recruiter notes .txt\n(unstructured)"]

    CSV --> ADAPT
    ATS --> ADAPT
    NOTES --> ADAPT

    subgraph ADAPT["Adapters"]
        direction TB
        A1["source-specific parsing -> RawRecord\n(field, value, method)"]
    end

    ADAPT --> LINK["Link detector\nscan RawRecords for a github handle/URL"]
    LINK -- "handle found" --> GH["GitHub enricher\nGET /users/:handle + /repos"]
    LINK -- "no handle found" --> NORM
    GH --> NORM["Normalize\ndates, phones, names, emails, skills, location"]

    NORM --> MATCH["Identity match\nemail -> phone tiers, union-find grouping"]
    MATCH --> MERGE["Merge / survivorship\nbuild CanonicalRecord + provenance + confidence"]
    MERGE --> PROJECT["Project\napply runtime config -> reshaped output"]
    PROJECT --> VALIDATE["Validate\ncheck output against requested shape"]
    VALIDATE --> OUT["{ \"profiles\": [...] } JSON"]
```

**Why GitHub is enrichment-only, not a core source:** it's an external API.
Making it conditional (only fetched if a handle is found in one of the other
three sources) means the pipeline never has a hard network dependency — if
the API is down, rate-limited, or no handle exists anywhere, the run still
produces complete profiles, just without that extra enrichment. A 404 or
API error logs a warning and moves on; it never crashes the run.

---

## Canonical schema

The internal `CanonicalRecord` (one per matched candidate) is the single
source of truth, and it is **never mutated** by the projection config — the
config only reads from it.

| Field                | Type                                         | Notes                                       |
| -------------------- | -------------------------------------------- | ------------------------------------------- |
| `candidate_id`       | `string`                                     | slug of first email, else slug of name      |
| `full_name`          | `string`                                     |                                             |
| `emails` / `phones`  | `string[]`                                   | union across sources, deduped               |
| `location`           | `{ city, region, country }`                  | `country` coerced to ISO-3166 alpha-2       |
| `links`              | `{ linkedin, github, portfolio, other[] }`   |                                             |
| `headline`           | `string \| null`                             |                                             |
| `years_experience`   | `number \| null`                             |                                             |
| `skills`             | `[{ name, confidence, sources[] }]`          | canonical skill names                       |
| `experience`         | `[{ company, title, start, end, summary }]`  | dates as `YYYY-MM`                          |
| `education`          | `[{ institution, degree, field, end_year }]` |                                             |
| `provenance`         | `[{ field, source, method }]`                | where every value came from                 |
| `overall_confidence` | `number`                                     | deterministic, see below                    |
| `matched_by`         | `"email" \| "phone" \| "name"`               | see [Identity matching](#identity-matching) |

---

## Identity matching

Decides which `RawRecord`s — possibly from different sources — refer to
the same person. **Exact match only** (no fuzzy/probabilistic matching),
and **cross-source joins only happen on email or phone**:

```mermaid
flowchart LR
    R1["RawRecord (csv)"] --> N1["normalize email/phone/name"]
    R2["RawRecord (ats)"] --> N2["normalize email/phone/name"]
    R3["RawRecord (notes)"] --> N3["normalize email/phone/name"]

    N1 & N2 & N3 --> E{"share a\nnormalized email?"}
    E -- yes --> JOIN_E["join: matched_by = email"]
    E -- no --> P{"share a\nnormalized phone?"}
    P -- yes --> JOIN_P["join: matched_by = phone"]
    P -- no --> SEP["stay separate profiles\n(matched_by = best own key,\ne.g. 'name' if no contact info)"]
```

Records that share neither a normalized email nor phone remain **separate
profiles, even if the full name matches exactly.** This is a deliberate
scope cut: a name like "Ryan Carniato" isn't a reliable join key on its own
(common-name collisions, no de-duplication guarantee), and a false merge
silently pollutes a hiring decision — worse than a duplicate, lower-confidence
profile that a human can later reconcile. `matched_by: "name"` on an
unjoined singleton is a **confidence label**, not evidence of a cross-source
match.

Grouping uses **union-find** so joins are transitive (A↔B via email, B↔C via
phone ⇒ A, B, C are one group), processed email-tier first, then phone-tier.

---

## Merge, survivorship & confidence

**Array fields** (`emails`, `phones`, `skills`) are unioned across every
source in the matched group, deduplicated after normalization — nothing is
dropped, every skill keeps a `sources[]` list.

**Scalar fields** (`full_name`, company/title, `headline`, `education`,
`years_experience`) use a fixed source-trust order, falling through to the
next source only when the higher-trust one actually lacks a value:

| Field                                         | Trust order                              |
| --------------------------------------------- | ---------------------------------------- |
| `full_name`                                   | csv → ats → recruiter_notes → github     |
| `current_company` / `title` → `experience[0]` | csv → ats                                |
| `headline`                                    | recruiter_notes (extracted) → github bio |
| `education`                                   | ats → null                               |
| `years_experience`                            | ats → recruiter_notes (extracted) → null |

Every winning value gets a `provenance` entry `{ field, source, method }` —
and so does every _losing_ value for the same field, so a CSV/ATS title
conflict stays fully visible even though only one wins into the canonical
field.

**Confidence** is a deterministic formula — no ML, no randomness:

```
base = MATCH_TIER_WEIGHT[matched_by] * SOURCE_TRUST[winning_source]

MATCH_TIER_WEIGHT: email = 1.0, phone = 0.85, name = 0.6
SOURCE_TRUST:      csv = 0.95, ats = 0.90, recruiter_notes = 0.70, github = 0.75

agreement_bonus = +0.05 per field where 2+ sources independently agree
overall_confidence = clamp(mean(per-field scores) + agreement_bonus, 0, 1)
```

---

## Configurable projection layer

The canonical record is internal and fixed; the **output shape is not.** A
JSON config can select a subset of fields, rename/remap them, change
per-field normalization, toggle `provenance`/confidence, and decide what
happens when a requested value is missing — all without touching the
engine.

```mermaid
flowchart LR
    CR["CanonicalRecord\n(internal, full, immutable)"] --> PROJ["Projector"]
    CFG["ProjectionConfig (json)\nfields[], include_confidence,\ninclude_provenance, on_missing"] --> PROJ
    PROJ --> RESHAPED["Reshaped output dict"]
    RESHAPED --> VAL["Validator\nchecks against requested shape"]
    VAL -- "ok" --> PROFILE["profile in output"]
    VAL -- "required field missing\n+ on_missing=error" --> FAIL["ValidationError\n(exit code 1)"]
```

Example (`configs/custom.json`):

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
  "on_missing": "null"
}
```

`on_missing` has three modes: `"null"` (fill the gap), `"omit"` (drop the
key entirely), `"error"` (fail the whole profile loudly — useful when a
downstream system genuinely can't tolerate a missing field).

---

## Setup

Requires **Python 3.12+**.

```bash
git clone <this-repo-url>
cd candidate-data-transformer

python -m venv .venv
.venv\Scripts\activate        # Windows (PowerShell / cmd)
# source .venv/bin/activate   # macOS / Linux

pip install -e ".[dev]"
```

This installs the project itself plus `pytest` for the test suite (see
`pyproject.toml` for the full dependency list — `pydantic`, `phonenumbers`,
`httpx`, `python-slugify`, `pycountry`, `python-dotenv`, `Faker`).

---

## Getting a GitHub token (optional)

GitHub enrichment works **without** a token — it just falls back to
GitHub's unauthenticated rate limit (60 requests/hour per IP), which is fine
for a quick demo but will get rate-limited on a full 500-persona run. With a
token, the limit jumps to 5,000 requests/hour.

1. Go to **github.com → Settings → Developer settings → Personal access
   tokens → Tokens (classic)** (or [this direct link](https://github.com/settings/tokens)).

2. Click **Generate new token (classic)**.

3. Give it any name (e.g. `candidate-transformer-demo`) and pick an
   expiration. **Leave every scope checkbox unchecked** — this project only
   reads public profile data (`GET /users/:handle` and
   `GET /users/:handle/repos`), which needs no scopes at all.

4. Click **Generate token** and copy it immediately — GitHub only shows it
   once.

5. In the repo root:

   ```bash
   cp .env.example .env
   ```

   Then open `.env` and set:

   ```
   GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

`.env` is gitignored — it's never committed. If `GITHUB_TOKEN` isn't set,
the pipeline still runs end-to-end; it just enriches fewer/no GitHub
profiles before hitting the unauthenticated rate limit, and that's logged,
not fatal.

---

## Commands

**Run the pipeline — default schema output:**

```bash
python -m src.cli \
  --csv sample_data/recruiter_export.csv \
  --ats sample_data/ats_export.json \
  --notes sample_data/recruiter_notes.txt \
  --out output/default_profiles.json
```

**Run the pipeline — custom-config output** (renames fields, drops
provenance, omits missing values — see `configs/custom.json`):

```bash
python -m src.cli \
  --csv sample_data/recruiter_export.csv \
  --ats sample_data/ats_export.json \
  --notes sample_data/recruiter_notes.txt \
  --config configs/custom.json \
  --out output/custom_profiles.json
```

**Skip GitHub enrichment** (faster local runs, or no token set):

```bash
python -m src.cli \
  --csv sample_data/recruiter_export.csv \
  --ats sample_data/ats_export.json \
  --notes sample_data/recruiter_notes.txt \
  --out output/default_profiles.json \
  --no-github
```

**Run against any one or two sources** (at least one of `--csv` / `--ats` /
`--notes` is required — a missing source degrades gracefully, not a crash):

```bash
python -m src.cli --ats sample_data/ats_export.json --out output/ats_only.json
```

**Regenerate the 500-persona synthetic sample data** (optional — already
committed, but rescalable):

```bash
generate-samples --count 500 --seed 42 --out sample_data
```

**All CLI flags:**

| Flag          | Required              | Meaning                                                                             |
| ------------- | --------------------- | ----------------------------------------------------------------------------------- |
| `--csv`       | no (≥1 source needed) | path to recruiter CSV export                                                        |
| `--ats`       | no (≥1 source needed) | path to ATS JSON export                                                             |
| `--notes`     | no (≥1 source needed) | path to recruiter notes `.txt`                                                      |
| `--config`    | no                    | projection config JSON (defaults to `configs/default.json` = full canonical schema) |
| `--out`       | **yes**               | output JSON file path                                                               |
| `--no-github` | no                    | skip GitHub enrichment even if a token/link is present                              |

**Exit codes:** `0` success · `1` validation error (`on_missing: "error"`
field actually missing) · `2` usage error (no source files given, or all
paths invalid).

---

## Tests

```bash
pytest
```

116 tests across normalization, adapters, identity matching, merge/
survivorship, projection, validation, and full-pipeline integration. Two
fixture sets back the tests:

- **`tests/fixtures/curated/`** — a small, hand-crafted set of named
  candidates (Linus Torvalds, Dan Abramov, Sindre Sorhus, Ryan Carniato, …),
  one per scenario in `docs/scenario_map.md`. Used for exact gold-output
  assertions.

- **`sample_data/`** — the full generated 500-persona set, used for scale/
  integration assertions (e.g. "produces ≥490 profiles without crashing").

Tests tagged `@pytest.mark.github` hit the live GitHub API and are skipped
automatically when `GITHUB_TOKEN` isn't set.

---

## Repo layout

```
src/
  adapters/      source-specific parsing (csv, ats, notes, github) -> RawRecord
  normalize/     per-field normalization (emails, phones, names, skills, location)
  match/         identity matching (email -> phone tiers, union-find grouping)
  merge/         survivorship + provenance + confidence -> CanonicalRecord
  project/       runtime-config-driven projection layer
  validate/      output validation against the requested config shape
  pipeline.py    orchestrates all stages
  cli.py         entrypoint
sample_generator/  synthetic multi-source sample data generator
configs/           projection configs (default.json, custom.json)
sample_data/       generated sample inputs (csv, ats json, notes txt)
output/            committed pipeline run artifacts
tests/             unit + integration tests, curated fixtures
docs/              architecture, scenario map, design specs
```

---

## Known limitations (deliberate scope cuts)

- **No fuzzy / cross-source name matching.** Identity matching only joins
  on normalized email or phone. Two records for the same person with
  neither in common (a typo'd email, or a recruiter-notes mention with no
  contact info) are kept as **separate, lower-confidence profiles** rather
  than guessed-merged.

- No recency-based survivorship tie-breaking (sample data has no reliable
  timestamps).

- No human-review queue for low-confidence merges.

- No persistent storage — pipeline runs in-memory; CLI in, JSON out.

- No LinkedIn or resume-file parsing (out of scope per assignment — GitHub +
  CSV + ATS + notes already cover both required source-type groups).
