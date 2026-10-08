# Private matcher evidence-audit hardening

A standalone, locally tested patch exists for institution_evidence_review.py and test_institution_evidence_review.py (13 synthetic unittest cases passing). The patch is not merged or deployed. It adds duplicate UNITID detection, malformed CSV/header checks, explicit approval flag, placeholder source rejection, and cohort-year consistency checks. It does not independently verify institutional sources or approve any record. All 20 institutional records remain DO_NOT_PUBLISH.

Next: apply and review patch, rerun tests and CI, then complete the 17 outstanding official aid-source reviews before NCES locale and Scorecard cohort mapping.
