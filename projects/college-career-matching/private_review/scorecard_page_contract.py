"""Private Scorecard page normalizer. Synthetic/staged input only; never fetches or publishes."""
from __future__ import annotations

import re
from source_vintage_contract import normalize_source_field

OWNERSHIP = {1: "public", 2: "private_nonprofit", 3: "private_for_profit"}
LOCALES = {11: "city", 12: "city", 13: "city", 21: "suburb", 22: "suburb",
           23: "suburb", 31: "town", 32: "town", 33: "town",
           41: "rural", 42: "rural", 43: "rural"}


def _unitid(raw):
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        raise ValueError("UNITID must be integer or six-digit string")
    if isinstance(raw, int):
        if not 0 <= raw <= 999999:
            raise ValueError("UNITID out of range")
        return f"{raw:06d}"
    if not re.fullmatch(r"[0-9]{6}", raw):
        raise ValueError("UNITID must have six digits")
    return raw


def normalize_scorecard_page(*, response, enrollment_year, field_years,
                             release_date, collection_period, source_url):
    """Normalize one bounded flat API page; preserve separate field vintages.

    Does not treat API data, a source URL, or a year label as independent
    verification. Returned evidence is always DO_NOT_PUBLISH.
    """
    if type(enrollment_year) is not int or not 1990 <= enrollment_year <= 2100:
        raise ValueError("Explicit enrollment reporting year required")
    if not isinstance(field_years, dict) or set(field_years) != {"school.ownership", "school.locale"}:
        raise ValueError("Field-specific ownership and locale vintages required")
    if any(type(y) is not int or not 1990 <= y <= 2100 for y in field_years.values()):
        raise ValueError("Invalid field reporting year")
    if not isinstance(response, dict) or set(response) != {"metadata", "results"}:
        raise ValueError("Expected Scorecard metadata and results")
    meta, rows = response["metadata"], response["results"]
    if not isinstance(meta, dict) or not isinstance(rows, list):
        raise ValueError("Malformed page")
    if any(type(meta.get(k)) is not int for k in ("page", "per_page", "total")):
        raise ValueError("Explicit pagination metadata required")
    page, per_page, total = (meta[k] for k in ("page", "per_page", "total"))
    if not (page >= 0 and 1 <= per_page <= 100 and total >= 0
            and len(rows) <= per_page and page * per_page <= total
            and len(rows) <= max(0, total - page * per_page)):
        raise ValueError("Inconsistent pagination")
    size_field = f"{enrollment_year}.student.size"
    fields = {"school.ownership", "school.locale", size_field}
    normalized, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or not {"id", "school.state"}.issubset(row):
            raise ValueError("Institution identity and state required")
        if any(str(key).startswith("latest.") for key in row):
            raise ValueError("Unversioned latest fields are not admissible")
        if not set(row).issubset(fields | {"id", "school.state", "school.name"}):
            raise ValueError("Unexpected Scorecard field")
        unitid = _unitid(row["id"])
        if unitid in seen:
            raise ValueError("Duplicate UNITID in page")
        seen.add(unitid)
        if row["school.state"] != "NY":
            raise ValueError("Private NY pilot requires explicit NY state")
        for variable, field, definition, year in (
            ("school.ownership", "control", "institutional control", field_years["school.ownership"]),
            ("school.locale", "locale", "NCES urban-centric locale", field_years["school.locale"]),
            (size_field, "undergraduate_enrollment",
             "undergraduate students; not total enrollment", enrollment_year),
        ):
            raw = row.get(variable)
            status = "unknown" if raw is None else "provided"
            if raw is not None:
                if type(raw) is not int:
                    raise ValueError("Expected integer Scorecard category/count")
                if variable == "school.ownership":
                    if raw not in OWNERSHIP:
                        raise ValueError("Invalid control code")
                    value = OWNERSHIP[raw]
                elif variable == "school.locale":
                    if raw not in LOCALES:
                        raise ValueError("Invalid NCES locale code")
                    value = {"code": raw, "category": LOCALES[raw]}
                else:
                    if raw < 0:
                        raise ValueError("Enrollment cannot be negative")
                    value = raw
            else:
                value = None
            record = {"unitid": unitid, "source_system": "college_scorecard",
                      "source_record_id": unitid, "field": field, "status": status,
                      "value": value, "source_variable": variable,
                      "source_url": source_url, "reporting_year": year,
                      "collection_period": collection_period, "release_date": release_date,
                      "cohort_year": None, "definition": definition}
            normalized.append(normalize_source_field(record))
    return {"records": normalized, "pagination": {"page": page, "per_page": per_page,
            "total": total}, "publication_status": "DO_NOT_PUBLISH",
            "independently_verified": False, "public_export_allowed": False,
            "admissions_probability": None}
