"""Orchestrate persona generation and file output."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sample_generator.config import DEFAULT_GITHUB_FAKE_RATE, DEFAULT_GITHUB_REAL_RATE
from sample_generator.models import GenerationManifest, SourceAssignment
from sample_generator.personas import build_persona
from sample_generator.scenarios.registry import build_assignment
from sample_generator.writers.ats_writer import write_ats
from sample_generator.writers.csv_writer import write_csv
from sample_generator.writers.notes_writer import write_notes


def generate(
    count: int,
    seed: int,
    out_dir: Path,
    *,
    github_real_rate: float = DEFAULT_GITHUB_REAL_RATE,
    github_fake_rate: float = DEFAULT_GITHUB_FAKE_RATE,
) -> GenerationManifest:
    import random

    rng = random.Random(seed)

    assignments: list[SourceAssignment] = []
    tag_counter: Counter[str] = Counter()
    github_stats = {"empty": 0, "real": 0, "fake": 0}

    for _ in range(count):
        persona = build_persona(
            rng,
            github_real_rate=github_real_rate,
            github_fake_rate=github_fake_rate,
        )
        if persona.github_handle is None:
            github_stats["empty"] += 1
        elif persona.github_is_real:
            github_stats["real"] += 1
        else:
            github_stats["fake"] += 1

        assignment = build_assignment(persona, rng)
        for tag in assignment.scenario_tags:
            tag_counter[tag] += 1
        assignments.append(assignment)

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_rows = write_csv(assignments, out_dir / "recruiter_export.csv")
    ats_count = write_ats(assignments, out_dir / "ats_export.json")
    notes_count = write_notes(assignments, out_dir / "recruiter_notes.txt")

    manifest = GenerationManifest(
        seed=seed,
        count=count,
        generated_at=datetime.fromtimestamp(seed, tz=timezone.utc).isoformat(),
        scenario_histogram=dict(tag_counter),
        source_counts={
            "csv_rows": csv_rows,
            "ats_candidates": ats_count,
            "notes_sections": notes_count,
        },
        github_stats=github_stats,
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
