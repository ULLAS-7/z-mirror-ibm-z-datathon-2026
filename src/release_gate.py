#!/usr/bin/env python3
"""Z-Mirror evidence-based release gate. No formal privacy guarantee."""

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"

REF = DATA / "reference_candidate.csv"
V2 = DATA / "generated_candidate_v2.csv"
V3 = DATA / "generated_candidate_v3.csv"
MANIFEST = DATA / "generated_candidate_v3.csv.manifest.json"

COLUMNS = ["record_id", "age", "balance", "outcome"]

# Illustrative prototype targets only; these are NOT formal or approved
# enterprise acceptance criteria and are NOT privacy thresholds.
THRESHOLDS = {
    "age_ks_max": 0.03,
    "balance_ks_max": 0.10,
    "balance_mean_relative_error_max": 0.10,
    "balance_p95_relative_error_max": 0.10,
    "outcome_yes_gap_pp_max": 2.0,
}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def utility_metrics(reference, candidate):
    result = {}

    for col in ("age", "balance"):
        a = reference[col].dropna()
        b = candidate[col].dropna()
        result[f"{col}_ks"] = float(ks_2samp(a, b).statistic)

    ref_balance_mean = float(reference["balance"].mean())
    syn_balance_mean = float(candidate["balance"].mean())
    ref_balance_p95 = float(reference["balance"].quantile(0.95))
    syn_balance_p95 = float(candidate["balance"].quantile(0.95))

    result["balance_mean_reference"] = ref_balance_mean
    result["balance_mean_candidate"] = syn_balance_mean
    result["balance_mean_relative_error"] = (
        abs(syn_balance_mean - ref_balance_mean) / abs(ref_balance_mean)
        if ref_balance_mean != 0 else None
    )
    result["balance_p95_reference"] = ref_balance_p95
    result["balance_p95_candidate"] = syn_balance_p95
    result["balance_p95_relative_error"] = (
        abs(syn_balance_p95 - ref_balance_p95) / abs(ref_balance_p95)
        if ref_balance_p95 != 0 else None
    )

    ref_yes = float((reference["outcome"] == "yes").mean())
    syn_yes = float((candidate["outcome"] == "yes").mean())
    result["outcome_yes_rate_reference"] = ref_yes
    result["outcome_yes_rate_candidate"] = syn_yes
    result["outcome_yes_gap_pp"] = abs(ref_yes - syn_yes) * 100

    return result


def evaluate_utility_thresholds(metrics):
    """Evaluate illustrative utility targets; never implies privacy safety."""
    checks = {
        "age_ks_within_target":
            metrics["age_ks"] <= THRESHOLDS["age_ks_max"],
        "balance_ks_within_target":
            metrics["balance_ks"] <= THRESHOLDS["balance_ks_max"],
        "balance_mean_error_within_target":
            metrics["balance_mean_relative_error"] is not None
            and metrics["balance_mean_relative_error"]
            <= THRESHOLDS["balance_mean_relative_error_max"],
        "balance_p95_error_within_target":
            metrics["balance_p95_relative_error"] is not None
            and metrics["balance_p95_relative_error"]
            <= THRESHOLDS["balance_p95_relative_error_max"],
        "outcome_gap_within_target":
            metrics["outcome_yes_gap_pp"]
            <= THRESHOLDS["outcome_yes_gap_pp_max"],
    }
    return checks


def decide_release(integrity_status, privacy_status, cobol_status):
    """Fail closed; successful checks permit review, never automatic approval."""
    if integrity_status != "PASS":
        return "NOT_APPROVED_INTEGRITY_FAILURE"

    privacy_ok = privacy_status == "PASS"
    cobol_ok = cobol_status == "PASS"

    if not privacy_ok and not cobol_ok:
        return "NOT_APPROVED_PRIVACY_AND_COBOL_CHECKS_PENDING"
    if not privacy_ok:
        return "NOT_APPROVED_PRIVACY_ASSURANCE_PENDING"
    if not cobol_ok:
        return "NOT_APPROVED_COBOL_EXECUTION_PENDING"

    return "ELIGIBLE_FOR_HUMAN_REVIEW_NOT_AUTOMATIC_APPROVAL"


def run():
    for path in (REF, V2, V3, MANIFEST):
        if not path.is_file():
            raise FileNotFoundError(f"Required artifact missing: {path}")

    ref = pd.read_csv(REF)
    v2 = pd.read_csv(V2)
    v3 = pd.read_csv(V3)
    manifest = json.loads(MANIFEST.read_text())

    schema_checks = {
        "reference_schema_valid": list(ref.columns) == COLUMNS,
        "v2_schema_valid": list(v2.columns) == COLUMNS,
        "v3_schema_valid": list(v3.columns) == COLUMNS,
    }
    if not all(schema_checks.values()):
        raise ValueError(f"Schema failure: {schema_checks}")

    for name, frame in (("reference", ref), ("v2", v2), ("v3", v3)):
        frame["age"] = pd.to_numeric(frame["age"], errors="raise")
        frame["balance"] = pd.to_numeric(frame["balance"], errors="raise")
        frame["outcome"] = frame["outcome"].astype(str).str.strip().str.lower()
        if frame[["age", "balance", "outcome"]].isna().any().any():
            raise ValueError(f"{name} has missing required values")
        if not set(frame["outcome"]).issubset({"yes", "no"}):
            raise ValueError(f"{name} has invalid outcome labels")

    integrity_checks = {
        **schema_checks,
        "v3_has_1000_rows": len(v3) == 1000,
        "v3_ids_unique": bool(v3["record_id"].is_unique),
        "v3_hash_matches_manifest":
            sha256(V3) == manifest.get("generated_sha256"),
        "reference_hash_matches_manifest":
            sha256(REF) == manifest.get("reference_sha256"),
        "v3_age_within_reference_range": bool(
            v3["age"].between(ref["age"].min(), ref["age"].max()).all()
        ),
        "v3_balance_within_reference_range": bool(
            v3["balance"].between(
                ref["balance"].min(), ref["balance"].max()
            ).all()
        ),
    }

    if not all(integrity_checks.values()):
        integrity_status = "FAIL"
    else:
        integrity_status = "PASS"

    metrics_v2 = utility_metrics(ref, v2)
    metrics_v3 = utility_metrics(ref, v3)
    utility_checks = evaluate_utility_thresholds(metrics_v3)

    utility_status = (
        "MEETS_ILLUSTRATIVE_TARGETS"
        if all(utility_checks.values())
        else "DOES_NOT_MEET_ALL_ILLUSTRATIVE_TARGETS"
    )

    # Utility similarity and hashes never substitute for privacy assurance.
    privacy_assurance = "INCONCLUSIVE_NOT_ESTABLISHED"
    cobol_execution = "NOT_VERIFIED"
    release_status = decide_release(
        integrity_status, privacy_assurance, cobol_execution
    )

    result = {
        "project": "Z-Mirror",
        "report": "Automated Release Gate",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "architecture": platform.machine(),
            "python": platform.python_version(),
        },
        "threshold_policy": {
            "type": "illustrative prototype targets",
            "approved_by_stakeholder": False,
            "privacy_thresholds": False,
            "thresholds": THRESHOLDS,
        },
        "artifacts": {
            "reference_rows": int(len(ref)),
            "v2_rows": int(len(v2)),
            "v3_rows": int(len(v3)),
            "reference_sha256": sha256(REF),
            "v2_sha256": sha256(V2),
            "v3_sha256": sha256(V3),
            "manifest_v3_sha256": manifest.get("generated_sha256"),
        },
        "integrity_checks": integrity_checks,
        "integrity_status": integrity_status,
        "v2_metrics": metrics_v2,
        "v3_metrics": metrics_v3,
        "v3_utility_checks": utility_checks,
        "utility_status": utility_status,
        "privacy_assurance": privacy_assurance,
        "cobol_execution": cobol_execution,
        "release_status": release_status,
        "limitations": [
            "Illustrative utility targets are not formally approved acceptance criteria.",
            "Distribution similarity and file hashes are not privacy guarantees.",
            "No differential privacy guarantee is provided.",
            "COBOL compilation and execution were not verified by this gate.",
            "Passing this gate does not establish production readiness."
        ],
    }

    REPORTS.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS / "release_gate_report_20261018.json"
    md_path = REPORTS / "RELEASE_GATE_REPORT_20261018.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n")

    lines = [
        "# Z-Mirror Automated Release Gate",
        "",
        f"Generated UTC: {result['generated_at_utc']}",
        "",
        f"- Integrity: **{integrity_status}**",
        f"- V3 utility against illustrative targets: **{utility_status}**",
        f"- Privacy assurance: **{result['privacy_assurance']}**",
        f"- COBOL execution: **{result['cobol_execution']}**",
        f"- Overall release: **{release_status}**",
        "",
        "## Integrity checks",
        "",
    ]
    lines.extend(
        f"- {'PASS' if ok else 'FAIL'}: {name}"
        for name, ok in integrity_checks.items()
    )
    lines += [
        "",
        "## V2 versus V3",
        "",
        "| Measure | V2 | V3 |",
        "|---|---:|---:|",
        f"| Age KS distance | {metrics_v2['age_ks']:.4f} | {metrics_v3['age_ks']:.4f} |",
        f"| Balance KS distance | {metrics_v2['balance_ks']:.4f} | {metrics_v3['balance_ks']:.4f} |",
        f"| Balance mean | {metrics_v2['balance_mean_candidate']:.2f} | {metrics_v3['balance_mean_candidate']:.2f} |",
        f"| Balance 95th percentile | {metrics_v2['balance_p95_candidate']:.2f} | {metrics_v3['balance_p95_candidate']:.2f} |",
        f"| Outcome yes-rate gap (pp) | {metrics_v2['outcome_yes_gap_pp']:.4f} | {metrics_v3['outcome_yes_gap_pp']:.4f} |",
        "",
        "## V3 utility target checks",
        "",
    ]
    lines.extend(
        f"- {'PASS' if ok else 'FAIL'}: {name}"
        for name, ok in utility_checks.items()
    )
    lines += [
        "",
        "## Release policy",
        "",
        "The configured numerical targets are illustrative prototype targets, "
        "not formally approved acceptance criteria and not privacy thresholds.",
        "The gate deliberately does not approve release while privacy assurance "
        "and actual COBOL execution remain unverified.",
        "",
        "No anonymity, differential privacy, or production-readiness guarantee is made.",
        "",
    ]
    md_path.write_text("\n".join(lines))

    print("=== AUTOMATED RELEASE GATE ===")
    for name, ok in integrity_checks.items():
        print(f"{'PASS' if ok else 'FAIL'}: {name}")
    print("\nV3 utility checks:")
    for name, ok in utility_checks.items():
        print(f"{'PASS' if ok else 'FAIL'}: {name}")
    print(f"\nIntegrity: {integrity_status}")
    print(f"Utility: {utility_status}")
    print(f"Release: {release_status}")
    print(f"\nMarkdown: {md_path}")
    print(f"JSON:     {json_path}")


if __name__ == "__main__":
    run()
