# Sample Data — Scenario Map

This maps each scenario to where it actually lives. There are **two
distinct datasets**, used for different purposes:

| Dataset               | Location                   | Purpose                                                                                                                                                                                                                       |
| --------------------- | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Curated fixtures      | `tests/fixtures/curated/`  | Small, hand-crafted, deterministic. One named candidate per scenario below. Used for exact gold-output assertions in `tests/`.                                                                                                |
| Generated sample data | `sample_data/` (committed) | 500 synthetic personas from `sample_generator/`, built to hit the same scenario _categories_ at scale (see `manifest.json`'s `scenario_histogram`). Used for the actual CLI demo run and committed `output/*.json` artifacts. |

The named people below (Linus Torvalds, Dan Abramov, etc.) exist only in
`tests/fixtures/curated/`, not in `sample_data/`. Don't go looking for
"Linus Torvalds" in the 500-persona `sample_data/recruiter_export.csv` —
he's not there; the generated set is anonymized/randomized so the pipeline
is demonstrably scale-tested, not just hand-tuned for 10 named people.

Three curated files, designed together so the same candidates recur across
sources with deliberate conflicts/gaps. Use this as your test/demo
checklist.

| File                   | Role                                                 |
| ---------------------- | ---------------------------------------------------- |
| `recruiter_export.csv` | structured source — recruiter CSV                    |
| `ats_export.json`      | structured source — ATS blob, different field names  |
| `recruiter_notes.txt`  | unstructured source — free text, multiple candidates |

## Scenario coverage

1. **Happy path — Linus Torvalds**
   In CSV + ATS + has a real github link in ATS (`torvalds`). All sources
   agree on company/title. Should merge cleanly, high confidence, full
   GitHub enrichment (real account, will return data).

2. **Conflicting scalar field — Dan Abramov**
   CSV says title = "Engineer", ATS says "Staff Software Engineer". Tests
   survivorship trust order (CSV should win per the architecture's trust
   table — verify your output reflects that, and both values show up in
   `provenance`). Real github (`gaearon`).

3. **Missing email, phone-fallback join — Sindre Sorhus**
   CSV has email but no phone; ATS has phone but `contact_email: null`.
   Tests that identity matching falls through email → phone correctly.
   Real github (`sindresorhus`).

4. **Missing source entirely — Addy Osmani**
   Present in CSV only. Not in ATS, not in recruiter notes, no github link
   anywhere. Tests graceful degrade — profile should still build from CSV
   alone with lower confidence, no crash.

5. **Unstructured-only candidate — Evan You**
   Present in ATS + recruiter notes, but NOT in the CSV. Tests merge when
   the "primary" structured source is missing for a candidate but other
   sources still resolve identity (via email match ATS↔notes-extracted, or
   name fallback if notes don't carry email). Real github (`yyx990803`).

6. **Malformed record — "Glitch Entry" in ats_export.json**
   `contact_email: "not-an-email"` (invalid format), `job_title: null`, no
   phone, no github. Tests that normalization/validation rejects or nulls
   the bad email rather than crashing, and the record either still produces
   a degraded profile or is skipped+logged — your call, just don't let it
   kill the run.

7. **GitHub link only in free text — Sarah Drasner**
   Not in CSV or ATS at all — only exists in `recruiter_notes.txt`, where
   her github link is embedded mid-sentence (`github.com/sdras`, no
   `https://` prefix). Tests the link-detector's regex against an
   unstructured, lower-priority source and that it still triggers
   enrichment. Real github account.

8. **GitHub 404 — Jane Doe**
   Only in recruiter notes. The github handle mentioned
   (`jane-doe-nonexistent-handle-12345`) does not exist. Tests that the
   GitHub adapter fails soft — logs it, sets no enrichment fields, doesn't
   crash, doesn't lower confidence on unrelated fields.

9. **Email-typo, no cross-source join — Ryan Carniato**
   Email differs between CSV (`ryan.carniato@example.com`) and ATS
   (`ryan.carniatto@example.com` — typo'd domain/local-part on purpose).
   Phones also differ slightly. By design, identity matching does **not**
   fall through to a name-based join across sources (see
   `architecture.md` §6 — exact-name cross-source joins are an explicit
   scope cut to avoid false merges on common names). Result: **two
   separate, lower-confidence profiles**, both named "Ryan Carniato" — this
   is the expected, tested behavior (`test_email_typo_stays_separate_groups`
   in `tests/test_match.py`), not a bug. `matched_by` on each singleton just
   reflects its own best available key (`"email"`), not a cross-source
   join. Real github (`ryansolid`) on the CSV-sourced one only.

10. **Within-source duplicate — Linus Torvalds (again)**
    Appears twice, identically, in `recruiter_export.csv`. Tests that your
    CSV adapter (or the merge stage) dedupes within a single source instead
    of producing two separate candidate records that then awkwardly
    "merge" into themselves.

## Testing a fully garbage/unreadable source (file-level, not row-level)

Not baked into the files above on purpose — easiest to test by pointing the
CLI at a non-existent path, or a truncated/corrupted copy of
`ats_export.json` (e.g. `ats_export.json` with the closing `]}` stripped).
Make this one of your CLI demo runs / test cases rather than a permanent
sample file, since the assignment cares that you handle it, not that it
lives in the fixture set.

## Suggested test/demo split

- **Default config run**: all 10 scenarios above, full pipeline, default
  schema output.
- **Custom config run** (for the demo video): a config that excludes
  `provenance`, renames `full_name` → `name`, and sets `on_missing: "omit"`
  — show it reshaping the same merged data without re-running merge logic.
- **Unit tests**: pick 2–3 of the above as gold-profile comparisons —
  scenario 2 (survivorship conflict) and scenario 9 (name-fallback match)
  are the most interesting to assert against exact expected output.
