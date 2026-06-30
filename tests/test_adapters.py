from src.adapters.ats_adapter import parse_ats
from src.adapters.csv_adapter import parse_csv
from src.adapters.link_detector import find_github_handle
from src.adapters.notes_adapter import parse_notes


def test_find_github_handle_with_and_without_scheme():
    assert find_github_handle("https://github.com/torvalds") == "torvalds"
    assert find_github_handle("see github.com/sdras for repos") == "sdras"
    assert find_github_handle("no link here") is None


def test_parse_csv_dedupes_linus(curated_csv):
    records = parse_csv(curated_csv)
    linus_count = sum(
        1 for r in records if r.fields["full_name"].value == "Linus Torvalds"
    )
    assert linus_count == 1
    assert len(records) == 5


def test_parse_csv_maps_columns(curated_csv):
    records = parse_csv(curated_csv)
    linus = next(r for r in records if r.fields["full_name"].value == "Linus Torvalds")
    assert linus.source == "csv"
    assert linus.fields["email"].value == "linus.torvalds@example.com"
    assert linus.fields["current_company"].value == "Linux Foundation"


def test_parse_ats_maps_and_skips_glitch(curated_ats):
    records = parse_ats(curated_ats)
    names = [r.fields["full_name"].value for r in records]
    assert "Glitch Entry" not in names
    assert "Linus Torvalds" in names
    linus = next(r for r in records if r.fields["full_name"].value == "Linus Torvalds")
    assert linus.fields["github_url"].value == "https://github.com/torvalds"


def test_parse_notes_splits_candidates(curated_notes):
    records = parse_notes(curated_notes)
    names = {r.fields["full_name"].value for r in records}
    assert "Sarah Drasner" in names
    assert "Jane Doe" in names
    assert len(records) == 6


def test_parse_notes_extracts_github_for_sarah(curated_notes):
    records = parse_notes(curated_notes)
    sarah = next(r for r in records if r.fields["full_name"].value == "Sarah Drasner")
    assert sarah.fields["github_url"].value == "https://github.com/sdras"


def test_parse_notes_extracts_skills_for_dan(curated_notes):
    records = parse_notes(curated_notes)
    dan = next(r for r in records if r.fields["full_name"].value == "Dan Abramov")
    skills = [fv.value for k, fv in dan.fields.items() if k.startswith("skill_")]
    assert "javascript" in skills
    assert dan.fields["years_experience"].value == 10
    assert dan.fields["city"].value == "San Francisco"


def test_parse_notes_extracts_location_for_sarah(curated_notes):
    records = parse_notes(curated_notes)
    sarah = next(r for r in records if r.fields["full_name"].value == "Sarah Drasner")
    assert sarah.fields["city"].value == "Denver"
    assert sarah.fields["region"].value == "Colorado"
    assert sarah.fields["country"].value == "US"


def test_parse_ats_includes_education_and_location(curated_ats):
    records = parse_ats(curated_ats)
    linus = next(r for r in records if r.fields["full_name"].value == "Linus Torvalds")
    assert linus.fields["city"].value == "Portland"
    assert linus.fields["country"].value == "United States"
    assert isinstance(linus.fields["education"].value, list)
    assert linus.fields["headline"].value == "Creator of Linux and Git"


def test_parse_csv_includes_location_and_linkedin(curated_csv):
    records = parse_csv(curated_csv)
    dan = next(r for r in records if r.fields["full_name"].value == "Dan Abramov")
    assert dan.fields["city"].value == "San Francisco"
    assert dan.fields["country"].value == "US"
    assert "linkedin.com" in dan.fields["linkedin_url"].value


def test_missing_file_returns_empty(tmp_path):
    assert parse_csv(tmp_path / "nope.csv") == []
    assert parse_ats(tmp_path / "nope.json") == []
    assert parse_notes(tmp_path / "nope.txt") == []
