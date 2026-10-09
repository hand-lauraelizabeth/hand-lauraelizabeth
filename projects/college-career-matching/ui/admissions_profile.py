"""Admission-profile input validation for the College + Career Matcher.

This module never estimates acceptance probability. Missing school-level evidence
remains unknown; GPA scales are not converted without an explicit method.
"""
from __future__ import annotations

def validate_profile(profile):
    errors = []
    gpa = profile.get("gpa")
    scale = profile.get("gpa_scale")
    if gpa is not None:
        if scale not in ("4.0", "5.0", "100"):
            errors.append("GPA scale must be explicit (4.0, 5.0, or 100).")
        elif isinstance(gpa, bool) or not isinstance(gpa, (int, float)) or not (0 <= gpa <= float(scale)):
            errors.append("GPA must be within its declared scale.")
    if profile.get("gpa_weighting") not in (None, "weighted", "unweighted", "unknown"):
        errors.append("GPA weighting must be weighted, unweighted, or unknown.")
    sat = profile.get("sat_total")
    if sat is not None and (isinstance(sat, bool) or not isinstance(sat, int) or not (400 <= sat <= 1600) or sat % 10):
        errors.append("SAT total must be 400–1600 in increments of 10.")
    act = profile.get("act_composite")
    if act is not None and (isinstance(act, bool) or not isinstance(act, int) or not (1 <= act <= 36)):
        errors.append("ACT composite must be 1–36.")
    for key in ("min_undergrad_enrollment", "max_undergrad_enrollment"):
        n = profile.get(key)
        if n is not None and (isinstance(n, bool) or not isinstance(n, int) or n < 0):
            errors.append(f"{key} must be a nonnegative whole number.")
    lo, hi = profile.get("min_undergrad_enrollment"), profile.get("max_undergrad_enrollment")
    if lo is not None and hi is not None and lo > hi:
        errors.append("Minimum school size exceeds maximum.")
    return errors

def school_size_match(profile, institution):
    """Return True, False, or None (unknown). Uses undergraduate headcount only."""
    n = institution.get("undergraduate_enrollment")
    if n is None:
        return None
    lo, hi = profile.get("min_undergrad_enrollment"), profile.get("max_undergrad_enrollment")
    return (lo is None or n >= lo) and (hi is None or n <= hi)

def testing_context(profile, institution):
    """Context, not admission odds. Test-blind institutions do not evaluate scores."""
    policy = institution.get("test_policy")
    if policy == "test_blind":
        return "SCORES_NOT_CONSIDERED"
    if policy == "test_optional" and profile.get("sat_total") is None and profile.get("act_composite") is None:
        return "OPTIONAL_SCORES_OMITTED"
    if policy not in ("test_required", "test_optional", "test_blind"):
        return "POLICY_UNKNOWN"
    if profile.get("sat_total") is None and profile.get("act_composite") is None:
        return "NO_SCORES_PROVIDED"
    return "SCORES_PROVIDED_NO_ODDS_ESTIMATE"
