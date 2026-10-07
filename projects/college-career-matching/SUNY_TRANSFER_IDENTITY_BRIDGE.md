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


## Reviewed STEP identity registry

The live STEP inventory uses short campus labels that are not safe to fuzzy-match automatically. The version-controlled `suny_step_reviewed_aliases.csv` records reviewed STEP label → current IPEDS identity mappings. Accepted mappings are validated against the active IPEDS snapshot at runtime: the UNITID must exist exactly once in New York and the normalized institutional name must match the registry.

The registry also preserves relationship type. Standard campuses use `campus`; statutory colleges such as Cornell CALS and the NYS College of Ceramics use `subunit_parent`; SUNY Plattsburgh at Queensbury uses `extension_parent`. This lets the product retain the source-specific subunit/site wording without inventing a separate IPEDS institution.

Token/fuzzy matches remain diagnostic only and never populate UNITID.
