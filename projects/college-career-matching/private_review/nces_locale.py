"""NCES locale definitions for private institutional evidence review.

The codebook edition is the definition vintage, NOT an institution's observation
year. A school-level reporting year must be verified independently.
"""
from dataclasses import dataclass
from typing import Optional

DEFINITION_URL = "https://nces.ed.gov/pubs2014/2014039.pdf"
DEFINITION_EDITION = "2012 codebook; definition vintage only"

LOCALE_LABELS = {
    "11": ("City", "City: Large"),
    "12": ("City", "City: Midsize"),
    "13": ("City", "City: Small"),
    "21": ("Suburb", "Suburb: Large"),
    "22": ("Suburb", "Suburb: Midsize"),
    "23": ("Suburb", "Suburb: Small"),
    "31": ("Town", "Town: Fringe"),
    "32": ("Town", "Town: Distant"),
    "33": ("Town", "Town: Remote"),
    "41": ("Rural", "Rural: Fringe"),
    "42": ("Rural", "Rural: Distant"),
    "43": ("Rural", "Rural: Remote"),
}

@dataclass(frozen=True)
class LocaleReview:
    raw: Optional[str]
    category: str
    detail: Optional[str]
    definition_url: str
    definition_edition: str
    observation_reporting_year: Optional[int]
    observation_source_url: Optional[str]
    evidence_status: str
    publication_status: str


def describe_locale(value: object) -> LocaleReview:
    raw = (str(value) if isinstance(value, int) and not isinstance(value, bool) else
           value.strip() if isinstance(value, str) else None)
    category, detail = LOCALE_LABELS.get(raw, ("Unknown", None))
    return LocaleReview(
        raw=raw, category=category, detail=detail,
        definition_url=DEFINITION_URL,
        definition_edition=DEFINITION_EDITION,
        observation_reporting_year=None,
        observation_source_url=None,
        evidence_status="PENDING_INSTITUTIONAL_VERIFICATION",
        publication_status="DO_NOT_PUBLISH",
    )
