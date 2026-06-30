"""CLI for sample data generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sample_generator.config import DEFAULT_GITHUB_FAKE_RATE, DEFAULT_GITHUB_REAL_RATE
from sample_generator.orchestrator import generate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate rich multi-source candidate sample data",
    )
    parser.add_argument("--count", type=int, default=1000, help="Unique personas to generate")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("sample_data"),
        help="Output directory (overwritten)",
    )
    parser.add_argument(
        "--github-real-rate",
        type=float,
        default=DEFAULT_GITHUB_REAL_RATE,
        help="Fraction of personas with real GitHub handles",
    )
    parser.add_argument(
        "--github-fake-rate",
        type=float,
        default=DEFAULT_GITHUB_FAKE_RATE,
        help="Fraction of personas with fake GitHub handles",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.count < 1:
        parser.error("--count must be at least 1")

    out_dir: Path = args.out
    manifest = generate(
        count=args.count,
        seed=args.seed,
        out_dir=out_dir,
        github_real_rate=args.github_real_rate,
        github_fake_rate=args.github_fake_rate,
    )
    print(
        f"Generated {args.count} personas -> {out_dir} "
        f"(csv={manifest.source_counts['csv_rows']}, "
        f"ats={manifest.source_counts['ats_candidates']}, "
        f"notes={manifest.source_counts['notes_sections']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
