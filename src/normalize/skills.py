"""Skill canonicalization and text extraction from unstructured notes.

Taxonomy maps many aliases (JS, k8s, Golang, ...) to one canonical name.
Unknown skills pass through lowercased — never dropped, never invented.
"""

from __future__ import annotations

import re

# canonical_name -> aliases 
SKILL_TAXONOMY: dict[str, list[str]] = {
    "javascript": ["javascript", "js", "ecmascript", "es6", "es2015"],
    "typescript": ["typescript", "ts"],
    "python": ["python", "py", "python3"],
    "go": ["go", "golang"],
    "rust": ["rust"],
    "java": ["java"],
    "kotlin": ["kotlin"],
    "scala": ["scala"],
    "c": ["c"],
    "cpp": ["c++", "cpp"],
    "csharp": ["c#", "csharp", "c sharp"],
    "ruby": ["ruby"],
    "php": ["php"],
    "swift": ["swift"],
    "sql": ["sql"],
    "bash": ["bash", "shell"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    # Frontend / UI
    "react": ["react", "react.js", "reactjs"],
    "vue": ["vue", "vue.js", "vuejs"],
    "angular": ["angular", "angularjs"],
    "nextjs": ["next.js", "nextjs", "next js"],
    "nuxt": ["nuxt", "nuxt.js", "nuxtjs"],
    "svelte": ["svelte", "sveltekit"],
    "solidjs": ["solidjs", "solid.js", "solid js"],
    "redux": ["redux"],
    "tailwind": ["tailwind", "tailwind css", "tailwindcss"],
    "svg": ["svg"],
    # Backend / runtime
    "nodejs": ["node.js", "nodejs", "node js"],
    "express": ["express", "express.js", "expressjs"],
    "django": ["django"],
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "spring": ["spring", "spring boot", "springboot"],
    "graphql": ["graphql"],
    "grpc": ["grpc"],
    # Data / messaging
    "postgresql": ["postgresql", "postgres", "psql"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch", "elastic search"],
    "dynamodb": ["dynamodb", "dynamo db"],
    "kafka": ["kafka", "apache kafka"],
    "rabbitmq": ["rabbitmq"],
    # Cloud / DevOps
    "aws": ["aws", "amazon web services"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "azure": ["azure", "microsoft azure"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s", "kube"],
    "terraform": ["terraform"],
    "ansible": ["ansible"],
    "jenkins": ["jenkins"],
    "github_actions": ["github actions", "gh actions"],
    "gitlab_ci": ["gitlab ci", "gitlab-ci"],
    "circleci": ["circleci", "circle ci"],
    "argocd": ["argocd", "argo cd"],
    "prometheus": ["prometheus"],
    "grafana": ["grafana"],
    "datadog": ["datadog"],
    "linux": ["linux"],
    "nginx": ["nginx"],
    # Tools / practices
    "git": ["git"],
    "github": ["github"],
    "jira": ["jira"],
    "agile": ["agile"],
    "scrum": ["scrum"],
    "ci_cd": ["ci/cd", "cicd", "ci cd", "continuous integration"],
    "microservices": ["microservices", "micro services"],
    "rest": ["rest", "rest api", "restful"],
    # Domain (Linus / systems)
    "kernel": ["kernel", "kernel-level", "kernel level"],
}


def _build_alias_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for canonical, aliases in SKILL_TAXONOMY.items():
        for alias in aliases:
            mapping[alias.lower()] = canonical
    return mapping


SKILL_ALIASES: dict[str, str] = _build_alias_map()

_SORTED_ALIAS_KEYS = sorted(SKILL_ALIASES.keys(), key=len, reverse=True)
_SKILL_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _SORTED_ALIAS_KEYS) + r")\b",
    re.IGNORECASE,
)


def canonicalize_skill(raw: str) -> str:
    key = raw.strip().lower()
    return SKILL_ALIASES.get(key, key)


def extract_skills_from_text(text: str) -> list[str]:
    """Return deduped canonical skills found in free text (order preserved)."""
    seen: set[str] = set()
    out: list[str] = []
    for match in _SKILL_PATTERN.finditer(text or ""):
        skill = canonicalize_skill(match.group(0))
        if skill not in seen:
            seen.add(skill)
            out.append(skill)
    return out
