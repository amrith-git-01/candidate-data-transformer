# Architecture — Multi-Source Candidate Data Transformer

## 1. Goal

Turn messy, multi-source candidate data into one canonical, trustworthy JSON
profile per candidate — with every value traceable to a source and a
confidence score. Wrong-but-confident is worse than honestly-empty, so the
pipeline is built to degrade gracefully, never to invent.

## 2. Pipeline stages

```
[csv] [ats_json] [recruiter_notes.txt]
        |   |        |
        v   v        v
      ┌─────────────────┐
      │   ADAPTERS       │  raw source -> RawRecord (per source)
      └─────────────────┘
              |
              v
      ┌─────────────────┐
      │  LINK DETECTOR   │  scan all RawRecords for a github handle/URL
      └─────────────────┘
              |
              v (optional, only if link found)
      ┌─────────────────┐
      │ GITHUB ENRICHER  │  fetch profile + repos -> RawRecord (source=github)
      └─────────────────┘
              |
              v
      ┌─────────────────┐
      │   NORMALIZE      │  per-field: dates, phones, names, skills
      └─────────────────┘
              |
              v
      ┌─────────────────┐
      │  IDENTITY MATCH  │  decide which RawRecords belong to the same person
      └─────────────────┘
              |
              v
      ┌─────────────────┐
      │ MERGE/SURVIVORSHIP│ build one CanonicalRecord + provenance + confidence
      └─────────────────┘
              |
              v
      ┌─────────────────┐
      │   PROJECT        │  apply runtime config -> reshaped output
      └─────────────────┘
              |
              v
      ┌─────────────────┐
      │   VALIDATE       │  check output against requested shape
      └─────────────────┘
              |
              v
        final JSON profile
```

Each stage is a pure function taking the previous stage's output — no stage
reaches backward or sideways. This is what makes the pipeline deterministic
and explainable: same inputs always produce the same output, and every value
can be traced back through the stages that touched it.

## 3. Source adapters

| Source | Group | Notes |
|---|---|---|
| Recruiter CSV | structured | columns: name, email, phone, current_company, title |
| ATS JSON blob | structured | field names don't match canonical — adapter remaps keys |
| Recruiter notes (.txt) | unstructured | free text — heuristic extraction (regex/keyword), not NLP |
| GitHub profile | enrichment only | conditional — only runs if a github link is found in any of the 3 sources above |

Every adapter outputs the same intermediate shape, a `RawRecord`:

```
RawRecord {
  source: "csv" | "ats" | "recruiter_notes" | "github"
  fields: { field_name: { value, method } }   // method = "direct" | "extracted" | "inferred"
}
```

This intermediate shape is the contract between "messy source-specific
parsing" and "everything downstream is source-agnostic." Adapters are the
only place that know about source-specific formats.

**Why GitHub is enrichment-only, not a core source:** it's an external API,
and Engineering Required #4 from the brief says a missing/garbage source must
degrade gracefully. Making it conditional (only fetched if a link is found
elsewhere) means the pipeline never has a hard dependency on the network —
if the API is down, rate-limited, or no link exists, the pipeline still
produces a complete profile, just without that enrichment.

## 4. Link detection

A small utility scans every `RawRecord`'s text fields (and the recruiter
notes blob specifically) for a GitHub URL or `github.com/<handle>` pattern,
in this priority order: ATS blob link fields → CSV (if any link-shaped
field exists) → recruiter notes free text. First match wins; if none found,
the GitHub enrichment stage is skipped entirely and logged as skipped, not
failed.

## 5. Normalization

Applied per-field, source-agnostic:

- **Dates** → `YYYY-MM`
- **Phones** → E.164
- **Names** → trim + title-case, no invention
- **Skills** → mapped through a small canonical skill dictionary
  (e.g. "JS" → "javascript", "Golang" → "go"); unmapped skills pass through
  lowercased rather than being dropped
- **Locations** → country coerced to ISO-3166 alpha-2 where resolvable, else
  left as given

Normalization happens *before* identity matching and merge, so every record
being compared/merged is already in canonical shape — matching never has to
deal with inconsistent formats.

## 6. Identity matching

Decides which `RawRecord`s (possibly from different sources) refer to the
same candidate. Tiered, exact-match only (no fuzzy/probabilistic matching —
explicit scope cut, noted below):

1. Normalized email match (primary key)
2. Normalized phone match (fallback if email missing on either side)
3. Exact normalized full-name match (last-resort fallback, lower confidence)

The matching method used is recorded per candidate (`matched_by:
"email"|"phone"|"name"`) and feeds into `overall_confidence` — an
email-based match is trusted more than a name-only match.

**Explicit scope cut:** no fuzzy/probabilistic name matching (e.g. Jaro-Winkler,
nicknames). Real MDM systems use this for messier data; out of scope here,
documented as a clear future extension rather than silently skipped.

## 7. Merge & survivorship

Two kinds of fields, handled differently:

**Array fields** (`emails`, `phones`, `skills`) — union across all matched
sources, deduplicated after normalization. No "winner" needed; every value
that was seen is kept, each tagged with its source(s) in `skills[].sources`
or `provenance[]`.

**Scalar fields** (`full_name`, `current_company`/title→`experience`,
`headline`) — survivorship by source-trust order, decided per field, not
per record:

| Field | Trust order |
|---|---|
| full_name | csv → ats → recruiter_notes |
| company / title (→ experience) | csv → ats |
| headline | recruiter_notes (extracted) → github bio (fallback) |
| education | ats → null |
| years_experience | ats → recruiter_notes (extracted) → null |

If the top-trust source is missing the field, fall through to the next —
this is fallback, not blind precedence: every source gets a chance, highest
trust wins only when it actually has a value.

**Explicit scope cut:** no recency-based tie-breaking (no reliable
timestamps in sample data) and no human-review queue for low-confidence
merges — static trust order stands in for both, noted as the production
extension point.

Every value in the output carries a `provenance` entry: `{ field, source,
method }`. Nothing is overwritten silently — if CSV and ATS disagree on
title, both are visible in provenance even though only one "wins" into the
canonical field.

## 8. Confidence scoring

`overall_confidence` and per-skill confidence are computed from:

- match-tier used (email > phone > name)
- source trust weight of whichever source supplied the value
- agreement bonus: +weight if 2+ sources independently agree on the same
  normalized value

Deterministic formula, no ML — same inputs always produce the same score.

## 9. Configurable projection layer

The canonical record (internal, full, never touched by config) is kept
strictly separate from the **projection layer**, which is the only thing
that reads the runtime config. The projector:

1. Walks `config.fields[]`
2. For each entry, resolves `from` (a path into the canonical record) or
   defaults to `path` if `from` is omitted
3. Applies `normalize` if specified (re-normalizes from canonical form into
   the requested shape, e.g. canonical skills → a different skill format)
4. Applies `on_missing` (`null` | `omit` | `error`) if the resolved value is
   absent
5. Toggles `provenance`/`confidence` inclusion per the config flags

This separation means the engine never changes for a new config — only the
projection step's interpretation of `fields[]` changes. New output shapes
are a config change, not a code change.

## 10. Validation

After projection, the output is checked against the *requested* config
shape (not the internal canonical schema) — required fields present,
types match, `on_missing: "error"` fields actually fail loudly rather than
silently passing through as null.

## 11. Edge cases handled

- Missing source entirely → that adapter is skipped, logged, doesn't crash
  the run; confidence reflects fewer corroborating sources
- Malformed CSV row / unparseable ATS JSON → skip the row/record, log it,
  continue
- Conflicting values across sources for the same scalar field → survivorship
  rule decides; both values remain visible in `provenance`
- GitHub link not found anywhere → enrichment stage skipped silently, rest
  of pipeline unaffected
- GitHub API failure (404 / rate limit) → enrichment fails soft, logged,
  confidence for github-sourced fields unaffected since they're just absent
- Identity match falls through to name-only → lower confidence, flagged via
  `matched_by`
- Config requests a field not present in canonical record → `on_missing`
  rule decides (null/omit/error)
- Empty skills / no repos from GitHub → empty array, never a crash

## 12. What's explicitly out of scope (by design, not oversight)

- Fuzzy/probabilistic identity matching (nicknames, name variants)
- Recency-based survivorship (sample data lacks reliable timestamps)
- Human-review queue for low-confidence merges
- Persistent storage — pipeline runs in-memory, CLI in, JSON out
- UI — CLI only, by the assignment's own stated priority

## 13. Repo layout

```
src/
  schema/        canonical record + config schema definitions
  normalize/     per-field normalization utilities
  adapters/
    csv_adapter.py
    ats_adapter.py
    recruiter_notes_adapter.py
    github_adapter.py
    link_detector.py
  match/         identity matching (email/phone/name tiers)
  merge/         survivorship + provenance + confidence
  project/        config-driven projection layer
  validate/       output validation against requested config shape
  cli/            entrypoint
tests/
sample_data/
README.md
design_doc.pdf
architecture.md
```
