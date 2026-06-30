"""Generator configuration: weights, pools, rates."""

from __future__ import annotations

SCENARIO_WEIGHTS: dict[str, float] = {
    "happy_path": 0.40,
    "title_conflict": 0.08,
    "email_typo": 0.05,
    "phone_join": 0.05,
    "csv_only": 0.06,
    "ats_notes_only": 0.05,
    "notes_only": 0.04,
    "glitch_email": 0.02,
    "github_text_only": 0.03,
    "github_404": 0.02,
    "csv_duplicate": 0.03,
}

INCOMPATIBLE_TAGS: set[frozenset[str]] = {
    frozenset({"notes_only", "csv_only"}),
    frozenset({"notes_only", "ats_notes_only"}),
    frozenset({"notes_only", "happy_path"}),
    frozenset({"csv_only", "ats_notes_only"}),
    frozenset({"csv_only", "phone_join"}),
    frozenset({"notes_only", "phone_join"}),
    frozenset({"glitch_email", "email_typo"}),
}

SECONDARY_TAG_CHANCE = 0.15

BASELINE_IN_CSV = 0.85
BASELINE_IN_ATS = 0.80
BASELINE_IN_NOTES = 0.60

DEFAULT_GITHUB_REAL_RATE = 0.03
DEFAULT_GITHUB_FAKE_RATE = 0.02

# Multi-locale Faker for names, cities, companies, and job titles.
FAKER_LOCALES = [
    "en_US",
    "en_GB",
    "en_CA",
    "en_AU",
    "en_IN",
    "de_DE",
    "fr_FR",
    "es_ES",
    "it_IT",
    "pt_BR",
    "ja_JP",
    "ko_KR",
    "nl_NL",
    "pl_PL",
    "no_NO",
]

# Mix curated engineering titles with Faker job titles.
TITLE_USE_FAKER_RATE = 0.45

REAL_GITHUB_HANDLES = [
    "torvalds",
    "gaearon",
    "sindresorhus",
    "yyx990803",
    "ryansolid",
    "sdras",
    "addyosmani",
    "evanw",
    "tj",
    "antfu",
    "getify",
    "wesbos",
]

TITLE_POOL = [
    "Software Engineer",
    "Senior Software Engineer",
    "Staff Software Engineer",
    "Principal Engineer",
    "Engineering Lead",
    "Engineering Manager",
    "Technical Lead",
    "Open Source Maintainer",
    "DevOps Engineer",
    "Platform Engineer",
    "Data Engineer",
    "Machine Learning Engineer",
    "Security Engineer",
    "Site Reliability Engineer",
    "Full Stack Developer",
    "Backend Developer",
    "Frontend Developer",
    "Founder",
    "CTO",
    "Fellow",
    "Creator",
    "Architect",
]

ALT_TITLE_SUFFIXES = [
    "Staff Software Engineer",
    "Senior Engineer",
    "Lead Engineer",
    "Principal Engineer",
    "Engineering Manager",
    "Staff Engineer",
    "Distinguished Engineer",
]

# Mirrors src/normalize/skills.py taxonomy keys so extractor + canonicalizer align.
SKILL_POOL = [
    "javascript",
    "typescript",
    "python",
    "go",
    "rust",
    "java",
    "kotlin",
    "scala",
    "c",
    "cpp",
    "csharp",
    "ruby",
    "php",
    "swift",
    "sql",
    "bash",
    "html",
    "css",
    "react",
    "vue",
    "angular",
    "nextjs",
    "nuxt",
    "svelte",
    "solidjs",
    "redux",
    "tailwind",
    "nodejs",
    "express",
    "django",
    "fastapi",
    "flask",
    "spring",
    "graphql",
    "grpc",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "elasticsearch",
    "dynamodb",
    "kafka",
    "rabbitmq",
    "aws",
    "gcp",
    "azure",
    "docker",
    "kubernetes",
    "terraform",
    "ansible",
    "jenkins",
    "github_actions",
    "gitlab_ci",
    "circleci",
    "argocd",
    "prometheus",
    "grafana",
    "datadog",
    "linux",
    "nginx",
    "git",
    "github",
    "jira",
    "agile",
    "scrum",
    "ci_cd",
    "microservices",
    "rest",
    "kernel",
]

# Aliases sprinkled into notes text to exercise skill extraction.
SKILL_NOTE_ALIASES = [
    "JS",
    "TS",
    "k8s",
    "Golang",
    "Node.js",
    "Postgres",
    "React.js",
    "CI/CD",
]

DEGREE_POOL = [
    "BS",
    "BA",
    "BSc",
    "BEng",
    "MS",
    "MSc",
    "MA",
    "MBA",
    "MEng",
    "PhD",
    "BCS",
    "Associate",
    "Certificate",
]

FIELD_POOL = [
    "Computer Science",
    "Software Engineering",
    "Applied Mathematics",
    "Information Systems",
    "Electrical Engineering",
    "Computer Engineering",
    "Data Science",
    "Statistics",
    "Physics",
    "Business Administration",
    "Information Technology",
    "Cybersecurity",
    "Human-Computer Interaction",
]

# (iso_code, variant, variant, ...) — mixed forms stress the location normalizer.
COUNTRY_VARIANTS: list[tuple[str, ...]] = [
    ("US", "USA", "United States"),
    ("CA", "Canada", "CA"),
    ("GB", "UK", "United Kingdom", "Great Britain"),
    ("DE", "Germany", "DE"),
    ("FR", "France", "FR"),
    ("NO", "Norway", "NO"),
    ("SG", "Singapore", "SG"),
    ("AU", "Australia", "AU"),
    ("IN", "India", "IN"),
    ("BR", "Brazil", "BR"),
    ("JP", "Japan", "JP"),
    ("KR", "South Korea", "Korea"),
    ("NL", "Netherlands", "NL"),
    ("ES", "Spain", "ES"),
    ("IT", "Italy", "IT"),
    ("PL", "Poland", "PL"),
    ("MX", "Mexico", "MX"),
    ("SE", "Sweden", "SE"),
    ("IE", "Ireland", "IE"),
    ("NZ", "New Zealand", "NZ"),
]

# ISO code → Faker locale for city/region generation.
COUNTRY_LOCALE: dict[str, str] = {
    "US": "en_US",
    "CA": "en_CA",
    "GB": "en_GB",
    "DE": "de_DE",
    "FR": "fr_FR",
    "NO": "no_NO",
    "SG": "en_US",
    "AU": "en_AU",
    "IN": "en_IN",
    "BR": "pt_BR",
    "JP": "ja_JP",
    "KR": "ko_KR",
    "NL": "nl_NL",
    "ES": "es_ES",
    "IT": "it_IT",
    "PL": "pl_PL",
    "MX": "es_MX",
    "SE": "sv_SE",
    "IE": "en_IE",
    "NZ": "en_NZ",
}
