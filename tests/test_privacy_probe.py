import csv, json, os, sys, tempfile, unittest
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import privacy_probe as pp

FAST = dict(baseline_draws=120, nn_baseline_draws=2)

def stand_in_rows(n, seed):
    """SYNTHETIC stand-in with a bank-like shape. Not Z-Mirror data."""
    r = np.random.default_rng(seed)
    age = np.clip(r.normal(41, 10, n).round(), 18, 95).astype(int)
    bal = (np.sign(r.normal(0.6, 1, n)) * np.expm1(np.abs(r.normal(6.2, 1.6, n)))).round().astype(int)
    out = np.where(r.random(n) < 0.117, "yes", "no")
    return [dict(record_id=i + 1, age=int(a), balance=int(b), outcome=o) for i, (a, b, o) in enumerate(zip(age, bal, out))]

def write(path, rows, fields=("record_id", "age", "balance", "outcome")):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fields), extrasaction="ignore"); w.writeheader(); w.writerows(rows)

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.d = self.tmp.name
        self.ref_rows = stand_in_rows(6000, 1)
        self.ref = os.path.join(self.d, "ref.csv"); write(self.ref, self.ref_rows)
    def tearDown(self): self.tmp.cleanup()
    def cand(self, rows, name="cand.csv", **kw):
        p = os.path.join(self.d, name); write(p, rows, **kw); return p

class TestChecks(Base):
    def test_planted_exact_copies_fail(self):
        c = self.cand(self.ref_rows[:300])
        res = pp.run(self.ref, c, **FAST)
        self.assertEqual(res["checks"]["exact_overlap"]["status"], "FAIL")
        self.assertEqual(res["overall"]["exit_code"], 1)

    def test_independent_draw_is_close_to_baseline(self):
        c = self.cand(stand_in_rows(300, 99))
        res = pp.run(self.ref, c, **FAST)["checks"]["exact_overlap"]
        self.assertLess(abs(res["candidate_rate"] - res["baseline_mean"]), 0.12)

    def test_nn_planted_copies_fail(self):
        r = np.random.default_rng(5)
        n = 3000
        ref = (r.integers(18, 91, n), r.integers(-3000, 90000, n), np.where(r.random(n) < .12, "yes", "no"))
        cand = tuple(a[:200].copy() for a in ref)
        res = pp.nn_check(ref, cand, dict(pp.DEFAULTS, **FAST), np.random.default_rng(1))
        self.assertEqual(res["status"], "FAIL")
        self.assertGreater(res["candidate_share_below_q05"], 0.9)

    def test_nn_degenerate_baseline_is_inconclusive_not_pass(self):
        r = np.random.default_rng(5)
        a = r.integers(18, 40, 1000); b = r.integers(0, 50, 1000); o = np.where(r.random(1000) < .1, "yes", "no")
        ref = tuple(np.concatenate([x, x]) for x in (a, b, o))     # every record has an exact twin
        cand = tuple(x[:100].copy() for x in (a, b, o))
        res = pp.nn_check(ref, cand, dict(pp.DEFAULTS, **FAST), np.random.default_rng(1))
        self.assertEqual(res["status"], "INCONCLUSIVE")

class TestFailClosed(Base):
    def assertAllInconclusive(self, res):
        self.assertEqual({c["status"] for c in res["checks"].values()}, {"INCONCLUSIVE"})
        self.assertEqual(res["overall"]["exit_code"], 2)
        self.assertEqual(res["overall"]["privacy_assurance"], "NOT ESTABLISHED")

    def test_missing_column(self):
        self.assertAllInconclusive(pp.run(self.ref, self.cand(self.ref_rows[:50], fields=("record_id", "age", "outcome")), **FAST))
    def test_non_integer_age(self):
        rows = [dict(r) for r in self.ref_rows[:50]]; rows[7]["age"] = "forty"
        self.assertAllInconclusive(pp.run(self.ref, self.cand(rows), **FAST))
    def test_empty_outcome(self):
        rows = [dict(r) for r in self.ref_rows[:50]]; rows[3]["outcome"] = ""
        self.assertAllInconclusive(pp.run(self.ref, self.cand(rows), **FAST))
    def test_empty_candidate(self):
        self.assertAllInconclusive(pp.run(self.ref, self.cand([]), **FAST))
    def test_missing_file(self):
        self.assertAllInconclusive(pp.run(self.ref, os.path.join(self.d, "nope.csv"), **FAST))
    def test_candidate_too_large_for_baseline(self):
        self.assertAllInconclusive(pp.run(self.ref, self.cand(stand_in_rows(4000, 3)), **FAST))

class TestPolicy(unittest.TestCase):
    def test_boundary_is_inclusive_and_just_over_fails(self):
        self.assertEqual(pp.decide(0.10, 0.10), "PASS")
        self.assertEqual(pp.decide(0.1000001, 0.10), "FAIL")
    def test_fail_outranks_inconclusive(self):
        res = pp._finish({"checks": {"a": {"status": "FAIL"}, "b": {"status": "INCONCLUSIVE"}}})
        self.assertEqual(res["overall"]["exit_code"], 1)
    def test_no_checks_is_not_success(self):
        self.assertEqual(pp._finish({"checks": {}})["overall"]["exit_code"], 2)
    def test_all_pass_still_does_not_establish_privacy(self):
        res = pp._finish({"checks": {"a": {"status": "PASS"}}})
        self.assertEqual(res["overall"]["exit_code"], 0)
        self.assertEqual(res["overall"]["privacy_assurance"], "NOT ESTABLISHED")

class TestReproducibility(Base):
    def test_same_seed_same_report_and_hash_tracks_content(self):
        c = self.cand(stand_in_rows(300, 99))
        a = json.dumps(pp.run(self.ref, c, **FAST), sort_keys=True)
        b = json.dumps(pp.run(self.ref, c, **FAST), sort_keys=True)
        self.assertEqual(a, b)
        before = json.loads(a)["inputs"]["candidate_sha256"]
        with open(c, "ab") as f: f.write(b" ")           # tamper with one byte
        self.assertNotEqual(before, pp.run(self.ref, c, **FAST)["inputs"]["candidate_sha256"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
