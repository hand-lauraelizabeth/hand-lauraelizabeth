"""Synthetic-only housing classification and filtering. Not an institutional evidence verifier."""
from dataclasses import dataclass
from enum import Enum

class HousingType(str, Enum):
    ON_CAMPUS = "ON_CAMPUS"
    AFFILIATED_OFF_CAMPUS = "AFFILIATED_OFF_CAMPUS"
    PARTNER_CAMPUS = "PARTNER_CAMPUS"
    REFERRAL_ONLY = "REFERRAL_ONLY"
    DOCUMENTED_NONE = "DOCUMENTED_NONE"
    UNKNOWN = "UNKNOWN"

class Availability(str, Enum):
    CONFIRMED_FOR_TERM = "CONFIRMED_FOR_TERM"
    WAITLIST = "WAITLIST"
    UNAVAILABLE_FOR_TERM = "UNAVAILABLE_FOR_TERM"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class HousingEvidence:
    housing_type: HousingType
    availability: Availability
    availability_term: str | None
    source_url: str | None
    unitid: str | None
    verified: bool = False
    publication_status: str = "DO_NOT_PUBLISH"
    owner_approved: bool = False


def classify_housing(e: HousingEvidence, requested_term: str | None = None) -> dict:
    """Classify evidence without conflating housing type, vacancy, or publication permission."""
    on_campus = e.housing_type is HousingType.ON_CAMPUS
    term_matches = bool(requested_term and e.availability_term == requested_term)
    confirmed = bool(on_campus and term_matches and e.availability is Availability.CONFIRMED_FOR_TERM and e.verified)
    publishable = bool(e.publication_status == "APPROVED" and e.owner_approved and e.verified and e.source_url and e.unitid)
    return {"on_campus": on_campus, "confirmed_vacancy": confirmed, "publishable": publishable,
            "unknown_housing": e.housing_type is HousingType.UNKNOWN,
            "documented_none": e.housing_type is HousingType.DOCUMENTED_NONE}


def public_filter(records: list[HousingEvidence], requested_term: str | None = None) -> list[HousingEvidence]:
    """Deny publication by default, including all private evidence-queue records."""
    return [e for e in records if classify_housing(e, requested_term)["publishable"]]
