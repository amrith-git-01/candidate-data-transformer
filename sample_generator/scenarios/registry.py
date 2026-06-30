"""Scenario tag registry and probabilistic rolling."""

from __future__ import annotations

import random
from collections.abc import Callable

from sample_generator import config
from sample_generator.models import SourceAssignment
from sample_generator.personas import baseline_source_presence
from sample_generator.scenarios import mutators

TAG_APPLIERS: dict[str, Callable[[SourceAssignment, random.Random], None]] = {
    "happy_path": lambda a, _r: mutators.apply_happy_path(a),
    "title_conflict": mutators.apply_title_conflict,
    "email_typo": mutators.apply_email_typo,
    "phone_join": lambda a, _r: mutators.apply_phone_join(a),
    "csv_only": lambda a, _r: mutators.apply_csv_only(a),
    "ats_notes_only": lambda a, _r: mutators.apply_ats_notes_only(a),
    "notes_only": lambda a, _r: mutators.apply_notes_only(a),
    "glitch_email": lambda a, _r: mutators.apply_glitch_email(a),
    "github_text_only": mutators.apply_github_text_only,
    "github_404": lambda a, _r: mutators.apply_github_404(a),
    "csv_duplicate": lambda a, _r: mutators.apply_csv_duplicate(a),
}


def _tags_compatible(existing: list[str], candidate: str) -> bool:
    for tag in existing:
        if frozenset({tag, candidate}) in config.INCOMPATIBLE_TAGS:
            return False
    return True


def roll_primary_tag(rng: random.Random) -> str | None:
    tags = list(config.SCENARIO_WEIGHTS.keys())
    weights = [config.SCENARIO_WEIGHTS[t] for t in tags]
    total = sum(weights)
    if rng.random() > total:
        return None
    return rng.choices(tags, weights=weights, k=1)[0]


def roll_secondary_tag(rng: random.Random, primary: str | None) -> str | None:
    if primary is None or rng.random() > config.SECONDARY_TAG_CHANCE:
        return None
    candidates = [
        t for t in config.SCENARIO_WEIGHTS if t != primary and _tags_compatible([primary], t)
    ]
    if not candidates:
        return None
    weights = [config.SCENARIO_WEIGHTS[t] for t in candidates]
    return rng.choices(candidates, weights=weights, k=1)[0]


def apply_tags(assignment: SourceAssignment, tags: list[str], rng: random.Random) -> None:
    for tag in tags:
        applier = TAG_APPLIERS.get(tag)
        if applier:
            applier(assignment, rng)


def build_assignment(
    persona,
    rng: random.Random,
) -> SourceAssignment:
    in_csv, in_ats, in_notes = baseline_source_presence(rng)
    assignment = SourceAssignment(
        persona=persona,
        in_csv=in_csv,
        in_ats=in_ats,
        in_notes=in_notes,
    )

    primary = roll_primary_tag(rng)
    tags: list[str] = []
    if primary:
        tags.append(primary)
    secondary = roll_secondary_tag(rng, primary)
    if secondary:
        tags.append(secondary)

    assignment.scenario_tags = tags
    apply_tags(assignment, tags, rng)

    if not assignment.in_csv and not assignment.in_ats and not assignment.in_notes:
        assignment.in_csv = True

    return assignment
