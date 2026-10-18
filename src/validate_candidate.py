import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "candidate.csv"
OUTPUT = ROOT / "data" / "cobol_input.dat"
REPORT = ROOT / "reports" / "validation_report.txt"
EXPECTED_COLUMNS = ["record_id", "age", "balance", "outcome"]


def _remove_stale_artifact(path: Path) -> None:
    """Remove an artifact from a previous run or raise if it cannot be invalidated."""
    path.unlink(missing_ok=True)


def _write_text_atomically(path: Path, text: str, encoding: str) -> None:
    """Write to a sibling temporary file, then replace the target atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(text, encoding=encoding, newline="")
        temporary.replace(path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _record_error_report(rows_seen: int, message: str) -> int:
    """Invalidate output and publish an error report; return operational-error code 2."""
    try:
        _remove_stale_artifact(OUTPUT)
    except OSError as error:
        print(f"File error while removing stale output: {error}", file=sys.stderr)
    report_lines = [
        "PYTHON VALIDATION: ERROR",
        f"Rows examined: {rows_seen}",
        message,
        "No current-run output is available.",
    ]
    report_text = "\n".join(report_lines) + "\n"
    try:
        _write_text_atomically(REPORT, report_text, encoding="utf-8")
    except OSError as error:
        print(f"File error while writing error report: {error}", file=sys.stderr)
    print(message, file=sys.stderr)
    print(report_text, end="")
    return 2


def validate() -> int:
    errors = []
    accepted = []
    seen_ids = set()
    rows_seen = 0
    schema_ok = False

    # Fail closed: remove previous-run artifacts before starting a new run.
    # If this cannot be done, stop rather than risk stale output being mistaken for current output.
    try:
        _remove_stale_artifact(OUTPUT)
        _remove_stale_artifact(REPORT)
    except OSError as error:
        print(
            f"File error: could not invalidate previous artifacts; do not trust existing output/report: {error}",
            file=sys.stderr,
        )
        return 2

    try:
        with INPUT.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file, strict=True)
            schema_ok = reader.fieldnames == EXPECTED_COLUMNS
            if not schema_ok:
                errors.append("CSV columns do not match the required schema.")

            # Always iterate to count available data rows, even with a bad header.
            for line, row in enumerate(reader, start=2):
                rows_seen += 1
                if not schema_ok:
                    continue

                row_errors = []
                if None in row:
                    row_errors.append("row has extra fields")
                # DictReader uses None for a missing value when a row has too few fields.
                if any(value is None for key, value in row.items() if key is not None):
                    row_errors.append("row has missing fields")

                record_id = (row.get("record_id") or "").strip()
                outcome = (row.get("outcome") or "").strip().lower()

                if not record_id:
                    row_errors.append("record_id is empty")
                elif record_id in seen_ids:
                    row_errors.append("duplicate record_id")
                else:
                    seen_ids.add(record_id)

                try:
                    age = int(row.get("age"))
                    if not 18 <= age <= 100:
                        row_errors.append("age must be between 18 and 100")
                except (ValueError, TypeError):
                    age = None
                    row_errors.append("age must be an integer")

                try:
                    balance = int(row.get("balance"))
                    if not -9999999 <= balance <= 9999999:
                        row_errors.append("balance is outside the supported range")
                except (ValueError, TypeError):
                    balance = None
                    row_errors.append("balance must be an integer")

                if outcome not in {"yes", "no"}:
                    row_errors.append("outcome must be yes or no")

                if row_errors:
                    errors.extend(f"Line {line}: {message}" for message in row_errors)
                else:
                    sign = "+" if balance >= 0 else "-"
                    outcome_code = "Y" if outcome == "yes" else "N"
                    accepted.append(f"{age:03d}{sign}{abs(balance):07d}{outcome_code}")

    except OSError as error:
        return _record_error_report(rows_seen, f"File error: {error}")
    except csv.Error as error:
        return _record_error_report(rows_seen, f"CSV parse error: {error}")

    if rows_seen == 0:
        errors.append("CSV has no data rows.")

    if errors:
        result = [
            "PYTHON VALIDATION: FAIL",
            f"Rows examined: {rows_seen}",
            *errors,
        ]
        exit_code = 1
    else:
        result = [
            "PYTHON VALIDATION: PASS",
            f"Rows examined: {rows_seen}",
            f"Rows accepted: {len(accepted)}",
            f"COBOL input generated: {OUTPUT.relative_to(ROOT)}",
            "Checks: schema, unique IDs, age, balance, outcome, row field count",
            "Privacy risk and statistical utility are NOT evaluated yet.",
        ]
        exit_code = 0

    report_text = "\n".join(result) + "\n"
    try:
        if exit_code == 0:
            _write_text_atomically(OUTPUT, "\n".join(accepted) + "\n", encoding="ascii")
        _write_text_atomically(REPORT, report_text, encoding="utf-8")
    except OSError as error:
        # Never leave a newly generated output behind if its matching report failed.
        try:
            _remove_stale_artifact(OUTPUT)
        except OSError as cleanup_error:
            print(f"File error while cleaning output: {cleanup_error}", file=sys.stderr)
        return _record_error_report(rows_seen, f"File error while writing artifacts: {error}")

    print(report_text, end="")
    return exit_code


if __name__ == "__main__":
    sys.exit(validate())
