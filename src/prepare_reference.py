#!/usr/bin/env python3
"""Prepare an attributed, minimal reference CSV from UCI Bank Marketing bank-full.csv.

Input: semicolon-delimited bank-full.csv from the UCI Bank Marketing dataset.
Output: record_id,age,balance,outcome. This is data preparation, not generation.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

COLUMNS = ["record_id", "age", "balance", "outcome"]
SOURCE_NAME = "Bank Marketing"
SOURCE_CITATION = "Moro, S., Rita, P., & Cortez, P. (2014). Bank Marketing. UCI Machine Learning Repository."
SOURCE_DOI = "https://doi.org/10.24432/C5K306"
SOURCE_LICENSE = "Creative Commons Attribution 4.0 International (CC BY 4.0)"


def prepare(input_path: Path, output_path: Path) -> int:
    records = []
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        required = {"age", "balance", "y"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("Input must be UCI bank-full.csv with age, balance and y columns.")
        for idx, row in enumerate(reader, start=2):
            try:
                age = int(row["age"])
                balance = int(row["balance"])
                outcome = (row["y"] or "").strip().lower()
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid row {idx}: age/balance must be integers.") from exc
            if outcome not in {"yes", "no"}:
                raise ValueError(f"Invalid row {idx}: y must be yes or no.")
            records.append({"record_id": f"REF{idx-1:08d}", "age": age, "balance": balance, "outcome": outcome})
    if not records:
        raise ValueError("Reference dataset contained no records.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp = output_path.with_suffix(output_path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    temp.replace(output_path)

    manifest = {
        "source_name": SOURCE_NAME,
        "citation": SOURCE_CITATION,
        "doi": SOURCE_DOI,
        "license": SOURCE_LICENSE,
        "input_file": input_path.name,
        "output_file": output_path.name,
        "rows": len(records),
        "columns": COLUMNS,
        "mapping": {"age": "age", "balance": "balance", "y": "outcome"},
        "record_id_note": "REF-prefixed sequential identifiers added during preparation; not source identifiers.",
        "purpose": "Public benchmark reference for an educational utility-measurement baseline.",
        "limitations": [
            "Only age, balance and outcome are retained; all other features are omitted.",
            "The public reference dataset is not a confidential source dataset.",
            "Attribution is required under the stated CC BY 4.0 license."
        ]
    }
    manifest_path = output_path.with_suffix(output_path.suffix + ".manifest.json")
    mtemp = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    mtemp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    mtemp.replace(manifest_path)
    print("REFERENCE PREPARATION: PASS")
    print(f"Rows prepared: {len(records)}")
    print(f"CSV: {output_path}")
    print(f"Manifest: {manifest_path}")
    print(f"Source DOI: {SOURCE_DOI}")
    print(f"License: {SOURCE_LICENSE}")
    return len(records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path, help="Path to semicolon-delimited UCI bank-full.csv")
    parser.add_argument("--output", required=True, type=Path, help="Output normalized reference CSV")
    args = parser.parse_args()
    try:
        prepare(args.input, args.output)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"REFERENCE PREPARATION: FAIL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
