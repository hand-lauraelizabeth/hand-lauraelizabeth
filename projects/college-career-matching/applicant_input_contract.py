"""Private applicant-input contract: descriptive matching, never admission prediction.

Missing, unknown and not-applicable are distinct. Institutional values require
independently reviewed provenance before they may appear in public releases.
"""
from __future__ import annotations

import math

GPA_SCALES = ("4.0", "other")
TEST_POLICIES = ("required", "optional", "blind", "unknown")
ENROLLMENT_DEFINITIONS = ("undergraduate", "total")
MISSING_STATES = ("missing", "unknown", "not_applicable")
ACT_SECTIONS = ("english", "math", "reading", "science")
SAT_SECTIONS = ("reading_writing", "math")


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return value


def _integer(value, name, low, high):
    value = _number(value, name)
    if not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low} to {high}")
    return value


def _state(value):
    if value not in MISSING_STATES:
        raise ValueError("Missing-value status must be missing, unknown or not_applicable")
    return {"status": value, "value": None}


def validate_gpa_scale(scale):
    if scale not in GPA_SCALES:
        raise ValueError("Unsupported GPA scale")
    return scale


def validate_weighting(value):
    if value not in ("weighted", "unweighted"):
        raise ValueError("GPA weighting must be declared")
    return value


def validate_gpa(value=None, *, scale=None, weighting=None, maximum=None, status=None):
    """Require explicit scale and weighting; never convert between scales."""
    if status is not None:
        if value is not None or scale is not None or weighting is not None or maximum is not None:
            raise ValueError("Missing GPA must not contain a numeric value or scale")
        return _state(status)
    validate_gpa_scale(scale)
    validate_weighting(weighting)
    value = _number(value, "GPA")
    if maximum is None:
        if scale != "4.0" or weighting != "unweighted":
            raise ValueError("Weighted and non-4.0 GPAs require an explicit maximum")
        maximum = 4.0
    maximum = _number(maximum, "GPA maximum")
    if maximum <= 0 or (scale == "4.0" and weighting == "unweighted" and maximum != 4.0):
        raise ValueError("Invalid GPA maximum for declared scale")
    if not 0 <= value <= maximum:
        raise ValueError("GPA outside declared scale")
    return {"status": "provided", "value": value, "scale": scale, "weighting": weighting, "maximum": maximum}


def validate_sat(total=None, *, reading_writing=None, math=None, status=None):
    if status is not None:
        if any(v is not None for v in (total, reading_writing, math)):
            raise ValueError("Omitted SAT scores cannot include numeric scores")
        return {"test": "SAT", **_state(status)}
    if all(v is None for v in (total, reading_writing, math)):
        raise ValueError("Use a missing-value status when SAT scores are omitted")
    sections = {}
    for name, value in (("reading_writing", reading_writing), ("math", math)):
        if value is not None:
            score = _integer(value, name, 200, 800)
            if score % 10:
                raise ValueError("SAT section scores must be in 10-point increments")
            sections[name] = score
    if total is not None:
        total = _integer(total, "SAT total", 400, 1600)
        if total % 10:
            raise ValueError("SAT total must be in 10-point increments")
    if len(sections) == 2:
        calculated = sum(sections.values())
        if total is not None and total != calculated:
            raise ValueError("SAT total does not equal the sum of sections")
        total = calculated
    return {"test": "SAT", "status": "provided", "total": total, "sections": sections}


def validate_act(composite=None, *, english=None, math=None, reading=None, science=None, status=None):
    values = (composite, english, math, reading, science)
    if status is not None:
        if any(v is not None for v in values):
            raise ValueError("Omitted ACT scores cannot include numeric scores")
        return {"test": "ACT", **_state(status)}
    if all(v is None for v in values):
        raise ValueError("Use a missing-value status when ACT scores are omitted")
    sections = {}
    for name, value in zip(ACT_SECTIONS, (english, math, reading, science)):
        if value is not None:
            sections[name] = _integer(value, f"ACT {name}", 1, 36)
    if composite is not None:
        composite = _integer(composite, "ACT composite", 1, 36)
    # ACT composite calculation varies by testing date; do not infer it from sections.
    return {"test": "ACT", "status": "provided", "composite": composite, "sections": sections}


def testing_evidence(policy, score):
    """A policy-aware descriptive indicator, not an admissions score or cutoff."""
    if policy not in TEST_POLICIES:
        raise ValueError("Unsupported testing policy")
    if score is not None and (not isinstance(score, dict) or score.get("test") not in ("SAT", "ACT")
                              or score.get("status") not in (*MISSING_STATES, "provided")):
        raise ValueError("Use a validated SAT or ACT input")
    if policy == "blind":
        return {"consider_scores": False, "evidence": "test_blind", "admission_probability": None}
    if policy == "unknown":
        return {"consider_scores": False, "evidence": "policy_unknown", "admission_probability": None}
    provided = score is not None and score["status"] == "provided"
    evidence = "reported_scores" if provided else ("required_scores_unavailable" if policy == "required" else "scores_omitted_allowed")
    return {"consider_scores": provided, "evidence": evidence, "admission_probability": None}


def validate_enrollment(value=None, *, definition, status=None):
    if definition not in ENROLLMENT_DEFINITIONS:
        raise ValueError("Enrollment must distinguish undergraduate from total")
    if status is not None:
        if value is not None:
            raise ValueError("Missing enrollment cannot include a numeric value")
        return {"definition": definition, **_state(status)}
    return {"definition": definition, "status": "provided",
            "value": _integer(value, "enrollment", 0, 100_000_000)}


def enrollment_preference(record, *, definition, minimum=None, maximum=None, mode="filter"):
    """Unknown institutional counts are unverified, never zero or a definite mismatch."""
    if mode not in ("filter", "preference") or definition not in ENROLLMENT_DEFINITIONS:
        raise ValueError("Invalid enrollment matching mode or definition")
    if minimum is None and maximum is None:
        raise ValueError("Specify an enrollment range")
    for label, bound in (("minimum", minimum), ("maximum", maximum)):
        if bound is not None:
            _integer(bound, label, 0, 100_000_000)
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("Minimum exceeds maximum")
    if record["definition"] != definition:
        return {"match": None, "reason": "enrollment_definition_mismatch", "mode": mode}
    if record["status"] != "provided":
        return {"match": None, "reason": "enrollment_unknown", "mode": mode}
    value = record["value"]
    match = (minimum is None or value >= minimum) and (maximum is None or value <= maximum)
    return {"match": match, "reason": "within_range" if match else "outside_range", "mode": mode}


def _official_reference(unitid, source_url, reporting_year, admissions_cohort):
    """Institution-specific provenance; a release date is not a cohort year."""
    if not isinstance(unitid, str) or len(unitid) != 6 or not unitid.isascii() or not unitid.isdigit():
        raise ValueError("Official institution evidence requires a six-digit UNITID")
    if not isinstance(source_url, str) or not source_url.startswith("https://") or len(source_url) <= 8:
        raise ValueError("Official evidence requires an HTTPS source URL")
    if isinstance(reporting_year, bool) or not isinstance(reporting_year, int) or not 1990 <= reporting_year <= 2026:
        raise ValueError("Institution-specific reporting year required")
    if not isinstance(admissions_cohort, str) or not admissions_cohort.strip():
        raise ValueError("Admissions cohort required; a data release date is insufficient")
    return {"unitid": unitid, "source_url": source_url,
            "reporting_year": reporting_year, "admissions_cohort": admissions_cohort.strip()}


def validate_institution_testing_policy(policy, *, unitid, source_url=None,
                                        reporting_year=None, admissions_cohort=None,
                                        independently_reviewed=False):
    """Private evidence. Unreviewed policies NEVER influence matching."""
    if policy not in TEST_POLICIES:
        raise ValueError("Unsupported testing policy")
    if not isinstance(independently_reviewed, bool):
        raise ValueError("Independent review must be boolean")
    if policy == "unknown":
        if independently_reviewed:
            raise ValueError("Unknown policy cannot be independently verified")
        if any(v is not None for v in (source_url, reporting_year, admissions_cohort)):
            raise ValueError("Unknown policy should not imply source-verified policy evidence")
        if not isinstance(unitid, str) or len(unitid) != 6 or not unitid.isascii() or not unitid.isdigit():
            raise ValueError("Six-digit UNITID required")
        provenance = {"unitid": unitid, "source_url": None,
                      "reporting_year": None, "admissions_cohort": None}
    else:
        provenance = _official_reference(unitid, source_url, reporting_year, admissions_cohort)
    return {**provenance, "reported_policy": policy,
            "effective_policy": policy if independently_reviewed else "unknown",
            "independently_reviewed": independently_reviewed,
            "publication_status": "DO_NOT_PUBLISH"}


def testing_evidence_with_provenance(policy_record, score):
    """Only independently reviewed school policy may enable descriptive scores."""
    if not isinstance(policy_record, dict) or policy_record.get("publication_status") != "DO_NOT_PUBLISH":
        raise ValueError("Private institutional policy evidence required")
    policy = policy_record.get("effective_policy")
    if policy not in TEST_POLICIES:
        raise ValueError("Invalid effective testing policy")
    decision = testing_evidence(policy, score)
    return {**decision, "confidence": "reviewed_policy" if policy_record.get("independently_reviewed") else "policy_unverified",
            "policy_reporting_year": policy_record.get("reporting_year"),
            "policy_admissions_cohort": policy_record.get("admissions_cohort"),
            "policy_source_url": policy_record.get("source_url"),
            "admission_probability": None}


def validate_institution_enrollment(value=None, *, definition, unitid,
                                    source_url=None, reporting_year=None,
                                    status=None, independently_reviewed=False):
    """Private enrollment evidence; definition and reporting year remain separate."""
    if not isinstance(independently_reviewed, bool):
        raise ValueError("Independent review must be boolean")
    count = validate_enrollment(value, definition=definition, status=status)
    if count["status"] == "provided":
        provenance = _official_reference(unitid, source_url, reporting_year,
                                         f"Enrollment {reporting_year}")
    else:
        if any(v is not None for v in (source_url, reporting_year)):
            raise ValueError("Missing enrollment cannot carry asserted source evidence")
        if not isinstance(unitid, str) or len(unitid) != 6 or not unitid.isascii() or not unitid.isdigit():
            raise ValueError("Six-digit UNITID required")
        if independently_reviewed:
            raise ValueError("Missing enrollment is not a verified numeric count")
        provenance = {"unitid": unitid, "source_url": None, "reporting_year": None}
    return {**count, "unitid": provenance["unitid"],
            "source_url": provenance["source_url"],
            "reporting_year": provenance["reporting_year"],
            "independently_reviewed": independently_reviewed,
            "publication_status": "DO_NOT_PUBLISH"}


def enrollment_evidence_preference(record, *, definition, minimum=None,
                                   maximum=None, mode="filter"):
    """Unreviewed counts remain unknown rather than a positive or negative match."""
    if not isinstance(record, dict) or record.get("publication_status") != "DO_NOT_PUBLISH":
        raise ValueError("Private institution enrollment record required")
    if not record.get("independently_reviewed"):
        # Validate range and mode even if institutional evidence is unavailable.
        check = enrollment_preference({"definition": definition, "status": "unknown"},
                                      definition=definition, minimum=minimum,
                                      maximum=maximum, mode=mode)
        return {**check, "reason": "enrollment_source_unverified",
                "confidence": "insufficient_evidence"}
    result = enrollment_preference(record, definition=definition,
                                   minimum=minimum, maximum=maximum, mode=mode)
    return {**result, "confidence": "reviewed_official_source" if result["match"] is not None
            else "insufficient_evidence"}
