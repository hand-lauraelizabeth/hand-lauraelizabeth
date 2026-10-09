"""Fail-closed public-bundle release gate; synthetic demo needs no approvals.

Usage: python publication_gate.py [directory containing public-data.json]
A passing structural check is NOT independent source verification or user approval.
"""
import importlib.util
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
BANDS = ("0_30k", "30_48k", "48_75k", "75_110k", "110k_plus")
CAREERS = ("data", "education", "health", "business")
ENROLLMENT = ("undergraduate", "total")


def valid_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password and parsed.port is None
    except ValueError:
        return False


def valid_year(value):
    return type(value) is int and 2000 <= value <= 2100


def evidence_ok(value, evidence, *, cost=False):
    if not isinstance(evidence, dict):
        return False
    status = evidence.get("status")
    if value is None:
        if status not in {"UNKNOWN", "NOT_APPLICABLE", "SUPPRESSED"}:
            return False
        return status != "SUPPRESSED" or (valid_url(evidence.get("source_url")) and valid_year(evidence.get("reporting_year")))
    if status != "VERIFIED" or not valid_url(evidence.get("source_url")) or not valid_year(evidence.get("reporting_year")):
        return False
    return not cost or isinstance(evidence.get("cohort_map_reference"), str) and bool(evidence["cohort_map_reference"].strip())


def check(payload, manifest):
    errors = []
    if not isinstance(payload, dict) or type(payload.get("schema_version")) is not int or payload["schema_version"] != 1 or not isinstance(payload.get("records"), list) or not payload["records"]:
        return ["Invalid publication bundle."]
    if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1 or not isinstance(manifest.get("approved_unitids"), list):
        return ["Missing or invalid publication approval manifest."]
    approvals = set()
    for item in manifest["approved_unitids"]:
        if not isinstance(item, dict) or not isinstance(item.get("unitid"), str) or not re.fullmatch(r"[0-9]{6}", item["unitid"]) or item.get("approved_by") != "user" or not isinstance(item.get("approval_reference"), str) or not item["approval_reference"].strip():
            return ["Malformed publication approval entry."]
        try:
            approved_on = item.get("approved_on")
            if not isinstance(approved_on, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", approved_on):
                raise ValueError
            date.fromisoformat(approved_on)
        except ValueError:
            return ["Malformed publication approval date."]
        if item["unitid"] in approvals:
            return ["Duplicate publication approval."]
        approvals.add(item["unitid"])
    seen = set()
    for i, record in enumerate(payload["records"]):
        prefix = f"records[{i}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix}: record must be object")
            continue
        unitid = record.get("unitid")
        if not isinstance(unitid, str) or not re.fullmatch(r"[0-9]{6}", unitid) or unitid not in approvals or unitid in seen or record.get("publication_status") != "APPROVED" or record.get("publication_approved_by_user") is not True:
            errors.append(f"{prefix}: explicit user approval missing, duplicate, or invalid UNITID")
        if isinstance(unitid, str):
            seen.add(unitid)
        provenance = record.get("field_provenance")
        if not isinstance(provenance, dict):
            errors.append(f"{prefix}: field_provenance missing")
            continue
        for key in ("setting", "housing", "access", "aid"):
            if key not in record or not evidence_ok(record[key], provenance.get(key)):
                errors.append(f"{prefix}: missing or invalid {key} provenance")
        if record.get("access") is not None:
            errors.append(f"{prefix}: campus-wide numeric accessibility rating not approved")
        if isinstance(record.get("aid"), list) and not record["aid"]:
            errors.append(f"{prefix}: empty aid list cannot establish no aid")
        for group, keys in (("cost", BANDS), ("careers", CAREERS), ("enrollment", ENROLLMENT)):
            values = record.get(group)
            if not isinstance(values, dict):
                errors.append(f"{prefix}: missing {group} object")
                continue
            for key in keys:
                value = values.get(key)
                if key not in values or not evidence_ok(value, provenance.get(f"{group}.{key}"), cost=group == "cost"):
                    errors.append(f"{prefix}: missing or invalid {group}.{key} provenance")
                if group == "enrollment" and value is not None and (type(value) is not int or value < 0):
                    errors.append(f"{prefix}: invalid {group}.{key} count")
        if record.get("testing_policy", "unknown") not in ("unknown", None):
            if record.get("testing_policy") not in ("required", "optional", "blind") or record.get("testing_policy_verified") is not True or not valid_url(record.get("testing_policy_source")) or not valid_year(record.get("testing_policy_year")):
                errors.append(f"{prefix}: institutional testing policy unverified")
    return errors


def main(directory=ROOT):
    directory = Path(directory)
    bundle = directory / "public-data.json"
    if not bundle.exists():
        print("PASS: no public institution bundle; synthetic demonstration only.")
        return 0
    try:
        payload = json.loads(bundle.read_text(encoding="utf-8"))
        manifest = json.loads((directory / "publication-approvals.json").read_text(encoding="utf-8"))
        spec = importlib.util.spec_from_file_location("matcher_validator", ROOT / "validate-public-data.py")
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        errors = validator.validate(payload) + check(payload, manifest)
    except (OSError, ValueError, TypeError) as exc:
        errors = [str(exc)]
    if errors:
        print("FAIL: institution publication blocked:\n" + "\n".join(errors))
        return 1
    print("PASS: release-gate metadata checks passed. Independent evidence and user approval must still be audited.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ROOT))
