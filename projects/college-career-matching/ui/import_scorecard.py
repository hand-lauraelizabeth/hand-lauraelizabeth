"""Convert reviewed College Scorecard CSV rows into matcher records.

Usage:
 python import_scorecard.py institutions.csv reviewed-metadata.json output.json

reviewed-metadata.json:
 {
   "release_year": 2025,
   "source_url": "https://...official-release.csv",
   "institutions": {
     "123456": {
       "setting": "Urban", "housing": true, "aid": [],
       "population": "PUB",
       "access": null,
       "careers": {"data": null, "education": null, "health": null, "business": null}
     }
   }
 }

Only explicitly reviewed UNITIDs are exported. Metadata must be independently
verified; this script cannot establish that its assertions are true.
"""
import csv
import json
import math
import sys
from pathlib import Path

from importlib.util import module_from_spec, spec_from_file_location

spec = spec_from_file_location("matcher_validator", Path(__file__).with_name("validate-public-data.py"))
validator = module_from_spec(spec)
spec.loader.exec_module(validator)

BANDS = ("0_30k", "30_48k", "48_75k", "75_110k", "110k_plus")
POPULATIONS = {"PUB", "PRIV", "PROG", "OTHER"}
SUPPRESSED = {"", "NULL", "NA", "N/A", "PS", "PRIVACY SUPPRESSED", "-1", "-2"}


def parse_price(value):
    if value is None or value.strip().upper() in SUPPRESSED:
        return None
    try:
        number = float(value.replace(",", ""))
    except ValueError as exc:
        raise ValueError(f"Unexpected net-price value {value!r}") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Invalid net-price value {value!r}")
    return int(number) if number.is_integer() else number


def convert(csv_path, metadata):
    if not isinstance(metadata, dict) or type(metadata.get("release_year")) is not int:
        raise ValueError("Metadata must specify integer release_year")
    if not isinstance(metadata.get("source_url"), str) or not metadata["source_url"].startswith("https://"):
        raise ValueError("Metadata must specify official HTTPS source_url")
    reviewed = metadata.get("institutions")
    if not isinstance(reviewed, dict) or not reviewed:
        raise ValueError("Metadata must list explicitly reviewed UNITIDs")
    records = []
    seen = set()
    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            unitid = (row.get("UNITID") or "").strip()
            if unitid not in reviewed:
                continue
            if unitid in seen:
                raise ValueError(f"Duplicate UNITID in source: {unitid}")
            seen.add(unitid)
            info = reviewed[unitid]
            if not isinstance(info, dict):
                raise ValueError(f"Metadata for {unitid} must be an object")
            population = info.get("population")
            if population not in POPULATIONS:
                raise ValueError(f"Reviewed population required for {unitid}")
            cost = {}
            for i, band in enumerate(BANDS, 1):
                field = f"NPT4{i}_{population}"
                if field not in row:
                    raise ValueError(f"Missing source column {field} for {unitid}")
                cost[band] = parse_price(row[field])
            record = {
                "name": (row.get("INSTNM") or "").strip(),
                "setting": info.get("setting"),
                "housing": info.get("housing"),
                "access": info.get("access"),
                "cost": cost,
                "careers": info.get("careers"),
                "aid": info.get("aid"),
                "source": f"College Scorecard {metadata['source_url']} · UNITID {unitid} · population {population}",
                "reference_year": metadata["release_year"],
            }
            records.append(record)
    missing = set(reviewed) - seen
    if missing:
        raise ValueError(f"Reviewed UNITIDs absent from CSV: {sorted(missing)}")
    payload = {"schema_version": 1, "records": records}
    errors = validator.validate(payload)
    if errors:
        raise ValueError("Validation failed:\n" + "\n".join(errors))
    return payload


def main():
    if len(sys.argv) != 4:
        sys.exit("Usage: python import_scorecard.py institutions.csv reviewed-metadata.json output.json")
    try:
        metadata = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        payload = convert(sys.argv[1], metadata)
        Path(sys.argv[3]).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError) as exc:
        sys.exit(str(exc))
    print(f"Prepared {len(payload['records'])} structurally valid records; independent source review required.")


if __name__ == "__main__":
    main()
