#!/usr/bin/env python3
import csv
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evaluate_utility import read_rows, evaluate, ks_statistic

HEADER = ["record_id", "age", "balance", "outcome"]
def write_csv(path, rows, header=HEADER):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)

class UtilityTests(unittest.TestCase):
    def test_identical_numeric_sets_ks_zero(self): self.assertEqual(ks_statistic([1,2,3], [1,2,3]), 0.0)
    def test_disjoint_sets_ks_one(self): self.assertEqual(ks_statistic([1,2,3], [10,11,12]), 1.0)
    def test_reads_valid_csv(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"a.csv"; write_csv(p, [["A",35,100,"yes"],["B",40,-5,"no"]])
            self.assertEqual(len(read_rows(p)), 2)
    def test_rejects_extra_fields(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv"; p.write_text("record_id,age,balance,outcome\nA,35,100,yes,EXTRA\n")
            with self.assertRaises(ValueError): read_rows(p)
    def test_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv"; write_csv(p, [["A",35,100,"yes"],["A",40,-5,"no"]])
            with self.assertRaises(ValueError): read_rows(p)
    def test_rejects_unknown_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.csv"; write_csv(p, [["A",35,100,"maybe"]])
            with self.assertRaises(ValueError): read_rows(p)
    def test_report_is_measurement_only(self):
        ref=[{"record_id":"R1","age":35,"balance":100,"outcome":"yes"},{"record_id":"R2","age":40,"balance":-5,"outcome":"no"}]
        can=[{"record_id":"C1","age":35,"balance":100,"outcome":"yes"},{"record_id":"C2","age":42,"balance":10,"outcome":"no"}]
        report=evaluate(ref,can)
        self.assertEqual(report["status"], "MEASUREMENT_ONLY_THRESHOLDS_NOT_CONFIGURED")
        self.assertIn("reference_overlap_diagnostic", report)
        self.assertIn("NOT a privacy-risk score", report["reference_overlap_diagnostic"]["interpretation"])

if __name__ == "__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(UtilityTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"Summary: {result.testsRun-len(result.failures)-len(result.errors)}/{result.testsRun} passed")
    raise SystemExit(0 if result.wasSuccessful() else 1)
