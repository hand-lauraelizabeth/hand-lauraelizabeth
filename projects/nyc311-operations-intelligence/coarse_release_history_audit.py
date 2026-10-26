"""Private all-pairs temporal QA for a history of NYC 311 20-cell manifests.

Adjacent-release checks alone can miss a small difference between older
and newer releases. Compare every historical pair, not just neighbors.
This is a diagnostic on supplied private aggregates: it cannot authenticate
source records, link request identities, or authorize publication.
Only issue codes are emitted; never print labels, counts, or source hashes.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

from coarse_20cell_binding_audit import audit as audit_binding
from paired_coarse_temporal_audit import audit as audit_pair

BINDING_BASELINE = {
    "source_provenance_not_authenticated",
    "public_auxiliary_marginals_not_reconciled",
    "temporal_reconstruction_not_reconciled",
    "editorial_group_definitions_not_independently_verified",
    "independent_source_digest_not_supplied",
}
PAIR_BASELINE = {
    "source_identity_cohort_not_reconciled",
    "paired_external_marginals_not_authenticated",
    "temporal_privacy_clearance_pending",
}
HOLDS = {
    "history_source_cohort_not_authenticated",
    "history_external_marginals_not_authenticated",
    "history_privacy_clearance_pending",
}
MAX_SNAPSHOTS = 24


def audit(history):
    """Return codes only; validate definitions and compare ALL snapshot pairs."""
    issues = set(HOLDS)
    if (not isinstance(history, list) or not 2 <= len(history) <= MAX_SNAPSHOTS):
        return sorted(issues | {"invalid_history_length"})
    for item in history:
        if not isinstance(item, dict):
            return sorted(issues | {"invalid_history_manifest"})
        try:
            findings = set(audit_binding(item))
        except (TypeError, ValueError, KeyError, OverflowError):
            return sorted(issues | {"invalid_history_manifest"})
        if findings - BINDING_BASELINE:
            return sorted(issues | {"invalid_history_manifest"})

    first = history[0]
    dates = [dt.date.fromisoformat(item["snapshot_as_of"]) for item in history]
    if any(item["dataset_id"] != first["dataset_id"]
           or item["month"] != first["month"] for item in history[1:]):
        return sorted(issues | {"history_cohort_changed"})
    if any(item["group_labels"] != first["group_labels"]
           or item["agency_to_group"] != first["agency_to_group"]
           for item in history[1:]):
        return sorted(issues | {"history_editorial_definitions_changed"})
    if any(a >= b for a, b in zip(dates, dates[1:])):
        return sorted(issues | {"history_snapshot_order_invalid"})

    for i, before in enumerate(history[:-1]):
        for j in range(i + 1, len(history)):
            try:
                findings = set(audit_pair(before, history[j])) - PAIR_BASELINE
            except (TypeError, ValueError, KeyError, OverflowError):
                return sorted(issues | {"invalid_history_pair"})
            # Every pair is assessed. A nonadjacent small difference may be
            # invisible to checks comparing only consecutive snapshots.
            prefix = "nonadjacent_" if j > i + 1 else "adjacent_"
            issues.update(prefix + code for code in findings)
    return sorted(issues)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_manifest_history", type=Path,
                        help="Private JSON array of 2-24 complete 20-cell manifests")
    args = parser.parse_args()
    try:
        history = json.loads(args.private_manifest_history.read_text(encoding="utf-8"))
        findings = audit(history)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, OverflowError):
        findings = sorted(HOLDS | {"unreadable_or_invalid_history"})
    print(json.dumps({"hold": True, "publication_approved": False,
                      "findings": findings}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
