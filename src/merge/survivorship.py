"""Merge CandidateGroup -> CanonicalRecord with survivorship + provenance."""

from __future__ import annotations

import re
import uuid

from src.merge.confidence import compute_overall_confidence, skill_confidence
from src.models import (
    CandidateGroup,
    CanonicalRecord,
    EducationEntry,
    ExperienceEntry,
    FieldValue,
    LinkSet,
    ProvenanceEntry,
    RawRecord,
    SkillEntry,
)
from src.normalize.emails import normalize_email
from src.normalize.location import normalize_location
from src.normalize.names import normalize_name
from src.normalize.phones import normalize_phone
from src.adapters.link_detector import find_github_from_fields

SOURCE_ORDER_NAME = ["csv", "ats", "recruiter_notes", "github"]
SOURCE_ORDER_JOB = ["csv", "ats"]
SOURCE_ORDER_HEADLINE = ["ats", "recruiter_notes", "github"]
SOURCE_ORDER_YEARS = ["ats", "recruiter_notes"]
SOURCE_ORDER_LOCATION = ["csv", "ats", "recruiter_notes", "github"]
SOURCE_ORDER_EDUCATION = ["ats", "recruiter_notes"]

TRUST_RANK = {s: i for i, s in enumerate(SOURCE_ORDER_NAME)}

# Stable namespace for deterministic candidate UUIDs (same identity key -> same id).
_CANDIDATE_ID_NAMESPACE = uuid.UUID("a3f2c8e1-4b9d-4e2a-9f1c-7d6e5b4a3920")


def merge_group(group: CandidateGroup) -> CanonicalRecord:
    records = group.records

    emails = _union_normalized_emails(records)
    phones = _union_normalized_phones(records)
    full_name = _scalar_winner(records, "full_name", SOURCE_ORDER_NAME) or _fallback_name(records)
    company = _scalar_winner(records, "current_company", SOURCE_ORDER_JOB)
    title = _scalar_winner(records, "current_title", SOURCE_ORDER_JOB)
    headline = _scalar_winner(records, "headline", SOURCE_ORDER_HEADLINE)
    years = _years_winner(records)
    location = _merge_location(records)
    education = _education_winner(records)

    skills, skill_prov = _merge_skills(records, group.matched_by)
    provenance = _build_provenance(records, full_name, company, title, headline, years)
    provenance.extend(_email_phone_provenance(records, emails, phones))
    provenance.extend(skill_prov)
    provenance.extend(_location_provenance(records))
    provenance.extend(_education_provenance(records, education))

    experience: list[ExperienceEntry] = []
    if company and title:
        experience.append(ExperienceEntry(company=company, title=title))

    links = _merge_links(records)
    candidate_id = _make_candidate_id(emails, full_name, phones)

    profile = CanonicalRecord(
        candidate_id=candidate_id,
        full_name=full_name,
        emails=emails,
        phones=phones,
        location=location,
        links=links,
        headline=headline,
        years_experience=years,
        skills=skills,
        experience=experience,
        education=education,
        provenance=provenance,
        matched_by=group.matched_by,
    )
    profile.overall_confidence = compute_overall_confidence(profile, group)
    return profile


def _field_str(rec: RawRecord, key: str) -> str | None:
    fv = rec.fields.get(key)
    if fv is None or fv.value is None:
        return None
    text = str(fv.value).strip()
    return text or None


def _scalar_winner(
    records: list[RawRecord],
    field: str,
    source_order: list[str],
) -> str | None:
    by_source: dict[str, str] = {}
    for rec in records:
        val = _field_str(rec, field)
        if val and rec.source not in by_source:
            by_source[rec.source] = val
    for source in source_order:
        if source in by_source:
            return by_source[source]
    return None


def _fallback_name(records: list[RawRecord]) -> str:
    for rec in records:
        if val := _field_str(rec, "full_name"):
            return normalize_name(val) or val
    return "unknown"


def _union_normalized_emails(records: list[RawRecord]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for rec in records:
        if val := _field_str(rec, "email"):
            if norm := normalize_email(val):
                if norm not in seen:
                    seen.add(norm)
                    out.append(norm)
    return out


def _union_normalized_phones(records: list[RawRecord]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for rec in records:
        if val := _field_str(rec, "phone"):
            if norm := normalize_phone(val):
                if norm not in seen:
                    seen.add(norm)
                    out.append(norm)
    return out


def _years_winner(records: list[RawRecord]) -> int | None:
    by_source: dict[str, int] = {}
    for rec in records:
        fv = rec.fields.get("years_experience")
        if fv and fv.value is not None:
            try:
                by_source[rec.source] = int(fv.value)
            except (TypeError, ValueError):
                continue
    for source in SOURCE_ORDER_YEARS:
        if source in by_source:
            return by_source[source]
    return None


def _merge_skills(
    records: list[RawRecord],
    matched_by: str,
) -> tuple[list[SkillEntry], list[ProvenanceEntry]]:
    # skill_name -> {sources}
    bucket: dict[str, set[str]] = {}
    methods: dict[str, str] = {}

    for rec in records:
        for key, fv in rec.fields.items():
            if key.startswith("skill_") and fv.value:
                name = str(fv.value)
                bucket.setdefault(name, set()).add(rec.source)
                methods[name] = fv.method

    skills: list[SkillEntry] = []
    prov: list[ProvenanceEntry] = []
    for name in sorted(bucket):
        sources = sorted(bucket[name])
        primary = sources[0]
        skills.append(
            SkillEntry(
                name=name,
                confidence=skill_confidence(primary, matched_by),
                sources=sources,
            )
        )
        for source in sources:
            prov.append(
                ProvenanceEntry(
                    field=f"skills.{name}",
                    source=source,
                    method=methods[name],
                )
            )
    return skills, prov


def _merge_links(records: list[RawRecord]) -> LinkSet:
    github: str | None = None
    linkedin: str | None = None
    for rec in sorted(records, key=lambda r: TRUST_RANK.get(r.source, 99)):
        if not github and (handle := find_github_from_fields(rec.fields)):
            github = f"https://github.com/{handle}"
        if not linkedin:
            url = _field_str(rec, "linkedin_url")
            if url:
                linkedin = url
    return LinkSet(github=github, linkedin=linkedin)


def _merge_location(records: list[RawRecord]):
    city = _scalar_winner(records, "city", SOURCE_ORDER_LOCATION)
    region = _scalar_winner(records, "region", SOURCE_ORDER_LOCATION)
    country = _scalar_winner(records, "country", SOURCE_ORDER_LOCATION)
    return normalize_location(city=city, region=region, country=country)


def _education_winner(records: list[RawRecord]) -> list[EducationEntry]:
    for source in SOURCE_ORDER_EDUCATION:
        for rec in records:
            if rec.source != source:
                continue
            fv = rec.fields.get("education")
            if not fv or not isinstance(fv.value, list):
                continue
            entries: list[EducationEntry] = []
            for item in fv.value:
                if not isinstance(item, dict):
                    continue
                institution = item.get("institution")
                if not institution:
                    continue
                entries.append(
                    EducationEntry(
                        institution=str(institution).strip(),
                        degree=item.get("degree"),
                        field=item.get("field"),
                        end_year=item.get("end_year"),
                    )
                )
            if entries:
                return entries
    return []


def _location_provenance(records: list[RawRecord]) -> list[ProvenanceEntry]:
    prov: list[ProvenanceEntry] = []
    for part, out_field in (("city", "location.city"), ("region", "location.region"), ("country", "location.country")):
        for rec in records:
            fv = rec.fields.get(part)
            if fv and fv.value is not None and str(fv.value).strip():
                prov.append(
                    ProvenanceEntry(field=out_field, source=rec.source, method=fv.method)
                )
    return prov


def _education_provenance(records: list[RawRecord], education: list) -> list[ProvenanceEntry]:
    if not education:
        return []
    prov: list[ProvenanceEntry] = []
    for source in SOURCE_ORDER_EDUCATION:
        for rec in records:
            if rec.source != source:
                continue
            fv = rec.fields.get("education")
            if not fv or not isinstance(fv.value, list):
                continue
            for idx, item in enumerate(fv.value):
                if not isinstance(item, dict):
                    continue
                prefix = f"education[{idx}]"
                if item.get("institution"):
                    prov.append(
                        ProvenanceEntry(
                            field=f"{prefix}.institution",
                            source=rec.source,
                            method=fv.method,
                        )
                    )
                if item.get("degree"):
                    prov.append(
                        ProvenanceEntry(
                            field=f"{prefix}.degree",
                            source=rec.source,
                            method=fv.method,
                        )
                    )
                if item.get("field"):
                    prov.append(
                        ProvenanceEntry(
                            field=f"{prefix}.field",
                            source=rec.source,
                            method=fv.method,
                        )
                    )
                if item.get("end_year") is not None:
                    prov.append(
                        ProvenanceEntry(
                            field=f"{prefix}.end_year",
                            source=rec.source,
                            method=fv.method,
                        )
                    )
            if prov:
                return prov
    return prov


def _email_phone_provenance(
    records: list[RawRecord],
    emails: list[str],
    phones: list[str],
) -> list[ProvenanceEntry]:
    """Record which sources contributed each unioned email/phone (indexed paths)."""
    prov: list[ProvenanceEntry] = []
    for rec in records:
        email_fv = rec.fields.get("email")
        if email_fv and email_fv.value is not None:
            norm = normalize_email(str(email_fv.value).strip())
            if norm and norm in emails:
                prov.append(
                    ProvenanceEntry(
                        field=f"emails[{emails.index(norm)}]",
                        source=rec.source,
                        method=email_fv.method,
                    )
                )
        phone_fv = rec.fields.get("phone")
        if phone_fv and phone_fv.value is not None:
            norm = normalize_phone(str(phone_fv.value).strip())
            if norm and norm in phones:
                prov.append(
                    ProvenanceEntry(
                        field=f"phones[{phones.index(norm)}]",
                        source=rec.source,
                        method=phone_fv.method,
                    )
                )
    return prov


def _build_provenance(
    records: list[RawRecord],
    full_name: str,
    company: str | None,
    title: str | None,
    headline: str | None,
    years: int | None,
) -> list[ProvenanceEntry]:
    prov: list[ProvenanceEntry] = []

    def add_all(field_key: str, out_field: str) -> None:
        for rec in records:
            fv = rec.fields.get(field_key)
            if fv and fv.value is not None and str(fv.value).strip():
                prov.append(
                    ProvenanceEntry(field=out_field, source=rec.source, method=fv.method)
                )

    add_all("full_name", "full_name")
    add_all("current_company", "experience[0].company")
    add_all("current_title", "experience[0].title")
    add_all("headline", "headline")
    add_all("linkedin_url", "links.linkedin")
    if years is not None:
        for rec in records:
            fv = rec.fields.get("years_experience")
            if fv and fv.value == years:
                prov.append(
                    ProvenanceEntry(
                        field="years_experience",
                        source=rec.source,
                        method=fv.method,
                    )
                )
    return prov


def _make_candidate_id(
    emails: list[str],
    full_name: str,
    phones: list[str] | None = None,
) -> str:
    """Deterministic UUID v5 from primary email, else phone+name, else name."""
    if emails:
        seed = emails[0].strip().lower()
    elif phones:
        name = normalize_name(full_name) or full_name.strip().lower()
        seed = f"{name}|{phones[0]}"
    else:
        seed = normalize_name(full_name) or full_name.strip().lower()
    return str(uuid.uuid5(_CANDIDATE_ID_NAMESPACE, seed))