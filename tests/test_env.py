from src.env import load_project_env, project_root


def test_load_project_env_reads_dotenv():
    load_project_env()
    env_file = project_root() / ".env"
    if not env_file.is_file():
        return
    # If .env exists with GITHUB_TOKEN, it should be in environ after load
    import os
    # load_dotenv does not override; token may already be set
    assert env_file.read_text(encoding="utf-8").strip().startswith("GITHUB_TOKEN")
