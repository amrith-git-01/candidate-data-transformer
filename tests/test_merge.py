import re

from src.merge.survivorship import merge_group
from src.models import CandidateGroup, FieldValue, RawRecord


def test_csv_wins_city_over_ats():
    group = CandidateGroup(
        matched_by="email",
        records=[
            RawRecord(
                source="csv",
                fields={
                    "full_name": FieldValue(value="Dan Abramov", method="direct"),
                    "email": FieldValue(value="dan.abramov@example.com", method="direct"),
                    "city": FieldValue(value="San Francisco", method="direct"),
                    "region": FieldValue(value="California", method="direct"),
                    "country": FieldValue(value="US", method="direct"),
                },
            ),
            RawRecord(
                source="ats",
                fields={
                    "full_name": FieldValue(value="Dan Abramov", method="direct"),
                    "email": FieldValue(value="dan.abramov@example.com", method="direct"),
                    "city": FieldValue(value="Oakland", method="direct"),
                    "region": FieldValue(value="California", method="direct"),
                    "country": FieldValue(value="US", method="direct"),
                },
            ),
        ],
    )
    profile = merge_group(group)
    assert profile.location.city == "San Francisco"
    assert profile.location.country == "US"


def test_education_from_ats():
    group = CandidateGroup(
        matched_by="email",
        records=[
            RawRecord(
                source="ats",
                fields={
                    "full_name": FieldValue(value="Linus Torvalds", method="direct"),
                    "education": FieldValue(
                        value=[{
                            "institution": "University of Helsinki",
                            "degree": "MSc",
                            "field": "Computer Science",
                            "end_year": 1996,
                        }],
                        method="direct",
                    ),
                },
            ),
        ],
    )
    profile = merge_group(group)
    assert len(profile.education) == 1
    assert profile.education[0].institution == "University of Helsinki"
    edu_fields = {p.field for p in profile.provenance if p.field.startswith("education[")}
    assert "education[0].institution" in edu_fields
    assert "education[0].degree" in edu_fields
    assert "education[0].field" in edu_fields
    assert "education[0].end_year" in edu_fields
    assert "education" not in edu_fields


def test_csv_wins_title_conflict():
    group = CandidateGroup(
        matched_by="email",
        records=[
            RawRecord(
                source="csv",
                fields={
                    "full_name": FieldValue(value="Dan Abramov", method="direct"),
                    "email": FieldValue(value="dan.abramov@example.com", method="direct"),
                    "current_title": FieldValue(value="Engineer", method="direct"),
                    "current_company": FieldValue(value="Bluesky", method="direct"),
                },
            ),
            RawRecord(
                source="ats",
                fields={
                    "full_name": FieldValue(value="Dan Abramov", method="direct"),
                    "email": FieldValue(value="dan.abramov@example.com", method="direct"),
                    "current_title": FieldValue(value="Staff Software Engineer", method="direct"),
                    "current_company": FieldValue(value="Bluesky", method="direct"),
                },
            ),
        ],
    )
    profile = merge_group(group)
    assert profile.experience[0].title == "Engineer"
    title_sources = {p.source for p in profile.provenance if "title" in p.field}
    assert title_sources == {"csv", "ats"}


def test_union_emails_and_phones():
    group = CandidateGroup(
        matched_by="email",
        records=[
            RawRecord(
                source="csv",
                fields={
                    "full_name": FieldValue(value="Test User", method="direct"),
                    "email": FieldValue(value="a@example.com", method="direct"),
                },
            ),
            RawRecord(
                source="ats",
                fields={
                    "full_name": FieldValue(value="Test User", method="direct"),
                    "phone": FieldValue(value="+1-650-555-0101", method="direct"),
                },
            ),
        ],
    )
    profile = merge_group(group)
    assert "a@example.com" in profile.emails
    assert "+16505550101" in profile.phones
    email_prov = [p for p in profile.provenance if p.field.startswith("emails")]
    phone_prov = [p for p in profile.provenance if p.field.startswith("phones")]
    assert len(email_prov) == 1
    assert email_prov[0].field == "emails[0]"
    assert email_prov[0].source == "csv"
    assert email_prov[0].method == "direct"
    assert len(phone_prov) == 1
    assert phone_prov[0].field == "phones[0]"
    assert phone_prov[0].source == "ats"
    assert phone_prov[0].method == "direct"


def test_name_match_lower_confidence_than_email():
    email_group = CandidateGroup(
        matched_by="email",
        records=[
            RawRecord(
                source="csv",
                fields={
                    "full_name": FieldValue(value="Alice", method="direct"),
                    "email": FieldValue(value="alice@example.com", method="direct"),
                    "current_company": FieldValue(value="Acme", method="direct"),
                    "current_title": FieldValue(value="Eng", method="direct"),
                },
            ),
            RawRecord(
                source="ats",
                fields={
                    "full_name": FieldValue(value="Alice", method="direct"),
                    "email": FieldValue(value="alice@example.com", method="direct"),
                    "current_company": FieldValue(value="Acme", method="direct"),
                    "current_title": FieldValue(value="Eng", method="direct"),
                },
            ),
        ],
    )
    name_group = CandidateGroup(
        matched_by="name",
        records=[
            RawRecord(
                source="csv",
                fields={
                    "full_name": FieldValue(value="Bob", method="direct"),
                    "current_company": FieldValue(value="Acme", method="direct"),
                    "current_title": FieldValue(value="Eng", method="direct"),
                },
            ),
            RawRecord(
                source="ats",
                fields={
                    "full_name": FieldValue(value="Bob", method="direct"),
                    "current_company": FieldValue(value="Acme", method="direct"),
                    "current_title": FieldValue(value="Eng", method="direct"),
                },
            ),
        ],
    )
    email_conf = merge_group(email_group).overall_confidence
    name_conf = merge_group(name_group).overall_confidence
    assert email_conf > name_conf


def test_candidate_id_from_email():
    group = CandidateGroup(
        matched_by="email",
        records=[
            RawRecord(
                source="csv",
                fields={
                    "full_name": FieldValue(value="Linus Torvalds", method="direct"),
                    "email": FieldValue(value="linus.torvalds@example.com", method="direct"),
                },
            ),
        ],
    )
    profile = merge_group(group)
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        profile.candidate_id,
    )
    again = merge_group(group)
    assert again.candidate_id == profile.candidate_id


def test_email_provenance_when_both_sources_agree():
    group = CandidateGroup(
        matched_by="email",
        records=[
            RawRecord(
                source="csv",
                fields={
                    "full_name": FieldValue(value="Aarush Radhakrishnan", method="direct"),
                    "email": FieldValue(value="aarush.radhakrishnan@mail.example.com", method="direct"),
                },
            ),
            RawRecord(
                source="ats",
                fields={
                    "full_name": FieldValue(value="Aarush Radhakrishnan", method="direct"),
                    "email": FieldValue(value="aarush.radhakrishnan@mail.example.com", method="direct"),
                },
            ),
        ],
    )
    profile = merge_group(group)
    email_prov = [p for p in profile.provenance if p.field == "emails[0]"]
    assert len(email_prov) == 2
    assert {p.source for p in email_prov} == {"csv", "ats"}


def test_skill_provenance_includes_all_sources():
    group = CandidateGroup(
        matched_by="email",
        records=[
            RawRecord(
                source="csv",
                fields={
                    "full_name": FieldValue(value="Dev", method="direct"),
                    "email": FieldValue(value="dev@example.com", method="direct"),
                    "skill_python": FieldValue(value="python", method="direct"),
                },
            ),
            RawRecord(
                source="recruiter_notes",
                fields={
                    "full_name": FieldValue(value="Dev", method="direct"),
                    "skill_python": FieldValue(value="python", method="extracted"),
                },
            ),
        ],
    )
    profile = merge_group(group)
    skill_prov = [p for p in profile.provenance if p.field == "skills.python"]
    assert len(skill_prov) == 2
    assert {p.source for p in skill_prov} == {"csv", "recruiter_notes"}


def test_github_link_picked_from_ats():
    group = CandidateGroup(
        matched_by="email",
        records=[
            RawRecord(
                source="ats",
                fields={
                    "full_name": FieldValue(value="Linus Torvalds", method="direct"),
                    "github_url": FieldValue(
                        value="https://github.com/torvalds",
                        method="direct",
                    ),
                },
            ),
        ],
    )
    profile = merge_group(group)
    assert profile.links.github == "https://github.com/torvalds"
