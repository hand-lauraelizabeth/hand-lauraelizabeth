# Housing filter acceptance contract (synthetic-only)

Status: proposed implementation specification; not independently validated in browser. No real institution data is approved for publication.

## Distinct fields

- `housing_type`: ON_CAMPUS, AFFILIATED_OFF_CAMPUS, PARTNER_CAMPUS, REFERRAL_ONLY, DOCUMENTED_NONE, UNKNOWN.
- `availability`: CONFIRMED_FOR_TERM, WAITLIST, UNAVAILABLE_FOR_TERM, UNKNOWN. An institution's housing type does not establish current vacancy.
- `term`: explicit term identifier or null. An availability assertion with no matching term is UNKNOWN for the requested term.
- `evidence`: official URL, institution UNITID, retrieval date, claim text, reviewer, and verification status.
- `publication_status`: default DO_NOT_PUBLISH; independent approval must be separately recorded.

## Matching semantics

When the user selects 'requires on-campus housing', include only ON_CAMPUS with separately verified evidence. AFFILIATED_OFF_CAMPUS, PARTNER_CAMPUS, and REFERRAL_ONLY are not equivalent. UNKNOWN is not NO. A filter for 'confirmed space this term' must additionally require CONFIRMED_FOR_TERM for the selected term; otherwise return UNKNOWN or exclude under a strict filter with an explanatory count.

Never infer a housing option from a referral, a disability-services page, or an absence of negative evidence. Do not expose raw institutional queue rows or citations to the public interface before owner approval.

## Synthetic QA acceptance cases

1. ON_CAMPUS + CONFIRMED_FOR_TERM + matching term => eligible for both filters.
2. ON_CAMPUS + UNKNOWN availability => housing-type filter only; not confirmed vacancy.
3. AFFILIATED_OFF_CAMPUS => excluded from on-campus-only filter.
4. REFERRAL_ONLY => excluded from on-campus-only filter.
5. DOCUMENTED_NONE => excluded, but displayed distinctly from UNKNOWN.
6. UNKNOWN housing => excluded from strict yes-only results, counted as unknown.
7. Stale or mismatched term => vacancy UNKNOWN, not confirmed.
8. DO_NOT_PUBLISH => never enters a public dataset regardless of filter outcome.
9. Missing or invalid source provenance => cannot be labeled independently verified.
10. Missing owner approval => deny external publication even with a verified source.

## Next step

Map the 19 observed raw housing status strings to this controlled vocabulary with source-by-source review. Implement and run synthetic UI browser tests for the ten cases; verify publication gate separately before any live institutional data integration.
