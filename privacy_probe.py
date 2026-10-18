#!/usr/bin/env python3
"""Z-Mirror empirical privacy probe (exploratory).

Compares a candidate CSV with a reference CSV on the fields age, balance and
outcome, and asks one narrow question: does the candidate match real records
more often than a *fresh real sample of the same size* would match the rest of
the reference by coincidence?

What it is:   a baseline-aware exact-overlap / singling-out / nearest-neighbour
              probe, with fail-closed statuses.
What it isn't: a privacy guarantee, differential privacy, or evidence about a
              confidential database. The reference here is a public dataset and
              the modelled schema has only three fields.

Statuses per check: PASS (ran, criterion met), FAIL (ran, criterion missed),
INCONCLUSIVE (could not be established), NOT RUN.  The overall privacy
assurance is always reported as NOT ESTABLISHED.

Depends on numpy only. Exit codes: 0 all checks PASS, 1 any FAIL, 2 any
INCONCLUSIVE or invalid input (fail closed).
"""
import argparse
import csv
import hashlib
import json
import sys

import numpy as np

VERSION = "0.1.0"
REQUIRED = ("age", "balance", "outcome")

# Exploratory criteria. Set BEFORE looking at results; not stakeholder-approved.
DEFAULTS = {
    "seed": 42,
    "baseline_draws": 500,
    "nn_baseline_draws": 3,
    "overlap_quantile": 0.95,   # candidate rate must not exceed this quantile of the baseline draws
    "singling_quantile": 0.95,
    "nn_max_share_below_q05": 0.10,
}


class InputError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_table(path, label):
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except OSError as e:
        raise InputError("%s: cannot read file (%s)" % (label, e))
    if not rows:
        raise InputError("%s: no data rows" % label)
    missing = [c for c in REQUIRED if c not in rows[0]]
    if missing:
        raise InputError("%s: missing column(s) %s" % (label, ", ".join(missing)))
    age, bal, out = [], [], []
    for n, r in enumerate(rows, start=2):
        try:
            a = int(str(r["age"]).strip())
            b = int(str(r["balance"]).strip())
        except (ValueError, TypeError):
            raise InputError("%s: line %d has a non-integer age or balance" % (label, n))
        o = (r["outcome"] or "").strip()
        if o == "":
            raise InputError("%s: line %d has an empty outcome" % (label, n))
        age.append(a); bal.append(b); out.append(o)
    return np.array(age), np.array(bal), np.array(out)


def encode_tuples(ref, cand):
    """Map (age, balance, outcome) tuples of both tables to shared integer ids."""
    labels = sorted(set(ref[2].tolist()) | set(cand[2].tolist()))
    lab = {l: i for i, l in enumerate(labels)}
    def stack(t):
        return np.stack([t[0], t[1], np.array([lab[x] for x in t[2]])], axis=1)
    both = np.concatenate([stack(ref), stack(cand)], axis=0)
    _, inv = np.unique(both, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    return inv[: len(ref[0])], inv[len(ref[0]):], labels


def decide(value, limit):
    """PASS when value <= limit (boundary inclusive); FAIL otherwise."""
    return "PASS" if value <= limit else "FAIL"


def overlap_checks(ref_ids, cand_ids, cfg, rng):
    n_ref, n = len(ref_ids), len(cand_ids)
    k = int(max(ref_ids.max(), cand_ids.max())) + 1
    cnt = np.bincount(ref_ids, minlength=k)
    cand_overlap = float(np.mean(cnt[cand_ids] >= 1))
    cand_single = float(np.mean(cnt[cand_ids] == 1))
    ov, sg = [], []
    for _ in range(cfg["baseline_draws"]):
        idx = rng.choice(n_ref, size=n, replace=False)
        rem = cnt - np.bincount(ref_ids[idx], minlength=k)
        r = rem[ref_ids[idx]]
        ov.append(np.mean(r >= 1)); sg.append(np.mean(r == 1))
    ov, sg = np.array(ov), np.array(sg)
    o_lim = float(np.quantile(ov, cfg["overlap_quantile"]))
    s_lim = float(np.quantile(sg, cfg["singling_quantile"]))
    return {
        "exact_overlap": {
            "status": decide(cand_overlap, o_lim),
            "candidate_rate": cand_overlap,
            "baseline_mean": float(ov.mean()),
            "baseline_limit": o_lim,
            "rule": "candidate rate <= baseline %.2f quantile" % cfg["overlap_quantile"],
        },
        "unique_record_match": {
            "status": decide(cand_single, s_lim),
            "candidate_rate": cand_single,
            "baseline_mean": float(sg.mean()),
            "baseline_limit": s_lim,
            "rule": "share of candidate rows matching exactly one reference record <= baseline %.2f quantile" % cfg["singling_quantile"],
        },
    }


def _feat(age, bal, out_ids, sd_a, sd_b):
    tb = np.sign(bal) * np.log1p(np.abs(bal))
    return np.stack([age / sd_a, tb / sd_b, out_ids.astype(float)], axis=1)


def _nn(q, base, chunk=250):
    d = np.empty(len(q))
    for i in range(0, len(q), chunk):
        a = q[i:i + chunk]
        dd = (a[:, None, :2] - base[None, :, :2]) ** 2
        s = dd.sum(axis=2) + (a[:, None, 2] != base[None, :, 2])
        d[i:i + chunk] = np.sqrt(s.min(axis=1))
    return d


def nn_check(ref, cand, cfg, rng):
    labels = sorted(set(ref[2].tolist()) | set(cand[2].tolist()))
    lab = {l: i for i, l in enumerate(labels)}
    r_out = np.array([lab[x] for x in ref[2]]); c_out = np.array([lab[x] for x in cand[2]])
    tb = np.sign(ref[1]) * np.log1p(np.abs(ref[1]))
    sd_a, sd_b = float(ref[0].std()) or 1.0, float(tb.std()) or 1.0
    R = _feat(ref[0], ref[1], r_out, sd_a, sd_b)
    C = _feat(cand[0], cand[1], c_out, sd_a, sd_b)
    d_c = _nn(C, R)
    d_b = []
    for _ in range(cfg["nn_baseline_draws"]):
        idx = rng.choice(len(R), size=len(C), replace=False)
        mask = np.ones(len(R), bool); mask[idx] = False
        d_b.append(_nn(R[idx], R[mask]))
    d_b = np.concatenate(d_b)
    q05 = float(np.quantile(d_b, 0.05))
    out = {"candidate_median": float(np.median(d_c)), "baseline_median": float(np.median(d_b)),
           "baseline_q05": q05, "rule": "share of candidates strictly closer than baseline 5th percentile <= %.2f" % cfg["nn_max_share_below_q05"]}
    if q05 <= 0.0:
        out.update(status="INCONCLUSIVE",
                   reason="baseline 5th percentile distance is 0 (many real records have exact twins in this coarse 3-field schema); the share test is degenerate here. Use the exact-overlap checks.")
        return out
    share = float(np.mean(d_c < q05))
    out.update(status=decide(share, cfg["nn_max_share_below_q05"]), candidate_share_below_q05=share)
    return out


def run(reference, candidate, **over):
    cfg = dict(DEFAULTS); cfg.update(over)
    result = {
        "tool": "zmirror_privacy_probe", "version": VERSION, "config": cfg,
        "threshold_status": "exploratory targets, fixed before the run; not stakeholder-approved; not privacy thresholds",
        "inputs": {}, "checks": {}, "overall": {}, "limitations": [
            "Public reference data; says nothing about protecting a confidential database.",
            "Only three fields are compared; absence of a match here is not anonymity.",
            "Heuristic probe, not differential privacy and not a formal guarantee.",
            "The generator's training data is the whole reference, so the baseline is a coincidence baseline, not a true holdout."],
    }
    try:
        for key, path, label in (("reference_sha256", reference, "reference"), ("candidate_sha256", candidate, "candidate")):
            try:
                result["inputs"][key] = sha256_file(path)
            except OSError as e:
                raise InputError("%s: cannot read file (%s)" % (label, e))
        ref = load_table(reference, "reference"); cand = load_table(candidate, "candidate")
        if len(cand[0]) > len(ref[0]) // 2:
            raise InputError("candidate has more than half as many rows as the reference; baseline sampling is not meaningful")
    except InputError as e:
        for name in ("exact_overlap", "unique_record_match", "nearest_neighbour"):
            result["checks"][name] = {"status": "INCONCLUSIVE", "reason": str(e)}
        return _finish(result)
    rng = np.random.default_rng(cfg["seed"])
    ref_ids, cand_ids, _ = encode_tuples(ref, cand)
    result["inputs"].update(reference_rows=len(ref[0]), candidate_rows=len(cand[0]))
    result["checks"].update(overlap_checks(ref_ids, cand_ids, cfg, rng))
    result["checks"]["nearest_neighbour"] = nn_check(ref, cand, cfg, rng)
    return _finish(result)


def _finish(result):
    st = [c["status"] for c in result["checks"].values()]
    # FAIL outranks INCONCLUSIVE: a demonstrated miss already blocks release.
    code = 1 if "FAIL" in st else (2 if "INCONCLUSIVE" in st or not st else 0)
    result["overall"] = {
        "checks_pass": st.count("PASS"), "checks_fail": st.count("FAIL"), "checks_inconclusive": st.count("INCONCLUSIVE"),
        "privacy_assurance": "NOT ESTABLISHED",
        "statement": "These checks measure selected empirical properties of one run. They do not establish privacy.",
        "exit_code": code,
    }
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--reference", required=True); ap.add_argument("--candidate", required=True)
    ap.add_argument("--output", help="write JSON report here")
    ap.add_argument("--seed", type=int, default=DEFAULTS["seed"])
    a = ap.parse_args(argv)
    res = run(a.reference, a.candidate, seed=a.seed)
    text = json.dumps(res, indent=2, sort_keys=True)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)
    return res["overall"]["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
