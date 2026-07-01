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
- [Web UI](#web-ui)
  - [Tech stack](#tech-stack)
  - [Pages (routes)](#pages-routes)
  - [Interactive projection config](#interactive-projection-config)
  - [API reference](#api-reference)
  - [Running it](#running-it)
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
    VALIDATE --> OUT["JSON output: profiles array"]
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
    CFG["ProjectionConfig (json)\nfields list, include_confidence,\ninclude_provenance, on_missing"] --> PROJ
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
git clone https://github.com/amrith-git-01/candidate-data-transformer.git
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

GitHub enrichment (`src/adapters/github_adapter.py`) calls two public,
unauthenticated-capable endpoints — `GET /users/:handle` and
`GET /users/:handle/repos` — to pull a candidate's name/bio/location and the
languages of their most recently updated repos. A token is **not required**
to use this feature at all; it only raises how many requests you're allowed
per hour before GitHub starts rejecting them.

### Steps

1. Go to **github.com → Settings → Developer settings → Personal access
   tokens → Tokens (classic)** (or [this direct link](https://github.com/settings/tokens)).

2. Click **Generate new token (classic)**.

3. Give it any name (e.g. `candidate-transformer-demo`) and pick an
   expiration. **Leave every scope checkbox unchecked** — this project only
   reads public profile data, which needs no scopes at all.

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

   `.env` is gitignored — it's never committed. Both the CLI (via
   `src/env.py::load_project_env`) and the web UI backend load it
   automatically on startup; no other config is needed.

### What happens if you enable enrichment _without_ a token

Nothing breaks — it degrades gracefully, by design:

- **Rate limit is just lower.** Unauthenticated requests are capped at
  **60/hour per IP** (vs. **5,000/hour** with a token). Fine for a handful
  of candidates or a quick demo; you'll run out partway through a full
  500-persona batch (each enriched candidate costs 2 requests).
- **No crash, no partial corruption.** `fetch_github_record()` wraps both
  GitHub calls in a `try/except httpx.HTTPError`. Once you're rate-limited,
  GitHub returns `403`, `raise_for_status()` raises, the exception is caught,
  a warning is logged, and the function returns `None`.
- **Pipeline just treats it like a missing source.** Back in
  `pipeline.py::_enrich_group_with_github`, a `None` result means that
  candidate's group is returned unchanged — merge/projection carry on with
  whatever CSV/ATS/notes data that candidate already had. You still get a
  complete result set; the candidates that got rate-limited simply won't
  have any GitHub-sourced fields (or provenance entries) merged in.
- **In the web UI**, this is the "Enrich with GitHub" checkbox on the Run
  Pipeline page — ticking it with no `GITHUB_TOKEN` set behaves exactly the
  same way: it'll enrich as many candidates as the unauthenticated budget
  allows, then silently stop enriching (not erroring) for the rest. Check
  the backend terminal/log output for the `GitHub API error` warnings if you
  want to see exactly where it started getting rate-limited.

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

## Web UI

A FastAPI + React add-on wraps the same pipeline in a browser UI — useful
for demoing without the CLI. It never re-implements pipeline logic: the
backend is a thin layer that calls `src.pipeline.run_pipeline` and
`sample_generator.orchestrator.generate` in-process, the same functions the
CLI calls. There is **no database** — it reads/writes the same files the
CLI uses (`sample_data/`, `configs/`), plus one extra artifact
(`output/webapp_run.json`) for its own last run.

```mermaid
flowchart LR
    subgraph Browser
        UI["React 19 SPA\n(Vite + Tailwind v4)"]
    end

    subgraph Server["FastAPI backend (port 8000)"]
        R1["/api/sample/*\nsample router"]
        R2["/api/configs/*\nconfigs router"]
        R3["/api/run\nrun router"]
        SVC1["sample_service"]
        SVC2["pipeline_service"]
    end

    UI -- "fetch /api/* (Vite dev proxy)" --> R1 & R2 & R3
    R1 --> SVC1
    R3 --> SVC2
    SVC1 -->|"writes"| SD["sample_data/*.csv .json .txt"]
    SVC1 -->|"reads back for preview"| SD
    R2 -->|"reads"| CFG["configs/*.json"]
    SVC2 -->|"calls in-process"| PIPE["src.pipeline.run_pipeline"]
    SVC2 -->|"writes"| RUN["output/webapp_run.json"]
    PIPE -->|"reads"| SD
```

### Tech stack

| Layer    | Choices                                                                                                                                                                                                                                                    |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend  | FastAPI, layered as `routers/` (HTTP) → `services/` (logic) → `schemas/` (Pydantic request/response models); CORS opened for the Vite dev origin only                                                                                                      |
| Frontend | React 19 + Vite, **React Router** for real per-page URLs, **React Query** (`@tanstack/react-query`) for all server state (caching, loading/error states, mutations), Tailwind CSS v4 for styling, `lucide-react` for icons, `clsx` for conditional classes |

### Pages (routes)

The SPA uses `react-router-dom`'s `BrowserRouter` — each tab is a real
route with its own URL, so the browser back/forward buttons work and a
page refresh lands you back where you were (`/` redirects to `/sample`):

```mermaid
flowchart LR
    ROOT["/"] -->|redirect| SAMPLE["/sample\nSample Data"]
    SAMPLE -.->|nav| RUN["/run\nRun Pipeline"]
    RUN -.->|nav| RESULTS["/results\nResults"]
    RESULTS -.->|nav| SAMPLE
    ANY["any unknown path"] -->|redirect| SAMPLE
```

- **`/sample` — Sample Data.** Generate a fresh synthetic dataset (persona
  count + seed) via `sample_generator`, see the manifest stats (rows
  written per source, real vs. fake GitHub handles), and page through the
  raw rows of each of the three generated source files.

- **`/run` — Run Pipeline.** Build a `ProjectionConfig` with **interactive
  controls — no JSON editing** — then run the pipeline in-process and see
  how many canonical profiles came out. See
  [Interactive projection config](#interactive-projection-config) below.

- **`/results` — Results.** Paginated table of every canonical profile
  from the most recent run (`output/webapp_run.json`), with columns for
  contact info, location, skills, experience, education, links, match
  tier, and confidence — adapting automatically to either the full
  canonical schema or a flattened custom projection.

### Interactive projection config

The same `ProjectionConfig` the CLI takes via `--config` is built entirely
through UI controls on `/run`, mapped 1:1 onto the Pydantic model in
`src/models.py`:

| Control                                                                                                                  | `ProjectionConfig` field                   |
| ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ |
| Segmented control — _Canonical schema_ / _Custom fields_                                                                 | `use_canonical_schema`                     |
| Field-row builder (add/remove; output path, source path, type, normalize, required) — only shown in _Custom fields_ mode | `fields[]` (each row is a `FieldSpec`)     |
| Toggle switches — _include confidence_, _include provenance_                                                             | `include_confidence`, `include_provenance` |
| Segmented control — _Null / Omit / Error_                                                                                | `on_missing`                               |

A **preset selector** (`ConfigSelector`) seeds the form from any file in
`configs/` (`default.json`, `custom.json`) as a starting point, which
you're then free to tweak interactively. A collapsible, read-only JSON
preview at the bottom shows the exact payload that will be POSTed —
useful for sanity-checking without ever hand-editing JSON.

```mermaid
sequenceDiagram
    participant U as User
    participant F as Form state (React)
    participant B as FieldsBuilder / Toggle / SegmentedControl
    participant API as POST /api/run

    U->>F: pick preset (ConfigSelector)
    F->>API: GET /api/configs/{name}
    API-->>F: raw config JSON
    F->>F: merge onto ProjectionConfig field defaults
    U->>B: toggle schema mode / add-edit-remove field rows / flip switches
    B->>F: patch config state
    U->>API: click "Run pipeline"
    F->>API: POST { config, enrich_github }
    API-->>F: { profile_count, wrote_to }
```

### API reference

| Method | Path                   | Purpose                                                                                                                     |
| ------ | ---------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `POST` | `/api/sample/generate` | Generate a fresh sample dataset (`{ count, seed }`), returns the manifest                                                   |
| `GET`  | `/api/sample/{source}` | Paginated raw rows for `source` = `csv` \| `ats` \| `notes`                                                                 |
| `GET`  | `/api/configs`         | List available config presets (filenames under `configs/`, no extension)                                                    |
| `GET`  | `/api/configs/{name}`  | Raw JSON contents of one config preset                                                                                      |
| `POST` | `/api/run`             | Run the pipeline (`{ config, enrich_github }`), persists to `output/webapp_run.json`, returns `{ profile_count, wrote_to }` |
| `GET`  | `/api/run/results`     | Paginated canonical profiles from the latest run                                                                            |
| `GET`  | `/api/health`          | Liveness check                                                                                                              |

### Running it

Backend (from repo root, same venv as the CLI):

```bash
pip install -r webapp/backend/requirements.txt
python -m uvicorn app.main:app --app-dir webapp/backend --port 8000
```

Frontend (separate terminal):

```bash
cd webapp/frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite's dev server proxies `/api/*` to the
backend on port 8000 (see `webapp/frontend/vite.config.js`) and serves
`index.html` for every client-side route, so no CORS setup is needed
beyond what's already configured and deep-linking/refreshing `/run` or
`/results` works out of the box.

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
webapp/
  backend/
    app/
      routers/     HTTP layer: sample.py, configs.py, run.py
      services/    logic: sample_service.py, pipeline_service.py
      schemas/     Pydantic request/response models
      core/        config.py (paths to sample_data/, configs/, output/)
      main.py      FastAPI app, CORS, router registration
  frontend/
    src/
      api/         client.js (fetch wrapper), queries.js (React Query hooks)
      components/  generic UI: Card, Table, Tabs, NavTabs, Toggle,
                   SegmentedControl, ConfigSelector, Pagination, Badge, ...
      features/    per-page logic: sampleData/, runPipeline/, results/
      App.jsx      route definitions (react-router-dom)
      main.jsx     QueryClientProvider + BrowserRouter root
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
