# SUNY transfer identity bridge

This stage connects normalized SUNY STEP transfer agreements to the conservative SUNY→IPEDS identity layer.

## Rule

Only identity rows already marked `accepted` may populate a UNITID. Review, unresolved, subunit, or group evidence remains unresolved in the agreement layer. The bridge does not perform fuzzy matching itself.

## Outputs

- enriched agreement rows with sending/receiving UNITID where accepted evidence exists;
- side-specific identity status and match method;
- QA JSON with sending, receiving, both-sides, and unresolved coverage.

Coverage is descriptive evidence availability, **not** a transfer quality or fit score.

## Next live-data step

Run the agreement adapter and institution-identity resolver against an authoritative current SUNY STEP snapshot plus the current IPEDS directory, then version the observed coverage baseline only after manual review of unresolved/review rows.
