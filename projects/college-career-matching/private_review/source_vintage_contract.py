"""Private field-level source/vintage validation. Never grants publication approval."""
from __future__ import annotations
import datetime as dt
import math
import re
from urllib.parse import urlsplit

SOURCES = frozenset({"college_scorecard", "ipeds", "nces", "dapip"})
STATES = frozenset({"provided", "missing", "unknown", "not_applicable"})
FIELDS = frozenset({"unitid", "source_system", "source_record_id", "field",
    "status", "value", "source_variable", "source_url", "reporting_year",
    "collection_period", "release_date", "cohort_year", "definition"})
OFFICIAL_HOSTS = frozenset({"collegescorecard.ed.gov", "nces.ed.gov",
    "data.ed.gov", "ope.ed.gov", "api.data.gov"})

def official_url(value):
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value):
        return False
    try:
        u = urlsplit(value)
        return (u.scheme == "https" and u.hostname in OFFICIAL_HOSTS
                and not u.username and not u.password
                and u.port in (None, 443) and not u.fragment)
    except ValueError:
        return False

def valid_year(value):
    return type(value) is int and 1990 <= value <= 2100

def normalize_source_field(record):
    """Retain each variable's reporting year, release date and cohort separately.

    Official-looking URLs do not prove data authenticity or permission to publish.
    """
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise ValueError("Exact field-level contract required")
    if not isinstance(record["unitid"], str) or not re.fullmatch(r"[0-9]{6}", record["unitid"]):
        raise ValueError("Six-digit UNITID required")
    if record["source_system"] not in SOURCES or record["status"] not in STATES:
        raise ValueError("Unrecognized source or evidence state")
    for key in ("source_record_id", "field", "definition"):
        if not isinstance(record[key], str) or not record[key].strip():
            raise ValueError(key + " must be explicit")
    if record["status"] == "provided":
        value = record["value"]
        if value is None or (isinstance(value, float) and not math.isfinite(value)):
            raise ValueError("Provided evidence must have finite non-null value")
        if not isinstance(record["source_variable"], str) or not record["source_variable"].strip():
            raise ValueError("Official variable name required")
        if not official_url(record["source_url"]):
            raise ValueError("Official documentation URL required")
        if not valid_year(record["reporting_year"]):
            raise ValueError("Field-level reporting year required; latest is not a year")
        if not isinstance(record["collection_period"], str) or not record["collection_period"].strip():
            raise ValueError("Collection period required")
        try:
            if not isinstance(record["release_date"], str):
                raise ValueError()
            dt.date.fromisoformat(record["release_date"])
        except ValueError:
            raise ValueError("Release date must be ISO date") from None
    elif record["value"] is not None:
        raise ValueError("Missing/unknown/not-applicable cannot carry values")
    if record["source_url"] is not None and not official_url(record["source_url"]):
        raise ValueError("Invalid source URL")
    for key in ("reporting_year", "cohort_year"):
        if record[key] is not None and not valid_year(record[key]):
            raise ValueError("Invalid " + key)
    if record["status"] == "provided" and record["field"] in (
        "net_price", "gpa_distribution", "sat_distribution", "act_distribution"
    ) and record["cohort_year"] is None:
        raise ValueError("Cohort-specific field requires cohort year")
    return {**record, "publication_status": "DO_NOT_PUBLISH",
            "public_export_allowed": False, "independently_verified": False,
            "admissions_probability": None}
