"""Private staging adapter for real institution directory facts.

No public file is written. A caller must separately review and approve any release.
Input is a list of source-backed records with field-level citations and dates.
"""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path

REQUIRED = ("unitid", "name", "state", "source_url", "retrieved_at")
DIRECTORY_FIELDS = ("name", "state", "city", "control", "undergraduate_enrollment", "test_policy")
ALLOWED_POLICIES = {"test_required", "test_optional", "test_blind", "unknown"}

def validate_record(record):
    errors = []
    for key in REQUIRED:
        if not record.get(key):
            errors.append(f"Missing {key}")
    unitid = record.get("unitid")
    if isinstance(unitid, bool) or not isinstance(unitid, int) or unitid <= 0:
        errors.append("unitid must be a positive integer")
    if record.get("state") and (not isinstance(record["state"], str) or len(record["state"]) != 2):
        errors.append("state must be a two-letter abbreviation")
    try:
        date.fromisoformat(record["retrieved_at"])
    except (KeyError, TypeError, ValueError):
        errors.append("retrieved_at must be an ISO date")
    if not str(record.get("source_url", "")).startswith("https://"):
        errors.append("source_url must be HTTPS")
    evidence = record.get("field_evidence", {})
    if not isinstance(evidence, dict):
        errors.append("field_evidence must be a mapping")
        evidence = {}
    for field in DIRECTORY_FIELDS:
        value = record.get(field)
        if value is None:
            continue
        proof = evidence.get(field)
        if not isinstance(proof, dict) or not str(proof.get("url", "")).startswith("https://") or not proof.get("as_of"):
            errors.append(f"{field} needs source URL and as_of")
    enrollment = record.get("undergraduate_enrollment")
    if enrollment is not None and (isinstance(enrollment, bool) or not isinstance(enrollment, int) or enrollment < 0):
        errors.append("undergraduate_enrollment must be nonnegative integer or unknown")
    if record.get("test_policy") not in (None, *ALLOWED_POLICIES):
        errors.append("test_policy is invalid")
    return errors

def scorecard_directory_record(source, retrieved_at, source_url, reporting_year):
    """Map one official Scorecard institution row into private review form.

    Only identity and undergraduate enrollment are mapped. Admissions policies,
    accessibility, housing, aid and accreditation remain unknown pending their
    independent official sources and field-specific review.
    """
    unitid = source.get("UNITID")
    try:
        unitid = int(unitid)
    except (TypeError, ValueError):
        unitid = None
    enrollment = source.get("UGDS")
    try:
        enrollment = int(enrollment) if enrollment not in (None, "", "NULL", "PrivacySuppressed") else None
    except (TypeError, ValueError):
        enrollment = None
    fields = {"name": source.get("INSTNM"), "state": source.get("STABBR"),
              "city": source.get("CITY"), "control": source.get("CONTROL"),
              "undergraduate_enrollment": enrollment}
    evidence = {key: {"url": source_url, "as_of": str(reporting_year),
                      "source_field": {"name": "INSTNM", "state": "STABBR",
                                       "city": "CITY", "control": "CONTROL",
                                       "undergraduate_enrollment": "UGDS"}[key]}
                for key, value in fields.items() if value is not None}
    return {"unitid": unitid, **fields, "test_policy": None,
            "source_url": source_url, "retrieved_at": retrieved_at,
            "field_evidence": evidence,
            "publication_status": "DO_NOT_PUBLISH"}

def stage_records(records, destination):
    """Produce PRIVATE review artifact only; never an importable public-data.json."""
    seen = set()
    staged = []
    for row in records:
        problems = validate_record(row)
        if row.get("unitid") in seen:
            problems.append("Duplicate UNITID")
        seen.add(row.get("unitid"))
        staged.append({"record": row, "validation_errors": problems,
                       "publication_status": "DO_NOT_PUBLISH"})
    target = Path(destination)
    resolved = target.resolve()
    parts = {part.lower() for part in resolved.parts}
    if target.name.lower() == "public-data.json" or any("public" in part or part in {"docs", "site", "dist", "build", "www", "static"} for part in parts):
        raise ValueError("Private staging cannot target a public or deployable data path")
    if target.suffix.lower() != ".json":
        raise ValueError("Private staging requires a JSON review artifact")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"schema_version": 1, "records": staged,
                                  "publication_status": "DO_NOT_PUBLISH"},
                                 indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return staged
