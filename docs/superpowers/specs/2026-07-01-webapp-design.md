# Web UI Add-On — Design Spec

**Date:** 2026-07-01
**Status:** Approved
**Goal:** A minimal, professional frontend + backend that wraps the existing CLI pipeline for demo purposes. This is an **add-on**, not a replacement — the CLI remains the primary submission artifact; this just makes it easier to click through in a demo.

---

## 1. Scope

**In scope:**

- Trigger sample-data (re)generation from the UI.
- Preview raw sample source files (CSV / ATS JSON / notes) as paginated read-only tables.
- Run the pipeline with a chosen config (default / custom / hand-edited JSON) and a GitHub-enrichment toggle.
- View the resulting profiles as a paginated table.

**Out of scope (explicit, time-boxed):**

- No auth, no user accounts, no sessions.
- No database — state is the same files the CLI already reads/writes (`sample_data/`, `configs/`, `output/`).
- No automated tests for the webapp layer (manual click-through verification only). Existing `pytest` suite for `src/`/`sample_generator/` is untouched and unaffected.
- No row-level detail/expand view, no in-place editing of sample data, no streaming/websocket progress (a run either completes and returns, or the request errors).
- No changes whatsoever to `src/`, `sample_generator/`, or existing tests — the webapp only _imports and calls_ that code.

---

## 2. Architecture

```
webapp/backend/   FastAPI, layered (routers -> services -> existing src.pipeline / sample_generator)
webapp/frontend/  Vite + React + Tailwind, componentized, single page, 3 tabs
```

Backend calls `src.pipeline.run_pipeline()` and `sample_generator.orchestrator.generate()` **in-process** — no subprocess/CLI shelling. This is safe (existing code is read-only from the webapp's perspective — the webapp never edits pipeline source), fast, and avoids parsing subprocess stdout.

Persistence = existing file conventions, nothing new:

- Sample data lives in `sample_data/` (same files the CLI uses).
- A webapp-triggered run writes to `output/webapp_run.json` (distinct from `output/default_profiles.json` / `output/custom_profiles.json` so it never overwrites the committed CLI artifacts).
- Results endpoint reads that file back. Restart-safe — no in-memory global state.

### Backend layout

```
webapp/backend/
  app/
    main.py                # FastAPI() app, CORS (allow the Vite dev origin), mounts routers
    core/
      config.py            # PROJECT_ROOT, SAMPLE_DATA_DIR, CONFIGS_DIR, OUTPUT_DIR constants
    schemas/
      sample.py            # GenerateSampleRequest, PaginatedRows response model
      run.py                # RunRequest {config: dict, enrich_github: bool}, PaginatedProfiles
    services/
      sample_service.py    # generate_sample(count, seed); read_source_page(source, page, page_size)
      pipeline_service.py  # run_and_persist(config_dict, enrich_github) -> writes webapp_run.json
                            # read_latest_run(page, page_size) -> reads it back
    routers/
      sample.py             # GET/POST /api/sample-data/*
      configs.py            # GET /api/configs
      run.py                 # POST /api/run, GET /api/run/latest
  requirements.txt          # fastapi, uvicorn[standard], python-multipart
```

### Backend endpoints

| Method | Path                        | Body / Query                                             | Returns                                               |
| ------ | --------------------------- | -------------------------------------------------------- | ----------------------------------------------------- |
| POST   | `/api/sample-data/generate` | `{count, seed}`                                          | manifest (same shape as `sample_data/manifest.json`)  |
| GET    | `/api/sample-data/{source}` | `?page=&page_size=` (`source` = `csv`\|`ats`\|`notes`)   | `{rows, total, page, page_size}`                      |
| GET    | `/api/configs`              | —                                                        | `{default: {...}, custom: {...}}` (raw JSON contents) |
| POST   | `/api/run`                  | `{config: <ProjectionConfig json>, enrich_github: bool}` | `{profile_count, wrote_to}`                           |
| GET    | `/api/run/latest`           | `?page=&page_size=`                                      | `{profiles, total, page, page_size}`                  |

Row-level parsing for the sample-data preview reuses the existing adapters where possible (`src.adapters.csv_adapter`, etc.) is **not** used directly for preview (those return `RawRecord`, not display-friendly rows) — `sample_service.py` does its own lightweight raw parse (csv.DictReader rows, ATS `candidates[]` entries, notes sections split the same way the adapter does) purely for **display**, kept separate from the real adapters so a display bug can never affect pipeline correctness.

`POST /api/run` validates the incoming `config` dict via `ProjectionConfig.model_validate()` (same Pydantic model the CLI uses) before calling `run_pipeline()` — a malformed hand-edited config returns `422` with Pydantic's validation error, not a 500.

### Frontend layout

```
webapp/frontend/
  src/
    api/client.js                 # fetch wrapper: base URL, JSON parsing, error normalization
    components/
      Tabs.jsx                    # tab bar + active-tab switch, generic
      Table.jsx                   # generic paginated table (columns config + rows)
      Pagination.jsx              # page controls, used by Table
      ConfidenceBadge.jsx          # colored pill: green >=0.8, amber >=0.5, gray below
      JsonEditor.jsx               # textarea + live JSON.parse validation + error display
      Spinner.jsx                  # loading indicator
    features/
      sampleData/SampleDataTab.jsx # source sub-tabs (CSV/ATS/Notes) + regenerate form
      runPipeline/RunPipelineTab.jsx # config dropdown -> JsonEditor, github toggle, run button
      results/ResultsTab.jsx       # paginated results table using Table + ConfidenceBadge
    App.jsx                       # top-level layout, Tabs, renders active feature
    main.jsx
  tailwind.config.js / postcss.config.js / index.html / package.json / vite.config.js
```

Plain JS (no TypeScript) to keep the build fast — folder structure (not types) is what keeps this maintainable. Tailwind via standard Vite+PostCSS setup, one shared accent palette (navy `#13294B` / accent blue `#2f5fa8` / green `#2f7d4f`) matching the README/design-PDF branding already established, so the whole submission looks like one coherent product.

---

## 3. Data flow (a single "Run Pipeline" click)

1. User picks "Default" or "Custom" in `RunPipelineTab` → frontend calls `GET /api/configs`, prefills `JsonEditor` with that config's JSON.
2. User optionally edits the JSON, toggles GitHub enrichment, clicks Run.
3. Frontend `JSON.parse`s the editor content client-side first (fast-fail on typos) → `POST /api/run`.
4. Backend: `ProjectionConfig.model_validate(body.config)` → `run_pipeline(csv_path=..., ats_path=..., notes_path=..., config=parsed, enrich_github=body.enrich_github)` (same three `sample_data/` paths every time) → writes `output/webapp_run.json`.
5. Frontend switches to Results tab, calls `GET /api/run/latest?page=1`, renders table.

---

## 4. Error handling

- Backend: Pydantic validation errors → `422` with field-level detail. Missing/unreadable sample files → `500` with a clear message (shouldn't happen since `sample_data/` is committed, but not swallowed silently).
- Frontend: every API call wrapped in try/catch in `api/client.js`; failures render an inline error banner in the active tab, never a blank screen or unhandled console error.

## 5. Testing

Manual click-through only, per the time-box: generate sample → preview all 3 sources → run default → view results → run custom with edited JSON → view reshaped results → run with an intentionally broken JSON (missing comma) → confirm inline error, no crash.
