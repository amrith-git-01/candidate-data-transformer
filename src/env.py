"""Load project-level environment variables from .env."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_LOADED = False


def load_project_env() -> None:
    """Load .env from repo root into os.environ (does not override existing vars)."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_path = _PROJECT_ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
    _ENV_LOADED = True


def project_root() -> Path:
    return _PROJECT_ROOT
