import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src" / "validate_candidate.py"
CASES = [
    dict(name="baseline_valid", csv="record_id,age,balance,outcome\nSYN001,35,1200,yes\nSYN002,48,-250,no\n", code=0, want=["Rows examined: 2", "Rows accepted: 2"], output=["035+0001200Y", "048-0000250N"]),
    dict(name="wrong_header_counts_rows", csv="record_id,age,balance,wrong_column\nSYN001,35,1200,yes\n", code=1, want=["Rows examined: 1", "CSV columns do not match the required schema."], not_want=["CSV has no data rows."]),
    dict(name="extra_value_rejected", csv="record_id,age,balance,outcome\nSYN001,35,1200,yes,UNEXPECTED\n", code=1, want=["row has extra fields"]),
    dict(name="missing_value_rejected", csv="record_id,age,balance,outcome\nSYN001,35,,yes\n", code=1, want=["balance must be an integer"]),
    dict(name="empty_id_rejected", csv="record_id,age,balance,outcome\n,35,1200,yes\n", code=1, want=["record_id is empty"]),
    dict(name="duplicate_id_rejected", csv="record_id,age,balance,outcome\nSYN001,35,1200,yes\nSYN001,40,100,no\n", code=1, want=["duplicate record_id"]),
    dict(name="age_too_low", csv="record_id,age,balance,outcome\nSYN001,17,1200,yes\n", code=1, want=["age must be between 18 and 100"]),
    dict(name="age_too_high", csv="record_id,age,balance,outcome\nSYN001,101,1200,yes\n", code=1, want=["age must be between 18 and 100"]),
    dict(name="age_not_integer", csv="record_id,age,balance,outcome\nSYN001,adult,1200,yes\n", code=1, want=["age must be an integer"]),
    dict(name="balance_too_high", csv="record_id,age,balance,outcome\nSYN001,35,10000000,yes\n", code=1, want=["balance is outside the supported range"]),
    dict(name="balance_too_low", csv="record_id,age,balance,outcome\nSYN001,35,-10000000,no\n", code=1, want=["balance is outside the supported range"]),
    dict(name="invalid_outcome", csv="record_id,age,balance,outcome\nSYN001,35,1200,maybe\n", code=1, want=["outcome must be yes or no"]),
    dict(name="negative_balance_encoded", csv="record_id,age,balance,outcome\nSYN001,35,-250,no\n", code=0, want=["Rows accepted: 1"], output=["035-0000250N"]),
    dict(name="balance_boundaries", csv="record_id,age,balance,outcome\nSYN001,35,-9999999,no\nSYN002,36,9999999,yes\n", code=0, want=["Rows accepted: 2"], output=["035-9999999N", "036+9999999Y"]),
    dict(name="empty_csv", csv="", code=1, want=["CSV columns do not match the required schema.", "CSV has no data rows."]),
    dict(name="header_only_csv", csv="record_id,age,balance,outcome\n", code=1, want=["Rows examined: 0", "CSV has no data rows."]),
    dict(name="malformed_csv_has_error_report", csv='record_id,age,balance,outcome\n"SYN001,35,1200,yes\n', code=2, want=["CSV parse error:"], report_want=["PYTHON VALIDATION: ERROR", "CSV parse error:"], report_not_want=["PYTHON VALIDATION: PASS"]),
]

failures = 0
for case in CASES:
    with tempfile.TemporaryDirectory(prefix="zmirror-validator-v2-") as temp:
        root = Path(temp) / "project"
        (root / "src").mkdir(parents=True)
        (root / "data").mkdir()
        (root / "reports").mkdir()
        shutil.copy2(SOURCE, root / "src" / "validate_candidate.py")
        (root / "data" / "candidate.csv").write_text(case["csv"], encoding="utf-8")
        result = subprocess.run([sys.executable, str(root / "src" / "validate_candidate.py")], cwd=root, capture_output=True, text=True)
        combined = result.stdout + result.stderr
        out_path = root / "data" / "cobol_input.dat"
        report_path = root / "reports" / "validation_report.txt"
        report = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
        ok = result.returncode == case["code"]
        for fragment in case.get("want", []):
            ok = ok and fragment in combined
        for fragment in case.get("not_want", []):
            ok = ok and fragment not in combined
        for fragment in case.get("report_want", []):
            ok = ok and fragment in report
        for fragment in case.get("report_not_want", []):
            ok = ok and fragment not in report
        actual_lines = out_path.read_text(encoding="ascii").splitlines() if out_path.exists() else []
        for expected_line in case.get("output", []):
            ok = ok and expected_line in actual_lines
        if case.get("output") and case["code"] == 0:
            ok = ok and all(len(line) == 12 for line in actual_lines)
        if case["code"] != 0:
            ok = ok and not out_path.exists()
        print(f"{'PASS' if ok else 'FAIL'} {case['name']}: exit={result.returncode}")
        if not ok:
            failures += 1
            print("  expected exit:", case["code"])
            print("  stdout:", result.stdout)
            print("  stderr:", result.stderr)
            print("  report:", report)
            print("  output records:", actual_lines)

# Additional stale-artifact regression: valid run, then malformed run in same project.
with tempfile.TemporaryDirectory(prefix="zmirror-validator-stale-") as temp:
    root = Path(temp) / "project"
    (root / "src").mkdir(parents=True)
    (root / "data").mkdir()
    (root / "reports").mkdir()
    shutil.copy2(SOURCE, root / "src" / "validate_candidate.py")
    input_path = root / "data" / "candidate.csv"
    output_path = root / "data" / "cobol_input.dat"
    report_path = root / "reports" / "validation_report.txt"
    input_path.write_text("record_id,age,balance,outcome\nSYN001,35,1200,yes\n", encoding="utf-8")
    first = subprocess.run([sys.executable, str(root / "src" / "validate_candidate.py")], cwd=root, capture_output=True, text=True)
    first_ok = first.returncode == 0 and output_path.exists() and "PYTHON VALIDATION: PASS" in report_path.read_text(encoding="utf-8")
    input_path.write_text('record_id,age,balance,outcome\n"SYN001,35,1200,yes\n', encoding="utf-8")
    second = subprocess.run([sys.executable, str(root / "src" / "validate_candidate.py")], cwd=root, capture_output=True, text=True)
    report = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    ok = first_ok and second.returncode == 2 and not output_path.exists() and "PYTHON VALIDATION: ERROR" in report and "CSV parse error:" in report and "PYTHON VALIDATION: PASS" not in report
    print(f"{'PASS' if ok else 'FAIL'} stale_artifacts_cleared_after_malformed_csv: exit={second.returncode}")
    if not ok:
        failures += 1
        print("  first return code:", first.returncode)
        print("  second return code:", second.returncode)
        print("  second stderr:", second.stderr)
        print("  report:", report)
        print("  output exists:", output_path.exists())

TOTAL = len(CASES) + 1
print(f"Extended summary: {TOTAL - failures}/{TOTAL} passed")
sys.exit(1 if failures else 0)
