#!/usr/bin/env python3
"""Generate a reproducible, parameterized demonstration dataset for Z-Mirror.

Important: this is a toy generator based on explicit demonstration parameters.
It does not learn from a real dataset and does not provide a privacy guarantee.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "generated_candidate.csv"
COLUMNS = ["record_id", "age", "balance", "outcome"]
MAX_ROWS = 1_000_000
PROFILE = {
    "profile_name": "zmirror-demo-profile-v1",
    "age": {"distribution": "triangular", "minimum": 18, "maximum": 100, "mode": 42},
    "balance": {"distribution": "triangular", "minimum": -20000, "maximum": 100000, "mode": 7000},
    "outcome_rule": (
        "Demonstration heuristic, not learned from source data: base yes probability 0.25; "
        "+0.15 when balance >= 0; -0.05 when balance < 0; +0.10 when age is 30-60; "
        "clamped to [0.05, 0.85]."
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_rows(count: int, seed: int):
    rng = random.Random(seed)
    for index in range(1, count + 1):
        age = int(round(rng.triangular(18, 100, 42)))
        balance = int(round(rng.triangular(-20_000, 100_000, 7_000)))
        probability_yes = 0.25
        probability_yes += 0.15 if balance >= 0 else -0.05
        probability_yes += 0.10 if 30 <= age <= 60 else 0.0
        probability_yes = min(0.85, max(0.05, probability_yes))
        outcome = "yes" if rng.random() < probability_yes else "no"
        yield {
            "record_id": f"SYN{index:07d}",
            "age": str(age),
            "balance": str(balance),
            "outcome": outcome,
        }


def write_csv_atomically(path: Path, count: int, seed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temp_path = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(generate_rows(count, seed))
            handle.flush()
        temp_path.replace(path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def write_manifest_atomically(path: Path, manifest: dict) -> None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
        temp_path.replace(path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def run(count: int, seed: int, output: Path, force: bool) -> int:
    if count < 1 or count > MAX_ROWS:
        print(f"ERROR: --rows must be between 1 and {MAX_ROWS}.", file=sys.stderr)
        return 2

    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    if not force and (output.exists() or manifest_path.exists()):
        print(
            "ERROR: output or manifest already exists. Choose another --output path "
            "or pass --force to replace both deliberately.",
            file=sys.stderr,
        )
        return 2

    try:
        write_csv_atomically(output, count, seed)
        digest = sha256_file(output)
        manifest = {
            "generator": "zmirror-demo-parameterized-v1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "rows": count,
            "seed": seed,
            "schema": COLUMNS,
            "profile": PROFILE,
            "source_mode": "parameterized demonstration; no record-level source data consumed",
            "sha256": digest,
            "limitations": [
                "This generator uses hand-defined demo parameters, not a fitted model.",
                "The generated distribution is not evidence of utility for a real dataset.",
                "Synthetic output is not automatically anonymous or privacy-safe.",
            ],
        }
        write_manifest_atomically(manifest_path, manifest)
    except (OSError, ValueError) as error:
        print(f"ERROR: generation failed: {error}", file=sys.stderr)
        return 2

    print("SYNTHETIC DEMO GENERATION: PASS")
    print(f"Rows generated: {count}")
    print(f"Seed: {seed}")
    print(f"Output: {output}")
    print(f"Manifest: {manifest_path}")
    print(f"SHA-256: {digest}")
    print("Note: parameterized demo data; utility and privacy have not been evaluated.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=1000, help=f"rows to generate (1-{MAX_ROWS}; default 1000)")
    parser.add_argument("--seed", type=int, default=42, help="random seed for reproducibility (default 42)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output CSV path (default: data/generated_candidate.csv)")
    parser.add_argument("--force", action="store_true", help="replace existing output CSV and manifest")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else (Path.cwd() / args.output).resolve()
    return run(args.rows, args.seed, output, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
