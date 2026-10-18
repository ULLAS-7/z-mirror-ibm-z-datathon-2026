#!/usr/bin/env python3
"""Experimental aggregate/histogram-based Z-Mirror V3 generator.

This is a utility experiment, not a formal privacy mechanism.
It samples from aggregate group counts and coarse balance histograms;
it does not copy complete source records.
"""
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "data/reference_candidate.csv"
V2 = ROOT / "data/generated_candidate_v2.csv"
OUT = ROOT / "data/generated_candidate_v3.csv"
WIDTH = 500
ROWS = 1000
SEED = 42
COLUMNS = ["record_id", "age", "balance", "outcome"]


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def age_group(age):
    if 18 <= age <= 29:
        return "18-29"
    if 30 <= age <= 44:
        return "30-44"
    if 45 <= age <= 60:
        return "45-60"
    if age >= 61:
        return "61+"
    raise ValueError(f"Age outside supported range: {age}")


def balance_sign(balance):
    if balance < 0:
        return "negative"
    if balance == 0:
        return "zero"
    return "positive"


def weighted_pick(rng, items, weights):
    if not items or len(items) != len(weights) or sum(weights) <= 0:
        raise ValueError("Invalid weighted-sampling inputs")
    target = rng.random() * sum(weights)
    cumulative = 0
    for item, weight in zip(items, weights):
        cumulative += weight
        if target < cumulative:
            return item
    return items[-1]


def main():
    if not REF.is_file() or not V2.is_file():
        raise SystemExit("Missing reference or V2 CSV; no files were generated.")
    manifest_path = OUT.with_suffix(OUT.suffix + ".manifest.json")
    if OUT.exists() or manifest_path.exists():
        raise SystemExit(
            "V3 output already exists. Nothing overwritten; inspect or rename it first."
        )

    ref = pd.read_csv(REF)
    if list(ref.columns) != COLUMNS:
        raise SystemExit(f"Unexpected reference schema: {list(ref.columns)}")

    ref["age"] = pd.to_numeric(ref["age"], errors="raise").astype(int)
    ref["balance"] = pd.to_numeric(ref["balance"], errors="raise").astype(int)
    ref["outcome"] = ref["outcome"].astype(str).str.strip().str.lower()

    if ref[COLUMNS].isna().any().any():
        raise SystemExit("Reference contains missing values; stopping.")
    if not set(ref["outcome"]).issubset({"yes", "no"}):
        raise SystemExit("Unexpected outcome values; stopping.")

    ref["age_group"] = ref["age"].map(age_group)
    ref["balance_sign"] = ref["balance"].map(balance_sign)
    ref["balance_bin"] = (ref["balance"] // WIDTH).astype(int)

    # Only coarse counts are used for balance generation.
    # Zero balance remains its own category.
    joint = ref.groupby(
        ["age_group", "balance_sign"], observed=True
    ).size().to_dict()
    joint_items = list(joint.keys())
    joint_weights = [int(joint[x]) for x in joint_items]

    age_hist = {}
    for group, part in ref.groupby("age_group", observed=True):
        counts = part["age"].value_counts().sort_index()
        age_hist[group] = (
            [int(x) for x in counts.index],
            [int(x) for x in counts.values],
        )

    bin_hist = {}
    nonzero = ref[ref["balance"] != 0]
    for sign, part in nonzero.groupby("balance_sign", observed=True):
        counts = part["balance_bin"].value_counts().sort_index()
        bin_hist[sign] = (
            [int(x) for x in counts.index],
            [int(x) for x in counts.values],
        )

    outcome_counts = ref.groupby(
        ["age_group", "balance_sign", "outcome"], observed=True
    ).size().to_dict()

    rng = random.Random(SEED)
    records = []
    min_balance, max_balance = int(ref["balance"].min()), int(ref["balance"].max())

    for i in range(1, ROWS + 1):
        group, sign = weighted_pick(rng, joint_items, joint_weights)

        ages, age_weights = age_hist[group]
        age = weighted_pick(rng, ages, age_weights)

        if sign == "zero":
            balance = 0
        else:
            bins, bin_weights = bin_hist[sign]
            bin_id = weighted_pick(rng, bins, bin_weights)
            low = max(min_balance, bin_id * WIDTH)
            high = min(max_balance, bin_id * WIDTH + WIDTH - 1)
            if sign == "negative":
                high = min(high, -1)
            else:
                low = max(low, 1)
            if low > high:
                raise ValueError(f"Invalid balance bin bounds: {low}, {high}")
            balance = rng.randint(low, high)

        yes_n = int(outcome_counts.get((group, sign, "yes"), 0))
        no_n = int(outcome_counts.get((group, sign, "no"), 0))

        # Add-one smoothing to stabilize group probabilities.
        # This is NOT differential privacy.
        p_yes = (yes_n + 1) / (yes_n + no_n + 2)
        outcome = "yes" if rng.random() < p_yes else "no"

        records.append({
            "record_id": f"SYN3_{i:06d}",
            "age": int(age),
            "balance": int(balance),
            "outcome": outcome,
        })

    candidate = pd.DataFrame(records, columns=COLUMNS)
    candidate.to_csv(OUT, index=False, lineterminator="\n")
    candidate_hash = sha256(OUT)

    manifest = {
        "generator": "zmirror-aggregate-histogram-v3",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "rows": ROWS,
        "schema": COLUMNS,
        "reference_sha256": sha256(REF),
        "generated_sha256": candidate_hash,
        "balance_bin_width": WIDTH,
        "method": (
            "Weighted age-group/balance-sign aggregate cells; age sampled "
            "from age histograms; balance sampled within weighted fixed-width "
            "histogram bins; add-one-smoothed outcome rates."
        ),
        "limitations": [
            "Experimental aggregate-based sampler; not differential privacy.",
            "No formal anonymity or disclosure-risk guarantee.",
            "Histogram counts and group statistics may still leak information.",
            "Utility acceptance thresholds are not defined.",
            "COBOL execution is not tested by this generator."
        ]
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    # Evaluate V2 and V3 against the same reference using the same measures.
    v2 = pd.read_csv(V2)
    v3 = pd.read_csv(OUT)
    for df in (ref, v2, v3):
        df["age"] = pd.to_numeric(df["age"], errors="raise")
        df["balance"] = pd.to_numeric(df["balance"], errors="raise")
        df["outcome"] = df["outcome"].astype(str).str.strip().str.lower()

    def summarize(df):
        result = {"rows": int(len(df))}
        for col in ("age", "balance"):
            s = df[col].dropna()
            result[col] = {
                "mean": float(s.mean()),
                "median": float(s.median()),
                "p95": float(s.quantile(.95)),
                "p99": float(s.quantile(.99)),
                "ks_vs_reference": float(
                    ks_2samp(ref[col].dropna(), s).statistic
                ),
            }
        yes_rate = float((df["outcome"] == "yes").mean())
        ref_yes_rate = float((ref["outcome"] == "yes").mean())
        result["outcome_yes_rate"] = yes_rate
        result["outcome_yes_rate_gap_pp"] = abs(
            yes_rate - ref_yes_rate
        ) * 100
        return result

    results = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reference": {
            "rows": int(len(ref)),
            "sha256": sha256(REF),
            "age": {"mean": float(ref["age"].mean()),
                    "median": float(ref["age"].median()),
                    "p95": float(ref["age"].quantile(.95)),
                    "p99": float(ref["age"].quantile(.99))},
            "balance": {"mean": float(ref["balance"].mean()),
                        "median": float(ref["balance"].median()),
                        "p95": float(ref["balance"].quantile(.95)),
                        "p99": float(ref["balance"].quantile(.99))},
            "outcome_yes_rate": float((ref["outcome"] == "yes").mean()),
        },
        "v2": summarize(v2),
        "v3": summarize(v3),
        "v3_sha256": candidate_hash,
        "v3_manifest_sha256_matches": (
            json.loads(manifest_path.read_text())["generated_sha256"]
            == sha256(OUT)
        ),
        "interpretation": [
            "Lower KS distance indicates closer empirical marginal distributions.",
            "Distribution similarity is not a privacy score.",
            "No utility acceptance threshold or utility PASS is assigned.",
            "Results do not establish anonymity, differential privacy, or production fitness."
        ]
    }

    report_path = ROOT / "reports/utility_comparison_v3_20261018.json"
    summary_path = ROOT / "reports/UTILITY_V3_SUMMARY_20261018.md"
    report_path.write_text(json.dumps(results, indent=2) + "\n")

    lines = [
        "# Z-Mirror V3 — Experimental Utility Comparison", "",
        f"- Reference rows: {len(ref):,}",
        f"- V2 rows: {len(v2):,}",
        f"- V3 rows: {len(v3):,}",
        f"- V3 SHA-256: `{candidate_hash}`",
        f"- Manifest hash matches CSV: {results['v3_manifest_sha256_matches']}",
        "",
        "| Measure | Reference | V2 | V3 |",
        "|---|---:|---:|---:|",
    ]
    for col in ("age", "balance"):
        for metric in ("mean", "median", "p95", "p99"):
            lines.append(
                f"| {col} {metric} | {results['reference'][col][metric]:.2f} "
                f"| {results['v2'][col][metric]:.2f} "
                f"| {results['v3'][col][metric]:.2f} |"
            )
        lines.append(
            f"| {col} KS distance vs reference | 0.0000 "
            f"| {results['v2'][col]['ks_vs_reference']:.4f} "
            f"| {results['v3'][col]['ks_vs_reference']:.4f} |"
        )
    lines.extend([
        f"| Outcome yes rate | {results['reference']['outcome_yes_rate']:.4%} "
        f"| {results['v2']['outcome_yes_rate']:.4%} "
        f"| {results['v3']['outcome_yes_rate']:.4%} |",
        "",
        "## Interpretation",
        "",
        "- Compare V3 with V2; do not assume V3 is better before reviewing results.",
        "- KS distances describe marginal distribution differences, not privacy.",
        "- No acceptance thresholds are defined; no utility PASS is assigned.",
        "- No formal privacy guarantee is provided.",
        "- COBOL compatibility remains untested.",
        "",
    ])
    summary_path.write_text("\n".join(lines))

    print("=== V3 EXPERIMENT COMPLETE ===")
    print(f"Candidate: {OUT}")
    print(f"Manifest:  {manifest_path}")
    print(f"JSON:      {report_path}")
    print(f"Summary:   {summary_path}")
    print(f"V3 SHA-256: {candidate_hash}")
    print(f"Manifest matches CSV: {results['v3_manifest_sha256_matches']}")
    print("\nBalance KS: V2 =", round(results["v2"]["balance"]["ks_vs_reference"], 4),
          "| V3 =", round(results["v3"]["balance"]["ks_vs_reference"], 4))
    print("Balance mean: reference =", round(results["reference"]["balance"]["mean"], 2),
          "| V2 =", round(results["v2"]["balance"]["mean"], 2),
          "| V3 =", round(results["v3"]["balance"]["mean"], 2))
    print("Outcome yes-rate gap (pp): V2 =",
          round(results["v2"]["outcome_yes_rate_gap_pp"], 4),
          "| V3 =", round(results["v3"]["outcome_yes_rate_gap_pp"], 4))
    print("\nNo privacy or utility acceptance PASS is claimed.")


if __name__ == "__main__":
    main()
