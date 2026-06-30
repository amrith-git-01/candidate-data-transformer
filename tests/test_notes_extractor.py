"""Strict notes extraction behavior."""

from src.adapters.notes_adapter import parse_notes
from src.merge.survivorship import merge_group
from src.models import CandidateGroup, FieldValue, RawRecord


def test_hortense_like_location_country_not_sentence_tail(tmp_path):
    body = (
        "=== Candidate: Hortense du Tessier ===\n"
        "Seasoned professional (30 years) with depth in React.js, kernel, dynamodb, rest. "
        "Currently in Göteborg, Örebro län, SE. "
        "Degree in Software Engineering from Gustafsson HB University. "
        "Based in Göteborg, Örebro län, SE."
    )
    path = tmp_path / "notes.txt"
    path.write_text(body, encoding="utf-8")
    record = parse_notes(path)[0]

    assert record.fields["city"].value == "Göteborg"
    assert record.fields["region"].value == "Örebro län"
    assert record.fields["country"].value == "SE"
    assert "Degree" not in record.fields["country"].value

    group = CandidateGroup(records=[record], matched_by="name")
    profile = merge_group(group)
    assert profile.location.country == "SE"


def test_hortense_like_education_field_and_institution(tmp_path):
    body = (
        "=== Candidate: Test Person ===\n"
        "Currently in Austin, Texas, US. "
        "Degree in Software Engineering from Gustafsson HB University."
    )
    path = tmp_path / "notes.txt"
    path.write_text(body, encoding="utf-8")
    record = parse_notes(path)[0]
    edu = record.fields["education"].value[0]
    assert edu["institution"] == "Gustafsson HB University"
    assert edu["field"] == "Software Engineering"
    assert "Software Engineering from" not in edu["institution"]


def test_ambiguous_degree_in_only_no_education_field():
    record = RawRecord(
        source="recruiter_notes",
        fields={
            "full_name": FieldValue(value="X", method="direct"),
        },
    )
    from src.adapters import notes_adapter

    body = "Degree in Computer Science without a named school."
    assert notes_adapter._extract_education(body) is None


def test_full_country_name_normalized_to_iso(tmp_path):
    body = "=== Candidate: X ===\nBased in Oslo, Oslo, Norway."
    path = tmp_path / "notes.txt"
    path.write_text(body, encoding="utf-8")
    record = parse_notes(path)[0]
    assert record.fields["country"].value == "NO"


def test_invalid_country_omitted(tmp_path):
    body = "=== Candidate: X ===\nBased in Springfield, Illinois, NotARealCountryXYZ."
    path = tmp_path / "notes.txt"
    path.write_text(body, encoding="utf-8")
    record = parse_notes(path)[0]
    assert "country" not in record.fields
    assert record.fields["city"].value == "Springfield"


def test_years_out_of_range_omitted(tmp_path):
    body = "=== Candidate: X ===\nHas 150 years experience with python."
    path = tmp_path / "notes.txt"
    path.write_text(body, encoding="utf-8")
    record = parse_notes(path)[0]
    assert "years_experience" not in record.fields
