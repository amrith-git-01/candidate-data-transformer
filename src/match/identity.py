"""Tiered exact identity matching: email -> phone (no name-based joins)."""

from src.models import CandidateGroup, RawRecord
from src.normalize.emails import normalize_email
from src.normalize.names import normalize_name
from src.normalize.phones import normalize_phone

TIER_RANK = {"email": 3, "phone": 2, "name": 1}


class _UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _record_keys(rec: RawRecord) -> dict[str, set[str]]:
    keys: dict[str, set[str]] = {"email": set(), "phone": set(), "name": set()}

    if email_fv := rec.fields.get("email"):
        if norm := normalize_email(str(email_fv.value)):
            keys["email"].add(norm)

    if phone_fv := rec.fields.get("phone"):
        if norm := normalize_phone(str(phone_fv.value)):
            keys["phone"].add(norm)

    if name_fv := rec.fields.get("full_name"):
        if norm := normalize_name(str(name_fv.value)):
            keys["name"].add(norm)

    return keys


def _merge_tier(current: str, candidate: str) -> str:
    """Keep strongest tier used to join the group (email > phone > name)."""
    return candidate if TIER_RANK[candidate] > TIER_RANK[current] else current


def _best_tier_for_keys(keys: dict[str, set[str]]) -> str:
    if keys["email"]:
        return "email"
    if keys["phone"]:
        return "phone"
    return "name"


def group_records(records: list[RawRecord]) -> list[CandidateGroup]:
    if not records:
        return []

    n = len(records)
    uf = _UnionFind(n)
    root_tier: dict[int, str] = {i: "name" for i in range(n)}
    all_keys = [_record_keys(r) for r in records]

    def merge_by(tier: str) -> None:
        buckets: dict[str, list[int]] = {}
        for idx, keys in enumerate(all_keys):
            for key in keys[tier]:
                buckets.setdefault(key, []).append(idx)

        for indices in buckets.values():
            if len(indices) < 2:
                continue
            anchor = indices[0]
            for other in indices[1:]:
                uf.union(anchor, other)
                root = uf.find(anchor)
                root_tier[root] = _merge_tier(root_tier[root], tier)

    merge_by("email")
    merge_by("phone")

    grouped: dict[int, list[int]] = {}
    for i in range(n):
        root = uf.find(i)
        grouped.setdefault(root, []).append(i)

    result: list[CandidateGroup] = []
    for root, indices in grouped.items():
        tier = root_tier[root]
        if len(indices) == 1:
            tier = _best_tier_for_keys(all_keys[indices[0]])
        result.append(
            CandidateGroup(
                records=[records[i] for i in indices],
                matched_by=tier,  # type: ignore[arg-type]
            )
        )
    return result