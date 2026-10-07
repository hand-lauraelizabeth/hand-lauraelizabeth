"""Produce a private, deterministic review queue from official institution CSV/ZIP.

Usage: python build_scorecard_review_queue.py SOURCE.csv-or-zip OUTPUT.csv [LIMIT]
No institutional records are committed or published by this utility.
"""
import csv
import io
import sys
import zipfile
from contextlib import contextmanager
from pathlib import Path

FIELDS = ("UNITID", "INSTNM", "CONTROL", "CITY", "STABBR", "LOCALE", "NPT41_PUB", "NPT41_PRIV")
OUTPUT = ("UNITID", "INSTNM", "CONTROL", "CITY", "STABBR", "LOCALE", "housing_source_review", "net_price_population", "net_price_sample", "setting_review", "housing_review", "access_review", "aid_review", "cohort_year_review", "publication_status")


@contextmanager
def source_csv(path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            entries = [x for x in archive.infolist() if not x.is_dir() and x.filename.lower().endswith(".csv") and not x.filename.startswith("__MACOSX/") and not Path(x.filename).name.startswith("._")]
            if len(entries) != 1:
                raise ValueError("Expected exactly one dataset CSV in archive")
            with archive.open(entries[0]) as raw:
                with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as handle:
                    yield handle
    else:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            yield handle


def build(source, destination, limit=100):
    if not 1 <= limit <= 10000:
        raise ValueError("LIMIT must be 1–10000")
    with source_csv(source) as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or not {"UNITID", "INSTNM", "CONTROL"}.issubset(headers):
            raise ValueError("Invalid institution CSV headers")
        rows = []
        for row in reader:
            if None in row:
                raise ValueError("Malformed CSV row")
            unitid = (row.get("UNITID") or "").strip()
            if len(unitid) != 6 or not unitid.isascii() or not unitid.isdecimal():
                continue
            control = (row.get("CONTROL") or "").strip()
            if control not in {"1", "2", "3"}:
                continue
            population = "PUB" if control == "1" else "PRIV"
            sample = (row.get("NPT41_" + population) or "").strip()
            rows.append({
                "UNITID": unitid, "INSTNM": (row.get("INSTNM") or "").strip(),
                "CONTROL": control, "CITY": (row.get("CITY") or "").strip(),
                "STABBR": (row.get("STABBR") or "").strip(),
                "LOCALE": (row.get("LOCALE") or "").strip(),
                "housing_source_review": "separate institutional/IPEDS source required",
                "net_price_population": population,
                "net_price_sample": sample,
                "setting_review": "pending", "housing_review": "pending",
                "access_review": "pending", "aid_review": "pending",
                "cohort_year_review": "pending", "publication_status": "DO_NOT_PUBLISH",
            })
    rows.sort(key=lambda r: (r["STABBR"] != "NY", r["STABBR"], r["INSTNM"].casefold(), r["UNITID"]))
    with open(destination, "w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=OUTPUT)
        writer.writeheader()
        writer.writerows(rows[:limit])
    return min(len(rows), limit)


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit("Usage: python build_scorecard_review_queue.py SOURCE.csv-or-zip OUTPUT.csv [LIMIT]")
    try:
        count = build(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) == 4 else 100)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        sys.exit(str(error))
    print(f"Prepared {count} private review rows; NOT publishable")
