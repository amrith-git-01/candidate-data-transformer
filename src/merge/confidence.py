from src.models import CanonicalRecord, CandidateGroup, ProvenanceEntry

MATCH_TIER_WEIGHT = {"email": 1.0, "phone": 0.85, "name": 0.6}
SOURCE_TRUST = {
    "csv": 0.95,
    "ats": 0.90,
    "recruiter_notes": 0.70,
    "github": 0.75,
}


def _provenance_score(entry: ProvenanceEntry, matched_by: str) -> float:
    base = MATCH_TIER_WEIGHT[matched_by] * SOURCE_TRUST.get(entry.source, 0.5)
    return min(base, 1.0)


def compute_overall_confidence(
    profile: CanonicalRecord,
    group: CandidateGroup,
) -> float:
    if not profile.provenance:
        return MATCH_TIER_WEIGHT[group.matched_by] * 0.5

    field_scores: dict[str, list[float]] = {}
    for entry in profile.provenance:
        field_scores.setdefault(entry.field, []).append(
            _provenance_score(entry, group.matched_by)
        )

    per_field_best = [max(scores) for scores in field_scores.values()]
    base = sum(per_field_best) / len(per_field_best)

    # Agreement bonus: count scalar/list fields with 2+ distinct agreeing sources
    agreement_bonus = 0.0
    for field, entries in _group_provenance_by_field(profile.provenance).items():
        sources = {e.source for e in entries}
        if len(sources) >= 2:
            agreement_bonus += 0.03

    return round(min(base + agreement_bonus, 1.0), 3)


def _group_provenance_by_field(
    provenance: list[ProvenanceEntry],
) -> dict[str, list[ProvenanceEntry]]:
    out: dict[str, list[ProvenanceEntry]] = {}
    for entry in provenance:
        out.setdefault(entry.field, []).append(entry)
    return out


def skill_confidence(source: str, matched_by: str) -> float:
    return round(MATCH_TIER_WEIGHT[matched_by] * SOURCE_TRUST.get(source, 0.5), 3)