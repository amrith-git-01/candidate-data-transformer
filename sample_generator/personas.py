"""Faker-based persona factory."""

from __future__ import annotations

import random
import re

from faker import Faker
from slugify import slugify

from sample_generator import config
from sample_generator.models import Persona


def _slug_name(name: str) -> str:
    return slugify(name, lowercase=True) or "candidate"


def _email_from_name(full_name: str, rng: random.Random) -> str:
    parts = re.sub(r"[^a-zA-Z\s]", "", full_name).lower().split()
    if len(parts) >= 2:
        base = f"{parts[0]}.{parts[-1]}"
    elif parts:
        base = parts[0]
    else:
        base = f"user{rng.randint(1000, 9999)}"
    if rng.random() < 0.12:
        base += str(rng.randint(1, 99))
    domain = rng.choice(["example.com", "mail.example.com", "corp.example.com"])
    return f"{base}@{domain}"


def _us_phone(rng: random.Random) -> str:
    area = rng.randint(200, 989)
    line = rng.randint(1000, 9999)
    return f"+1-{area}-555-{line:04d}"


def _phone_for_country(
    rng: random.Random,
    country_code: str,
    loc_faker: Faker,
) -> str:
    if country_code in ("US", "CA"):
        return _us_phone(rng)
    raw = loc_faker.phone_number()
    if raw.startswith("+"):
        return raw
    return f"+{rng.randint(1, 99)}-{raw}"


def _pick_region(loc_faker: Faker, rng: random.Random) -> str:
    for name in ("state", "administrative_unit", "province", "region", "county"):
        provider = getattr(loc_faker, name, None)
        if callable(provider):
            try:
                value = provider()
                if value:
                    return str(value)
            except Exception:
                continue
    return f"Region-{rng.randint(1, 99)}"


def _pick_country(rng: random.Random) -> tuple[str, str]:
    variants = rng.choice(config.COUNTRY_VARIANTS)
    country_code = variants[0]
    country_label = rng.choice(variants[1:])
    return country_code, country_label


def _localized_faker(country_code: str, rng: random.Random) -> Faker:
    locale = config.COUNTRY_LOCALE.get(country_code, "en_US")
    loc = Faker(locale)
    loc.seed_instance(rng.randint(0, 2**31 - 1))
    return loc


def _pick_title(rng: random.Random, faker: Faker) -> str:
    if rng.random() < config.TITLE_USE_FAKER_RATE:
        job = faker.job()
        if job and len(job) < 80:
            return job
    return rng.choice(config.TITLE_POOL)


def _assign_github(
    rng: random.Random,
    real_rate: float,
    fake_rate: float,
    person_id: str,
) -> tuple[str | None, bool]:
    roll = rng.random()
    if roll < real_rate:
        return rng.choice(config.REAL_GITHUB_HANDLES), True
    if roll < real_rate + fake_rate:
        return f"nonexistent-handle-{person_id}", False
    return None, False


def _build_education(
    faker: Faker,
    loc_faker: Faker,
    rng: random.Random,
) -> list[dict]:
    count = rng.randint(0, 3)
    entries: list[dict] = []
    for _ in range(count):
        institution = rng.choice([
            loc_faker.company() + " University",
            faker.company() + " Institute of Technology",
            loc_faker.city() + " State University",
            faker.company() + " College",
        ])
        entries.append({
            "institution": institution,
            "degree": rng.choice(config.DEGREE_POOL),
            "field": rng.choice(config.FIELD_POOL),
            "end_year": rng.randint(1985, 2025),
        })
    return entries


def _skill_list_for_persona(rng: random.Random) -> list[str]:
    count = rng.randint(4, min(12, len(config.SKILL_POOL)))
    return rng.sample(config.SKILL_POOL, k=count)


def _skills_for_notes(skills: list[str], rng: random.Random) -> str:
    display = list(skills[: min(4, len(skills))])
    if display and rng.random() < 0.25:
        idx = rng.randrange(len(display))
        display[idx] = rng.choice(config.SKILL_NOTE_ALIASES)
    return ", ".join(display)


def _build_notes_body(persona: Persona, rng: random.Random) -> str:
    skill_sample = _skills_for_notes(persona.skills, rng)
    years = persona.years_experience or rng.randint(2, 15)
    openings = [
        f"Has around {years} years experience, mostly working with {skill_sample}.",
        f"Brings {years}+ years of hands-on experience across {skill_sample}.",
        f"Seasoned professional ({years} years) with depth in {skill_sample}.",
        f"Background spans {years} years; strongest in {skill_sample}.",
    ]
    lines = [rng.choice(openings)]
    if persona.city and persona.region:
        country = persona.country or "the region"
        loc_phrases = [
            f"Based in {persona.city}, {persona.region}, {country}.",
            f"Currently in {persona.city}, {persona.region}, {country}.",
            f"Lives in {persona.city}, {persona.region}, {country}.",
        ]
        lines.append(rng.choice(loc_phrases))
    if persona.education:
        inst = persona.education[0].get("institution", "university")
        field = persona.education[0].get("field")
        if field and rng.random() < 0.5:
            lines.append(f"Degree in {field} from {inst}.")
        else:
            lines.append(f"Studied at {inst}.")
    if persona.github_handle and rng.random() < 0.35:
        lines.append(
            f"Open source activity at github.com/{persona.github_handle}."
        )
    return " ".join(lines)


def _persona_faker(rng: random.Random) -> Faker:
    locale = rng.choice(config.FAKER_LOCALES)
    faker = Faker(locale)
    faker.seed_instance(rng.randint(0, 2**31 - 1))
    return faker


def build_persona(
    rng: random.Random,
    *,
    github_real_rate: float = config.DEFAULT_GITHUB_REAL_RATE,
    github_fake_rate: float = config.DEFAULT_GITHUB_FAKE_RATE,
) -> Persona:
    faker = _persona_faker(rng)
    full_name = faker.name()
    person_id = _slug_name(full_name) + f"-{rng.randint(1000, 9999)}"
    email = _email_from_name(full_name, rng)

    country_code, country = _pick_country(rng)
    loc_faker = _localized_faker(country_code, rng)
    city = loc_faker.city()
    region = _pick_region(loc_faker, rng)
    phone = _phone_for_country(rng, country_code, loc_faker)

    title = _pick_title(rng, faker)
    skills = _skill_list_for_persona(rng)
    years = rng.randint(1, 30)
    education = _build_education(faker, loc_faker, rng)
    company = faker.company()

    github_handle, github_is_real = _assign_github(
        rng, github_real_rate, github_fake_rate, person_id
    )

    headline = None
    if rng.random() < 0.75:
        headline = rng.choice([
            f"{title} at {company}",
            f"{title} · {company}",
            f"{title} | {faker.catch_phrase()}",
            faker.catch_phrase(),
        ])

    linkedin = None
    if rng.random() < 0.72:
        slug = _slug_name(full_name)
        if rng.random() < 0.15:
            slug += f"-{rng.randint(1, 999)}"
        linkedin = rng.choice([
            f"https://linkedin.com/in/{slug}",
            f"https://www.linkedin.com/in/{slug}/",
        ])

    persona = Persona(
        person_id=person_id,
        full_name=full_name,
        email=email,
        phone=phone,
        company=company,
        title=title,
        city=city,
        region=region,
        country=country,
        linkedin_url=linkedin,
        github_handle=github_handle,
        github_is_real=github_is_real,
        headline=headline,
        years_experience=years,
        skills=skills,
        education=education,
    )

    if rng.random() < 0.65:
        persona.notes_template = _build_notes_body(persona, rng)

    return persona


def baseline_source_presence(rng: random.Random) -> tuple[bool, bool, bool]:
    return (
        rng.random() < config.BASELINE_IN_CSV,
        rng.random() < config.BASELINE_IN_ATS,
        rng.random() < config.BASELINE_IN_NOTES,
    )
