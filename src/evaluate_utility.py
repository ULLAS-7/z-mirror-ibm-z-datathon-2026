#!/usr/bin/env python3
"""Compare a candidate CSV with a reference CSV using descriptive metrics only.
This tool does not decide privacy, anonymity, or release readiness.
"""
import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

REQUIRED_COLUMNS = ["record_id", "age", "balance", "outcome"]


def read_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != REQUIRED_COLUMNS:
            raise ValueError(f"{path}: header must be exactly {REQUIRED_COLUMNS}")
        rows, seen = [], set()
        for line, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"{path}: line {line} has extra fields")
            if any(row.get(k) is None for k in REQUIRED_COLUMNS):
                raise ValueError(f"{path}: line {line} has missing fields")
            rid = row["record_id"].strip()
            if not rid:
                raise ValueError(f"{path}: line {line} has an empty record_id")
            if rid in seen:
                raise ValueError(f"{path}: line {line} has duplicate record_id {rid!r}")
            seen.add(rid)
            try:
                age, balance = int(row["age"]), int(row["balance"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{path}: line {line} age and balance must be integers") from exc
            outcome = row["outcome"].strip().lower()
            if outcome not in {"yes", "no"}:
                raise ValueError(f"{path}: line {line} outcome must be yes/no")
            rows.append({"record_id": rid, "age": age, "balance": balance, "outcome": outcome})
    if not rows:
        raise ValueError(f"{path}: no data rows")
    return rows


def ks_statistic(a, b):
    """Two-sample empirical KS distance (not a p-value), range [0, 1]."""
    x, y = sorted(a), sorted(b)
    i = j = 0
    best = 0.0
    while i < len(x) or j < len(y):
        if j >= len(y) or (i < len(x) and x[i] <= y[j]):
            value = x[i]
        else:
            value = y[j]
        while i < len(x) and x[i] <= value:
            i += 1
        while j < len(y) and y[j] <= value:
            j += 1
        best = max(best, abs(i / len(x) - j / len(y)))
    return best


def numeric_summary(xs):
    sx = sorted(xs)
    def quantile(p):
        pos = p * (len(sx) - 1)
        lo, hi = math.floor(pos), math.ceil(pos)
        return sx[lo] if lo == hi else sx[lo] * (hi - pos) + sx[hi] * (pos - lo)
    return {
        "n": len(xs), "mean": statistics.mean(xs), "median": statistics.median(xs),
        "stdev_sample": statistics.stdev(xs) if len(xs) > 1 else 0.0,
        "min": min(xs), "q1": quantile(0.25), "q3": quantile(0.75), "max": max(xs)
    }


def group_yes_rates(rows, group_fn):
    groups = {}
    for r in rows:
        g = group_fn(r)
        stats = groups.setdefault(g, {"n": 0, "yes": 0})
        stats["n"] += 1
        stats["yes"] += (r["outcome"] == "yes")
    return {k: {"n": v["n"], "yes_rate": v["yes"] / v["n"]} for k, v in sorted(groups.items())}


def rate_differences(reference_groups, candidate_groups):
    out = {}
    for group in sorted(reference_groups.keys() | candidate_groups.keys()):
        if group not in reference_groups or group not in candidate_groups:
            out[group] = {"status": "GROUP_PRESENT_IN_ONLY_ONE_DATASET"}
        else:
            rr, cr = reference_groups[group], candidate_groups[group]
            out[group] = {
                "reference_n": rr["n"], "candidate_n": cr["n"],
                "reference_yes_rate": rr["yes_rate"], "candidate_yes_rate": cr["yes_rate"],
                "absolute_yes_rate_difference": abs(rr["yes_rate"] - cr["yes_rate"])
            }
    return out


def exact_tuple_overlap(reference, candidate):
    r = Counter((x["age"], x["balance"], x["outcome"]) for x in reference)
    c = Counter((x["age"], x["balance"], x["outcome"]) for x in candidate)
    shared = r.keys() & c.keys()
    return {
        "distinct_shared_age_balance_outcome_tuples": len(shared),
        "matched_record_multiplicity": sum(min(r[k], c[k]) for k in shared),
        "interpretation": "Reference-overlap diagnostic only. The reference is public benchmark data; this is NOT a privacy-risk score or anonymity guarantee."
    }


def evaluate(reference, candidate):
    r_age, c_age = [x["age"] for x in reference], [x["age"] for x in candidate]
    r_bal, c_bal = [x["balance"] for x in reference], [x["balance"] for x in candidate]
    r_yes = sum(x["outcome"] == "yes" for x in reference) / len(reference)
    c_yes = sum(x["outcome"] == "yes" for x in candidate) / len(candidate)
    age_group = lambda x: "under_30" if x["age"] < 30 else ("30_to_49" if x["age"] < 50 else "50_plus")
    bal_group = lambda x: "negative" if x["balance"] < 0 else ("zero" if x["balance"] == 0 else "positive")
    ra, ca = group_yes_rates(reference, age_group), group_yes_rates(candidate, age_group)
    rb, cb = group_yes_rates(reference, bal_group), group_yes_rates(candidate, bal_group)
    return {
        "status": "MEASUREMENT_ONLY_THRESHOLDS_NOT_CONFIGURED",
        "reference_rows": len(reference), "candidate_rows": len(candidate),
        "numeric_comparison": {
            "age": {"reference": numeric_summary(r_age), "candidate": numeric_summary(c_age),
                    "absolute_mean_difference": abs(statistics.mean(r_age) - statistics.mean(c_age)),
                    "ks_distance": ks_statistic(r_age, c_age)},
            "balance": {"reference": numeric_summary(r_bal), "candidate": numeric_summary(c_bal),
                        "absolute_mean_difference": abs(statistics.mean(r_bal) - statistics.mean(c_bal)),
                        "ks_distance": ks_statistic(r_bal, c_bal)}
        },
        "outcome": {"reference_yes_rate": r_yes, "candidate_yes_rate": c_yes,
                    "absolute_yes_rate_difference": abs(r_yes - c_yes)},
        "conditional_outcome_rates": {
            "by_age_group": rate_differences(ra, ca),
            "by_balance_sign": rate_differences(rb, cb)
        },
        "reference_overlap_diagnostic": exact_tuple_overlap(reference, candidate),
        "limitations": [
            "The current candidate generator uses hand-defined demo parameters rather than a fitted model.",
            "Distribution differences measure mismatch for selected fields, not overall utility for every task.",
            "No thresholds are configured; this report makes no PASS/FAIL decision.",
            "The public benchmark is not a confidential source; overlap does not establish privacy safety.",
            "No formal differential privacy or anonymity guarantee is implemented."
        ]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        reference, candidate = read_rows(args.reference), read_rows(args.candidate)
        report = evaluate(reference, candidate)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output.with_suffix(args.output.suffix + ".tmp")
        temp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(args.output)
        print("UTILITY MEASUREMENT: COMPLETE")
        print(f"Reference rows: {report['reference_rows']}")
        print(f"Candidate rows: {report['candidate_rows']}")
        for field in ("age", "balance"):
            item = report["numeric_comparison"][field]
            print(f"{field}: reference mean={item['reference']['mean']:.4f}; candidate mean={item['candidate']['mean']:.4f}; KS distance={item['ks_distance']:.4f}")
        out = report["outcome"]
        print(f"outcome yes-rate: reference={out['reference_yes_rate']:.4f}; candidate={out['candidate_yes_rate']:.4f}; abs_difference={out['absolute_yes_rate_difference']:.4f}")
        print(f"Reference-overlap diagnostic: {report['reference_overlap_diagnostic']['matched_record_multiplicity']} matched tuples (not a privacy score)")
        print(f"Report: {args.output}")
        print("Decision: NOT MADE (thresholds not configured)")
    except (OSError, ValueError, csv.Error) as exc:
        print(f"UTILITY MEASUREMENT: ERROR: {exc}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
