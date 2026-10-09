"""Synthetic-only NCES locale filter; not an independent institutional verifier.

A Scorecard LOCALE candidate must not be promoted to verified NCES/IPEDS
evidence merely because its code is valid. Public release is controlled
separately by the dataset-level approval gate.
"""
from dataclasses import dataclass

LOCALES = {
    11: ("City", "Large"), 12: ("City", "Midsize"), 13: ("City", "Small"),
    21: ("Suburb", "Large"), 22: ("Suburb", "Midsize"), 23: ("Suburb", "Small"),
    31: ("Town", "Fringe"), 32: ("Town", "Distant"), 33: ("Town", "Remote"),
    41: ("Rural", "Fringe"), 42: ("Rural", "Distant"), 43: ("Rural", "Remote"),
}

@dataclass(frozen=True)
class LocaleEvidence:
    unitid: str | None
    code: int | None
    source_kind: str = "SCORECARD_CANDIDATE"
    source_url: str | None = None
    source_year: int | None = None
    independently_verified: bool = False

def classify_locale(record: LocaleEvidence) -> dict:
    """Separate candidate code, verified NCES code and genuine unknown."""
    candidate = LOCALES.get(record.code) if type(record.code) is int else None
    supported = bool(
        candidate and record.unitid and record.unitid.isdigit()
        and record.source_kind == "NCES_IPEDS_UNITID"
        and record.source_url and record.source_url.startswith("https://")
        and type(record.source_year) is int and 2000 <= record.source_year <= 2100
        and record.independently_verified
    )
    return {
        "status": "VERIFIED" if supported else "UNVERIFIED",
        "candidate_code": record.code if candidate else None,
        "verified_code": record.code if supported else None,
        "group": candidate[0] if supported else None,
        "subtype": candidate[1] if supported else None,
    }

def matches_locale(record: LocaleEvidence, group: str | None = None,
                   subtype: str | None = None, include_unknown: bool = False) -> bool:
    """Unverified candidates are excluded unless unknowns are explicitly requested."""
    result = classify_locale(record)
    if result["status"] != "VERIFIED":
        return include_unknown
    if group is not None and result["group"] != group:
        return False
    if subtype is not None and result["subtype"] != subtype:
        return False
    return True
