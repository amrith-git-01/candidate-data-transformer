import pytest

from src.normalize.emails import normalize_email
from src.normalize.names import normalize_name
from src.normalize.phones import normalize_phone
from src.normalize.skills import canonicalize_skill, extract_skills_from_text


# --- phones ---


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+1-650-555-0101", "+16505550101"),
        ("650-555-0101", "+16505550101"),
        ("+1-415-555-0102", "+14155550102"),
        ("+1-647-555-0109", "+16475550109"),
    ],
)
def test_normalize_phone_us_formats(raw, expected):
    assert normalize_phone(raw) == expected


def test_normalize_phone_invalid_returns_none():
    assert normalize_phone("not-a-phone") is None
    assert normalize_phone("") is None
    assert normalize_phone(None) is None


# --- emails ---


def test_normalize_email_lowercase():
    assert normalize_email("Linus.Torvalds@Example.COM") == "linus.torvalds@example.com"


def test_normalize_email_invalid_returns_none():
    assert normalize_email("not-an-email") is None
    assert normalize_email(None) is None


# --- names ---


def test_normalize_name_title_case_and_whitespace():
    assert normalize_name("  linus torvalds ") == "Linus Torvalds"
    assert normalize_name("Dan Abramov") == "Dan Abramov"


def test_normalize_name_empty_returns_none():
    assert normalize_name("") is None
    assert normalize_name(None) is None


# --- skills ---


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("JS", "javascript"),
        ("ecmascript", "javascript"),
        ("Golang", "go"),
        ("Rust", "rust"),
        ("Vue", "vue"),
        ("vue.js", "vue"),
        ("k8s", "kubernetes"),
        ("K8s", "kubernetes"),
        ("AWS", "aws"),
        ("node.js", "nodejs"),
        ("Next.js", "nextjs"),
        ("SolidJS", "solidjs"),
        ("CI/CD", "ci_cd"),
        ("PostgreSQL", "postgresql"),
    ],
)
def test_canonicalize_skill_aliases(raw, expected):
    assert canonicalize_skill(raw) == expected


def test_canonicalize_skill_unknown_passes_through_lowercased():
    assert canonicalize_skill("SomeObscureTool") == "someobscuretool"


def test_extract_skills_from_dan_notes_snippet():
    text = "mostly frontend - React, JavaScript, TypeScript. Rust on the side."
    found = extract_skills_from_text(text)
    assert found == ["react", "javascript", "typescript", "rust"]


def test_extract_skills_dedupes():
    text = "JavaScript, JS, and more JavaScript"
    found = extract_skills_from_text(text)
    assert found.count("javascript") == 1


def test_extract_skills_linus_kernel_and_c():
    text = "systems programming for over 30 years, primarily C and kernel-level work"
    found = extract_skills_from_text(text)
    assert "c" in found
    assert "kernel" in found


def test_extract_skills_ryan_solidjs():
    text = "Ryan created SolidJS, deep expertise in reactive UI frameworks. JavaScript, TypeScript."
    found = extract_skills_from_text(text)
    assert found[:3] == ["solidjs", "javascript", "typescript"]


def test_extract_skills_evan_vue_rust():
    text = "created Vue.js and Vite. JavaScript, TypeScript, Rust (for some newer tooling work)."
    found = extract_skills_from_text(text)
    assert "vue" in found
    assert "javascript" in found
    assert "typescript" in found
    assert "rust" in found


def test_extract_skills_does_not_false_positive_json():
    """'js' alias should not match inside unrelated tokens when using word boundaries."""
    text = "configured json schemas for the api"
    found = extract_skills_from_text(text)
    assert "javascript" not in found
