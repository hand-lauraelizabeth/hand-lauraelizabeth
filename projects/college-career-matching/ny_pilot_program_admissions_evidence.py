"""Source-attributed admissions-stage evidence for review, not a live data feed.

Institution-level SAT/ACT policies, program entrance exams, and licensure
examinations are different questions. No missing federal test-score value
is treated as evidence of a testing policy. No record authorizes publication.
"""
from __future__ import annotations

from datetime import date
from typing import Mapping

VERIFIED_ON = "2026-11-02"
HUNTER = "Hunter College"
FRESHMAN = "https://www.hunter.cuny.edu/students/admissions/undergraduate/apply/freshman/"
GENERIC = "https://www.hunter.cuny.edu/hunter-bellevue-school-of-nursing/prospective-students/undergraduate-nursing-programs/bachelor-of-science-bs-in-nursing-program/"
ACCELERATED = "https://www.hunter.cuny.edu/hunter-bellevue-school-of-nursing/prospective-students/undergraduate-nursing-programs/accelerated-second-degree-nursing-program-a2d/"
RN_TO_BS = "https://www.hunter.cuny.edu/hunter-bellevue-school-of-nursing/prospective-students/undergraduate-nursing-programs/rn-to-bs-nursing-program/"
LICENSURE = "https://www.hunter.cuny.edu/hunter-bellevue-school-of-nursing/prospective-students/professional-licensure-disclosures/"
BOARD = "https://www.cuny.edu/main/wp-content/uploads/sites/4/page-assets/about/trustees/meetings-of-the-board/CAL0626.pdf"

# All statements below come from named institutional pages; program-level
# regulatory registration and current applicant-cycle terms need further review.
REVIEW_RECORDS = (
    dict(route="general_freshman", stage="institution_freshman", assessment="SAT_ACT",
         requirement="optional", source=FRESHMAN, verified_on=VERIFIED_ON,
         prior_credential="none", nex_weight=None, gpa_weight=None,
         honors_scores_encouraged=True, cip_code=None),
    dict(route="generic_bs", stage="nursing_major", assessment="NEX",
         requirement="required", source=GENERIC, verified_on=VERIFIED_ON,
         prior_credential="hunter_matriculation_and_prerequisites",
         nex_weight=0.5, gpa_weight=0.5, honors_scores_encouraged=False,
         cip_code="51.3801"),
    dict(route="accelerated_second_degree_bs", stage="nursing_major",
         assessment="NEX", requirement="required", source=ACCELERATED,
         verified_on=VERIFIED_ON, prior_credential="non_nursing_bachelors",
         nex_weight=0.5, gpa_weight=0.5, honors_scores_encouraged=False,
         cip_code="51.3801"),
    dict(route="rn_to_bs", stage="licensed_rn_completion", assessment="NEX",
         requirement="unknown", source=RN_TO_BS, verified_on=VERIFIED_ON,
         prior_credential="existing_ny_rn_license_and_nursing_associates",
         nex_weight=None, gpa_weight=None, honors_scores_encouraged=False,
         cip_code="51.3801"),
)
VALID_STAGES = {"institution_freshman", "nursing_major", "licensed_rn_completion"}
VALID_REQUIREMENTS = {"required", "optional", "unknown"}
VALID_ASSESSMENTS = {"SAT_ACT", "NEX"}
VALID_ROUTES = {"general_freshman", "generic_bs", "accelerated_second_degree_bs", "rn_to_bs"}
VALID_CREDENTIALS = {"none", "hunter_matriculation_and_prerequisites",
                     "non_nursing_bachelors", "existing_ny_rn_license_and_nursing_associates"}


def validate_record(record: Mapping) -> None:
    required = ("route", "stage", "assessment", "requirement", "source",
                "verified_on", "prior_credential", "nex_weight", "gpa_weight",
                "honors_scores_encouraged", "cip_code")
    if any(key not in record for key in required):
        raise ValueError("Incomplete source-attributed admissions record")
    if (record["route"] not in VALID_ROUTES
            or record["stage"] not in VALID_STAGES
            or record["assessment"] not in VALID_ASSESSMENTS
            or record["requirement"] not in VALID_REQUIREMENTS
            or record["prior_credential"] not in VALID_CREDENTIALS):
        raise ValueError("Unsupported admissions evidence classification")
    if not isinstance(record["source"], str) or not record["source"].startswith("https://www.hunter.cuny.edu/"):
        raise ValueError("Publisher source URL required")
    try:
        date.fromisoformat(record["verified_on"])
    except (TypeError, ValueError):
        raise ValueError("Source verification date required") from None
    if type(record["honors_scores_encouraged"]) is not bool:
        raise ValueError("Honors preference must be explicit")
    route, stage, exam = record["route"], record["stage"], record["assessment"]
    if route == "general_freshman":
        if stage != "institution_freshman" or exam != "SAT_ACT" or record["prior_credential"] != "none":
            raise ValueError("General SAT/ACT policy must stay at the institution stage")
    elif route == "rn_to_bs":
        if stage != "licensed_rn_completion" or record["prior_credential"] != "existing_ny_rn_license_and_nursing_associates":
            raise ValueError("RN-to-BS must retain existing-licensure prerequisite")
    elif stage != "nursing_major" or exam != "NEX":
        raise ValueError("Prelicensure nursing selection is separate from freshman SAT/ACT")
    weights = (record["nex_weight"], record["gpa_weight"])
    if route in {"generic_bs", "accelerated_second_degree_bs"}:
        if record["requirement"] != "required" or weights != (0.5, 0.5):
            raise ValueError("Published nursing selection composite must be attributed")
    elif weights != (None, None):
        raise ValueError("Do not propagate nursing selection weights to other routes")
    if route == "rn_to_bs" and record["requirement"] != "unknown":
        raise ValueError("RN-to-BS NEX status has not been independently established")


def build_review_summary(records=REVIEW_RECORDS, route="generic_bs",
                         scorecard_sat=None, scorecard_act=None) -> dict:
    """Return stage-separated facts. Scorecard fields are intentionally unused."""
    by_route = {}
    for record in records:
        validate_record(record)
        if record["route"] in by_route:
            raise ValueError("Duplicate route evidence")
        by_route[record["route"]] = record
    if "general_freshman" not in by_route or route not in by_route or route == "general_freshman":
        raise ValueError("One institution record and a distinct program route are required")
    general, program = by_route["general_freshman"], by_route[route]
    general_text = {
        "optional": "SAT/ACT submission is optional for general freshman admission.",
        "required": "SAT/ACT submission is required for general freshman admission.",
        "unknown": "General freshman SAT/ACT policy has not been established.",
    }[general["requirement"]]
    program_text = {
        "required": "NEX is required for this nursing-program selection route.",
        "optional": "NEX is optional for this nursing-program selection route.",
        "unknown": "NEX requirement for this route has not been established.",
    }[program["requirement"]]
    prerequisites = {
        "hunter_matriculation_and_prerequisites": "Separate nursing-major application after matriculation and prerequisites.",
        "non_nursing_bachelors": "Requires a prior non-nursing bachelor's degree.",
        "existing_ny_rn_license_and_nursing_associates": "Requires an existing New York RN license and nursing associate degree.",
    }[program["prior_credential"]]
    return {
        "institution": HUNTER, "route": route, "general_admissions": general_text,
        "program_selection": program_text, "prior_qualification": prerequisites,
        "honors_score_preference": ("Scores encouraged for certain honors or merit programs; "
                                    "this does not make general admission test-required.")
                                    if general["honors_scores_encouraged"] else None,
        "licensure": ("Hunter describes its nursing BS pathways as meeting New York educational "
                      "requirements; independent regulator program-code verification is pending. "
                      "NEX is not the NCLEX-RN licensure examination."),
        "source_urls": [general["source"], program["source"], LICENSURE, BOARD],
        "verified_on": VERIFIED_ON, "applicant_cycle": "unverified",
        "program_deadline": None, "regulator_verified": False,
        "nursing_admission_guaranteed": False, "rn_license_guaranteed": False,
        "publication_cleared": False,
    }
