"""Read-only preflight for a College Scorecard institution-level CSV.

Usage: python preflight_scorecard.py path/to/institution.csv|.zip PUB
No network calls, no output bundle, no institutional records published.
"""
import csv
import sys
import zipfile
from pathlib import Path

POPULATIONS = {"PUB", "PRIV", "PROG", "OTHER"}
CORE = {"UNITID", "INSTNM", "CONTROL"}


def inspect(csv_path, population):
    if population not in POPULATIONS:
        raise ValueError("population must be PUB, PRIV, PROG, or OTHER")
    csv_path = Path(csv_path)
    if csv_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(csv_path) as archive:
            candidates = [entry for entry in archive.infolist() if not entry.is_dir() and entry.filename.lower().endswith(".csv")]
            if len(candidates) != 1:
                raise ValueError(f"ZIP must contain exactly one CSV; found {len(candidates)}")
            with archive.open(candidates[0]) as raw:
                import io
                headers = next(csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")), [])
    else:
        with open(csv_path, newline="", encoding="utf-8-sig") as handle:
            headers = next(csv.reader(handle), [])
    if not headers:
        raise ValueError("CSV is empty or missing a header")
    if len(headers) != len(set(headers)) or any(not h.strip() for h in headers):
        raise ValueError("CSV contains duplicate or blank headers")
    expected = CORE | {f"NPT4{i}_{population}" for i in range(1, 6)}
    missing = sorted(expected - set(headers))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    return {"population": population, "required_columns": len(expected),
            "total_columns": len(headers), "header_check": "PASS"}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python preflight_scorecard.py institution.csv|.zip PUB|PRIV|PROG|OTHER")
    try:
        result = inspect(Path(sys.argv[1]), sys.argv[2])
    except (OSError, ValueError) as exc:
        sys.exit(str(exc))
    print(f"PASS: {result['population']} header check; {result['required_columns']} required columns present among {result['total_columns']} total. Data provenance and metric year still require independent verification.")
