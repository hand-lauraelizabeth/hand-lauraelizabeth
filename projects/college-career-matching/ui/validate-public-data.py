"""Validate a reviewed public-data.json bundle before deployment.

Usage: python validate-public-data.py public-data.json
No third-party dependencies. Exit code 1 means the bundle is not publishable.
"""
import json
import math
import sys
from pathlib import Path

BANDS = ("low", "mid", "high")
CAREERS = ("data", "education", "health", "business")
SETTINGS = {"Urban", "Suburban", "Rural"}
REQUIRED = {"name", "setting", "housing", "access", "cost", "careers", "aid", "source", "reference_year"}

def validate(payload):
    errors = []
    if not isinstance(payload, dict):
        return ["bundle must be a JSON object"]
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        errors.append("schema_version must be 1")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        return errors + ["records must be a nonempty list"]
    seen = set()
    for i, record in enumerate(records):
        prefix = f"records[{i}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        missing = REQUIRED - record.keys()
        if missing:
            errors.append(f"{prefix}: missing {sorted(missing)}")
            continue
        name = record["name"]
        if not isinstance(name, str) or not name.strip() or name.strip().casefold() in seen:
            errors.append(f"{prefix}: blank or duplicate institution name")
        if isinstance(name, str):
            seen.add(name.strip().casefold())
        if not isinstance(record["setting"], str) or record["setting"] not in SETTINGS:
            errors.append(f"{prefix}: unrecognized campus setting")
        if not isinstance(record["housing"], bool):
            errors.append(f"{prefix}: housing must be boolean")
        if record["access"] is not None and (type(record["access"]) is not int or not 1 <= record["access"] <= 3):
            errors.append(f"{prefix}: access must be null or an integer from 1 to 3")
        if not isinstance(record["cost"], dict):
            errors.append(f"{prefix}: cost must be an object")
        else:
            for band in BANDS:
                value = record["cost"].get(band)
                if band not in record["cost"] or (value is not None and (type(value) not in (float, int) or not math.isfinite(value) or value < 0)):
                    errors.append(f"{prefix}: invalid {band} cost; use null for unavailable")
        if not isinstance(record["careers"], dict) or any(k not in record["careers"] or (record["careers"][k] is not None and (type(record["careers"][k]) is not int or not 0 <= record["careers"][k] <= 3)) for k in CAREERS):
            errors.append(f"{prefix}: career signals must be null or integers 0-3")
        if not isinstance(record["aid"], list) or not all(isinstance(a, str) for a in record["aid"]):
            errors.append(f"{prefix}: aid must be a string list")
        if not isinstance(record["source"], str) or not record["source"].strip():
            errors.append(f"{prefix}: source required")
        if type(record["reference_year"]) is not int or not 2000 <= record["reference_year"] <= 2100:
            errors.append(f"{prefix}: valid reference_year required")
    return errors

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python validate-public-data.py public-data.json")
    try:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.exit(f"Invalid input: {exc}")
    issues = validate(data)
    if issues:
        print("\n".join(issues))
        sys.exit(1)
    print(f"PASS: {len(data['records'])} records passed structural validation; source verification remains a separate review.")
