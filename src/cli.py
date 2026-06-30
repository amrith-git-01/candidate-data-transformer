"""CLI entrypoint: explicit file flags in, JSON out."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from src.env import load_project_env
from src.pipeline import default_config_path, run_pipeline_from_paths
from src.validate.validator import ValidationError

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


DEFAULT_CONFIG_PATH = default_config_path()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Multi-source candidate data transformer",
    )
    parser.add_argument("--csv", help="Path to recruiter CSV export")
    parser.add_argument("--ats", help="Path to ATS JSON export")
    parser.add_argument("--notes", help="Path to recruiter notes .txt")
    parser.add_argument(
        "--config",
        help=f"Projection config JSON (default: {DEFAULT_CONFIG_PATH.name} in configs/)",
    )
    parser.add_argument("--out", required=True, help="Output JSON file path")
    parser.add_argument(
        "--no-github",
        action="store_true",
        help="Skip GitHub enrichment even if links are present",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_project_env()
    parser = build_parser()
    args = parser.parse_args(argv)

    if not any([args.csv, args.ats, args.notes]):
        parser.error("At least one of --csv, --ats, or --notes is required")

    try:
        result = run_pipeline_from_paths(
            csv_path=args.csv,
            ats_path=args.ats,
            notes_path=args.notes,
            config_path=args.config,
            enrich_github=not args.no_github,
        )
    except ValidationError as exc:
        logger.error("%s", exc)
        return 1
    except ValueError as exc:
        logger.error("%s", exc)
        return 2

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info("Wrote %d profile(s) to %s", len(result["profiles"]), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
