# Product Snapshot Release Evidence & Activation-Review Contract

**Status:** evidence profiling and fail-closed activation-review bundling implemented. Production activation remains manual and separate.

## Purpose

The public explorer currently uses synthetic fixtures. Replacing them with an authoritative product snapshot requires a reproducible evidence trail rather than a direct file swap.

## Release evidence profile

`product_snapshot_release_profile.py` reports observed snapshot facts:

- candidate and institution counts;
- completeness of core identity/program fields;
- every available `coverage__*` rate;
- source vintages and input hashes from the manifest;
- output-hash agreement;
- interface-option build counts.

The profile is **observation only**. Current counts or coverage never become thresholds automatically.

## Policy and gate

Thresholds remain explicit inputs to `product_snapshot_release_gate.py`. The example policy intentionally contains null thresholds until evidence supports a human-authored policy.

## Activation-review bundle

`product_snapshot_activation_bundle.py` can run only after the release gate returns `ELIGIBLE_FOR_ACTIVATION_REVIEW`. It pins:

- exact snapshot SHA-256;
- `data_version`;
- `model_version`;
- candidate and institution counts;
- interface-option counts;
- release-check PASS/WARN totals.

The bundle always emits `production_authorized: false` and `required_next_action: human_activation_review`.

## Public explorer boundary

The portfolio explorer must remain in synthetic fixture mode until a separate, explicit activation decision approves a specific activation-review bundle. A passed release gate or bundle is insufficient by itself.
