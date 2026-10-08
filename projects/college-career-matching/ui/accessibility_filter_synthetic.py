"""Synthetic-only feature-level accessibility evidence; no campus-wide ratings."""
from dataclasses import dataclass
from enum import Enum
from typing import AbstractSet

class FeatureState(str, Enum):
    OBSERVED_YES = "OBSERVED_YES"
    OBSERVED_NO = "OBSERVED_NO"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_PUBLISHED = "NOT_PUBLISHED"

FEATURES = frozenset({
    "disability_services", "academic_accommodations", "accessible_housing_process",
    "building_access", "transit_path_access", "digital_accessibility"
})

@dataclass(frozen=True)
class AccessibilityEvidence:
    unitid: str | None
    feature: str
    state: FeatureState
    source_url: str | None = None
    reviewed_at: str | None = None
    independently_verified: bool = False
    owner_approved: bool = False
    publication_status: str = "DO_NOT_PUBLISH"

def classify_feature(record: AccessibilityEvidence) -> dict:
    """Do not turn missing or unreviewed evidence into a negative finding."""
    valid = bool(
        record.feature in FEATURES and record.unitid and record.unitid.isdigit()
        and record.source_url and record.source_url.startswith("https://")
        and record.reviewed_at and record.independently_verified
    )
    state = record.state if valid else FeatureState.UNKNOWN
    return {"feature": record.feature, "state": state.value,
            "verified": valid, "supported_yes": valid and state is FeatureState.OBSERVED_YES,
            "supported_no": valid and state is FeatureState.OBSERVED_NO}

def matches_feature(record: AccessibilityEvidence, feature: str,
                    include_unknown: bool = False) -> bool:
    if record.feature != feature or feature not in FEATURES:
        return False
    result = classify_feature(record)
    return result["supported_yes"] or (include_unknown and result["state"] == "UNKNOWN")

def public_filter(records: list[AccessibilityEvidence],
                  approved_unitids: AbstractSet[str] | None = None) -> list[AccessibilityEvidence]:
    """Separate owner approval and allowlist are mandatory for release."""
    if not approved_unitids:
        return []
    return [r for r in records if r.unitid in approved_unitids
            and r.publication_status == "APPROVED" and r.owner_approved
            and classify_feature(r)["verified"]]
