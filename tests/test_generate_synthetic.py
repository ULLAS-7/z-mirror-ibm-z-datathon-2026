#!/usr/bin/env python3
"""Standard-library regression tests for the Z-Mirror demo generator."""
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "src" / "generate_synthetic.py"
EXPECTED_COLUMNS = ["record_id", "age", "balance", "outcome"]


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = self.root / "generated.csv"

    def execute(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            cwd=self.root, capture_output=True, text=True, check=False,
        )

    def test_schema_and_row_count(self):
        result = self.execute("--rows", 25, "--seed", 7, "--output", self.out)
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.out.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, EXPECTED_COLUMNS)
            rows = list(reader)
        self.assertEqual(len(rows), 25)

    def test_reproducible_same_seed(self):
        one, two = self.root / "one.csv", self.root / "two.csv"
        self.assertEqual(self.execute("--rows", 40, "--seed", 123, "--output", one).returncode, 0)
        self.assertEqual(self.execute("--rows", 40, "--seed", 123, "--output", two).returncode, 0)
        self.assertEqual(one.read_bytes(), two.read_bytes())

    def test_different_seed_changes_content(self):
        one, two = self.root / "one.csv", self.root / "two.csv"
        self.assertEqual(self.execute("--rows", 40, "--seed", 123, "--output", one).returncode, 0)
        self.assertEqual(self.execute("--rows", 40, "--seed", 124, "--output", two).returncode, 0)
        self.assertNotEqual(one.read_bytes(), two.read_bytes())

    def test_unique_ids_and_valid_ranges(self):
        result = self.execute("--rows", 500, "--seed", 42, "--output", self.out)
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.out.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        ids = [row["record_id"] for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        for row in rows:
            self.assertTrue(18 <= int(row["age"]) <= 100)
            self.assertTrue(-9_999_999 <= int(row["balance"]) <= 9_999_999)
            self.assertIn(row["outcome"], {"yes", "no"})

    def test_manifest_schema_seed_and_hash(self):
        result = self.execute("--rows", 9, "--seed", 77, "--output", self.out)
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest_path = Path(str(self.out) + ".manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["rows"], 9)
        self.assertEqual(manifest["seed"], 77)
        self.assertEqual(manifest["schema"], EXPECTED_COLUMNS)
        self.assertEqual(manifest["sha256"], hashlib.sha256(self.out.read_bytes()).hexdigest())
        self.assertIn("not automatically anonymous", " ".join(manifest["limitations"]))

    def test_refuses_to_overwrite_without_force(self):
        self.assertEqual(self.execute("--rows", 3, "--output", self.out).returncode, 0)
        before = self.out.read_bytes()
        result = self.execute("--rows", 4, "--output", self.out)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.out.read_bytes(), before)

    def test_force_overwrites_deliberately(self):
        self.assertEqual(self.execute("--rows", 3, "--output", self.out).returncode, 0)
        result = self.execute("--rows", 4, "--output", self.out, "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.out.open(newline="", encoding="utf-8") as f:
            self.assertEqual(len(list(csv.DictReader(f))), 4)

    def test_rejects_zero_or_negative_rows(self):
        for count in (0, -1):
            result = self.execute("--rows", count, "--output", self.root / f"bad{count}.csv")
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GeneratorTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"Summary: {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun} passed")
    raise SystemExit(0 if result.wasSuccessful() else 1)
