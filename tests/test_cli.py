import json
import subprocess
import sys
from pathlib import Path


def test_cli_writes_profiles(tmp_path, curated_csv, curated_ats, curated_notes):
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "out.json"
    cmd = [
        sys.executable,
        "-m",
        "src.cli",
        "--csv",
        curated_csv,
        "--ats",
        curated_ats,
        "--notes",
        curated_notes,
        "--no-github",
        "--out",
        str(out),
    ]
    proc = subprocess.run(cmd, cwd=str(root), check=True)
    assert proc.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "profiles" in data
    assert len(data["profiles"]) == 14


def test_cli_custom_config(tmp_path, curated_csv, curated_ats, curated_notes):
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "custom.json"
    cmd = [
        sys.executable,
        "-m",
        "src.cli",
        "--csv",
        curated_csv,
        "--ats",
        curated_ats,
        "--notes",
        curated_notes,
        "--config",
        str(root / "configs" / "custom.json"),
        "--no-github",
        "--out",
        str(out),
    ]
    subprocess.run(cmd, cwd=str(root), check=True)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["profiles"]) == 7
    first = data["profiles"][0]
    assert "name" in first
    assert "full_name" not in first
