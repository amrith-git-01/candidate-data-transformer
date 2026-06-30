# Sample Data Generator — Design Spec

**Date:** 2026-06-30  
**Status:** Approved  
**Goal:** Multi-file `sample_generator/` module that produces rich, deterministic sample inputs (CSV, ATS JSON, recruiter notes) at scale (1000+ personas), with probabilistic edge-case scenarios embedded randomly — overwriting `sample_data/` on demand.

---

## 1. Problem & success criteria

The pipeline needs realistic, messy, multi-source inputs that stress merge, identity matching, normalization, and GitHub enrichment without hand-authoring thousands of rows.

**Success criteria:**

- `python -m sample_generator --count 1000 --seed 42` overwrites `sample_data/` with three adapter-compatible files
- Same seed → byte-identical output (deterministic)
- Rich field coverage aligned with canonical schema inputs (location, education, skills, links, headlines)
- Edge-case **behaviors** (not fixed celebrity names) appear probabilistically across the population
- Existing adapters + pipeline run without crash on generated output
- Generator is isolated from `src/` pipeline runtime (dev tool)

---

## 2. Decisions (brainstorming outcomes)

| Decision           | Choice                                                                                        |
| ------------------ | --------------------------------------------------------------------------------------------- |
| Architecture       | Hybrid: persona factory + scenario decorators + per-source writers                            |
| Scale              | Default 1000 unique personas; configurable via `--count`                                      |
| Richness           | High — most personas have email, phone, location, education, skills, headline                 |
| GitHub             | Sparse natural distribution: empty (majority), small % real handles, small % fake 404 handles |
| Output             | Overwrite `--out` directory (default `sample_data/`)                                          |
| Scenarios          | Random personas with probabilistic scenario tags (no pinned Linus/Dan rows)                   |
| Scenario guarantee | Probabilistic only — not every run contains all 10 types                                      |
| Determinism        | Seeded `random.Random` throughout                                                             |
| Repo commits       | Do not commit 1000-row fixtures by default; document `--count 100` for repo smoke             |

---

## 3. Module layout

```
sample_generator/
  __init__.py
  __main__.py              # python -m sample_generator
  cli.py                   # argparse entrypoint
  config.py                # weights, rates, real GitHub handle pool
  models.py                # Persona, SourceAssignment, GenerationManifest
  personas.py              # Faker-based persona factory
  scenarios/
    __init__.py
    registry.py            # tag → apply(persona, assignment) -> mutations
    mutators.py            # shared mutation helpers (typo email, strip field, etc.)
  writers/
    __init__.py
    csv_writer.py
    ats_writer.py
    notes_writer.py
  orchestrator.py          # roll personas, assign scenarios, invoke writers
```

**Package boundary:** `sample_generator` imports **nothing** from `src.adapters` at generation time. Optional test-only import to validate round-trip.

**Optional pyproject entry:**

```toml
[project.scripts]
generate-samples = "sample_generator.cli:main"

[project.optional-dependencies]
generate = ["Faker>=24.0"]
```

---

## 4. Core data models

### 4.1 `Persona`

Single logical candidate before source projection.

```python
@dataclass
class Persona:
    person_id: str              # slug, stable cross-source key
    full_name: str
    email: str | None
    phone: str | None           # raw; writers may format differently per source
    company: str
    title: str
    city: str | None
    region: str | None
    country: str | None         # mixed forms: US, USA, United States (normalizer handles)
    linkedin_url: str | None
    github_handle: str | None    # None | real public handle | fake nonexistent handle
    headline: str | None
    years_experience: int | None
    skills: list[str]           # canonical-ish skill names
    education: list[dict]       # {institution, degree, field, end_year}
    notes_template: str | None    # base prose; scenarios may override
```

### 4.2 `SourceAssignment`

Links persona to sources and scenario mutations.

```python
@dataclass
class SourceAssignment:
    persona: Persona
    scenario_tags: list[str]    # max 2 tags per persona
    in_csv: bool
    in_ats: bool
    in_notes: bool
    csv_row_extra: int          # 0 or 1 for duplicate row
    csv_overrides: dict[str, Any]
    ats_overrides: dict[str, Any]
    notes_overrides: dict[str, Any]
```

### 4.3 `GenerationManifest`

Written to `{out}/manifest.json` for reproducibility debugging.

```python
@dataclass
class GenerationManifest:
    seed: int
    count: int
    generated_at: str           # ISO timestamp
    scenario_histogram: dict[str, int]
    source_counts: dict[str, int]  # csv_rows, ats_candidates, notes_sections
    github_stats: dict[str, int]   # empty, real, fake
```

---

## 5. Persona factory (`personas.py`)

Uses `Faker` with locale `en_US` + seeded instance.

**Per persona (baseline before scenarios):**

| Field              | Generation rule                                                                    |
| ------------------ | ---------------------------------------------------------------------------------- |
| `full_name`        | `faker.name()`                                                                     |
| `email`            | `{first}.{last}@example.com` lowercased                                            |
| `phone`            | US-style `+1-XXX-555-XXXX` (valid for phonenumbers)                                |
| `company`          | `faker.company()`                                                                  |
| `title`            | Random from title pool (Engineer, Senior Engineer, Staff SWE, etc.)                |
| `location`         | city, region, country from Faker + manual country variety                          |
| `skills`           | 3–8 picks from shared skill pool (overlap with `src/normalize/skills.py` taxonomy) |
| `education`        | 0–2 entries, institution/degree/field/end_year                                     |
| `headline`         | 70% chance, short role summary                                                     |
| `years_experience` | 1–25, consistent with notes text                                                   |
| `linkedin_url`     | 70% chance if email present                                                        |
| `github_handle`    | See §7                                                                             |
| `notes_template`   | 60% chance; 2–4 sentences mentioning skills + years                                |

**Source presence (baseline, before scenario tags):**

- `in_csv`: 85%
- `in_ats`: 80%
- `in_notes`: 60%

Scenarios override presence (e.g. `csv_only`, `notes_only`).

---

## 6. Scenario system (probabilistic)

### 6.1 Registry

Each scenario tag maps to a function:

```python
def apply_tag(tag: str, assignment: SourceAssignment) -> None:
    ...
```

Mutators set `*_overrides` and flip `in_csv` / `in_ats` / `in_notes`.

### 6.2 Tags and weights

Rolled per persona after baseline. **Max 2 tags** per persona.

| Tag                | Weight    | Behavior                                                          |
| ------------------ | --------- | ----------------------------------------------------------------- |
| `happy_path`       | 0.40      | Force all three sources; aligned fields                           |
| `title_conflict`   | 0.08      | `csv_overrides.title` ≠ ATS `job_title`                           |
| `email_typo`       | 0.05      | ATS email typo vs CSV (name-match path)                           |
| `phone_join`       | 0.05      | CSV has email only; ATS has phone only (same name)                |
| `csv_only`         | 0.06      | `in_ats=False`, `in_notes=False`                                  |
| `ats_notes_only`   | 0.05      | `in_csv=False`                                                    |
| `notes_only`       | 0.04      | only `in_notes=True`                                              |
| `glitch_email`     | 0.02      | ATS `contact_email="not-an-email"` (adapter skips)                |
| `github_text_only` | 0.03      | strip ATS `github_url`; embed `github.com/{handle}` in notes only |
| `github_404`       | 0.02      | fake handle `jane-doe-nonexistent-handle-{id}`                    |
| `csv_duplicate`    | 0.03      | `csv_row_extra=1` identical duplicate row                         |
| _(none)_           | remainder | baseline presence only                                            |

Weights configurable in `config.py`. Roll order: primary tag, then 15% chance of secondary compatible tag.

**Compatibility rule:** secondary tag must not contradict primary (e.g. `notes_only` + `csv_only` forbidden).

### 6.3 Real GitHub handle pool

Small static list of public accounts for enrichment demos (e.g. `torvalds`, `gaearon`, `sindresorhus`, `yyx990803`, `ryansolid`, `sdras`). Used only when persona assigned a real handle (~3% baseline, scenarios may add).

---

## 7. GitHub distribution

Applied at persona creation (before scenarios):

| Bucket          | Default rate | Result                              |
| --------------- | ------------ | ----------------------------------- |
| No GitHub       | ~85%         | `github_handle=None`, no URL fields |
| Real handle     | ~3%          | pick from pool                      |
| Fake handle     | ~2%          | `nonexistent-handle-{uuid}`         |
| Scenario-driven | tags above   | may override                        |

ATS `github_url` set only when handle present and not `github_text_only`. Notes may embed handle in prose per scenario.

---

## 8. Writers

### 8.1 CSV (`recruiter_export.csv`)

Header:

```
name,email,phone,current_company,title,city,region,country,linkedin_url
```

- One row per `in_csv` assignment
- `csv_duplicate` emits second identical row
- Scenario overrides applied per row
- No `github_url` column (matches current adapter)

### 8.2 ATS (`ats_export.json`)

```json
{ "candidates": [ ... ] }
```

Field names match current adapter expectations:

- `candidate_name`, `contact_email`, `contact_phone`, `employer`, `job_title`
- `headline`, `github_url`, `linkedin_url`
- `location`: `{city, region, country}`
- `education`: `[{institution, degree, field, end_year}]`

`glitch_email` sets invalid email; row still emitted (adapter skips).

### 8.3 Notes (`recruiter_notes.txt`)

Format:

```
=== Candidate: {full_name} ===
{body paragraph(s)}
```

Body includes:

- years experience phrase
- skill keywords (for extractor)
- optional location phrase (`Based in City, Region, Country`)
- optional `github.com/{handle}` inline without scheme
- optional education mention

Only personas with `in_notes=True`.

---

## 9. Orchestrator flow

```
1. Parse CLI args (count, seed, out, rates)
2. Initialize Faker + Random(seed)
3. For i in range(count):
     a. persona = build_persona(rng, faker)
     b. assignment = baseline_source_presence(persona, rng)
     c. roll_scenario_tags(assignment, rng)
     d. apply each tag via registry
     e. append assignment to list
4. writers.csv_writer.write(assignments, out/recruiter_export.csv)
5. writers.ats_writer.write(assignments, out/ats_export.json)
6. writers.notes_writer.write(assignments, out/recruiter_notes.txt)
7. Write manifest.json
8. Log summary counts
```

**`--count` semantics:** number of unique personas generated. Physical row/section counts vary by source presence.

---

## 10. CLI

```bash
python -m sample_generator --count 1000 --seed 42 --out sample_data
```

| Flag                 | Default       | Description                    |
| -------------------- | ------------- | ------------------------------ |
| `--count`            | 1000          | Unique personas                |
| `--seed`             | 42            | RNG seed                       |
| `--out`              | `sample_data` | Output directory (overwritten) |
| `--github-real-rate` | 0.03          | Override real handle rate      |
| `--github-fake-rate` | 0.02          | Override fake handle rate      |
| `--yes`              | false         | Skip overwrite confirmation    |

Prompt before overwrite unless `--yes`:

```
About to overwrite sample_data/ (3 files + manifest). Continue? [y/N]
```

---

## 11. Testing strategy

| Test file                                    | Coverage                                             |
| -------------------------------------------- | ---------------------------------------------------- |
| `tests/test_sample_generator_determinism.py` | Same seed → identical file hash                      |
| `tests/test_sample_generator_adapters.py`    | Parse 100-count output with `src.adapters`           |
| `tests/test_sample_generator_pipeline.py`    | `run_pipeline` on 100-count, `--no-github`, no crash |
| `tests/test_sample_generator_scenarios.py`   | Unit tests per scenario mutator                      |

**CI default:** generate `--count 50 --seed 1` to temp dir (do not overwrite committed `sample_data/` in CI unless explicitly requested).

---

## 12. Out of scope

- Generating canonical output JSON (pipeline's job)
- LinkedIn scraping or resume PDF/DOCX generation
- Guaranteeing all 10 scenario types per run
- GraphQL GitHub API (REST only in pipeline)
- Committing 1000-row fixtures to git

---

## 13. Relationship to existing `docs/scenario_map.md`

`scenario_map.md` documents **behavioral archetypes** the generator implements as tags. After generator lands:

- Update `scenario_map.md` to reference probabilistic tags + `manifest.json` histogram
- Keep small hand-run checklist for demo video (run pipeline, inspect manifest for tag hits)

---

## 14. Implementation order

1. `models.py`, `config.py`, `personas.py`
2. `scenarios/registry.py` + mutators
3. Writers (csv, ats, notes)
4. `orchestrator.py` + `cli.py`
5. Tests (determinism → adapters → pipeline)
6. README section for generator usage

---

## Spec self-review

- [x] No TBD placeholders
- [x] Consistent with existing adapter field names (verified against `csv_adapter`, `ats_adapter`, `notes_adapter`)
- [x] Scope bounded to generator module + tests
- [x] Probabilistic scenarios explicit; no contradiction with user request for random embedding
- [x] GitHub sparse policy documented
- [x] Overwrite `sample_data/` documented with confirmation flag
