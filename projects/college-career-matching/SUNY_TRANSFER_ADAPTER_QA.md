# SUNY Transfer Agreement Adapter — QA & Coverage Contract

**Implemented:** 2026-10-04  
**Adapter:** `suny_transfer_agreement_adapter.py`  
**Authoritative source:** SUNY STEP Transfer Agreements public page  
**Production baseline status:** pending execution against a saved authoritative CSV snapshot

## Source-shape finding

The current public SUNY STEP Transfer Agreements page exposes a four-column reviewer-facing table:

- `4 Year Partner Campus`
- `Partner Campus`
- `Type Description`
- `Major or Program`

The current page includes General Articulation, Major Specific, Dual Admission, and Dual Enrollment relationships. Some rows describe systemwide or broad relationships (for example, a four-year institution paired with all SUNY community colleges), while others describe specific program-to-program pathways.

This differs from an older/indexed STEP presentation that exposed source IDs such as `R283` and separate initial/partner/program/destination fields. The adapter therefore treats the **current public table as the current source contract** and creates deterministic source-scoped IDs when a stable current source ID is not present. Historical/indexed IDs must not be silently attached to current rows unless an authoritative crosswalk establishes equivalence.

## Directionality rule

For the current table:

- `Partner Campus` → `sending_institution_source_id`
- `4 Year Partner Campus` → `receiving_institution_source_id`

This is a modeling interpretation of the table's explicit four-year/partner structure. It must be revalidated if SUNY changes the source schema. Rows whose wording represents a systemwide relationship remain source records; expansion to individual campuses belongs in a separate reviewed transformation.

## Program-text rule

The current table provides one combined `Major or Program` field. The adapter preserves that text verbatim in `source_program_text` and **does not fabricate** separate sending and receiving program names.

A later parsing/crosswalk stage may split program relationships only when the source text or another authoritative source supports the split. Program-to-CIP mapping remains separately reviewable.

## Agreement-type normalization

| Current source text | Canonical value |
| --- | --- |
| Dual Admission | `dual_admission` |
| Dual Enrollment | `dual_enrollment` |
| Major Specific | `major_specific` |
| General Articulation | `articulation` |
| Other/unrecognized | `other` |

The raw value is always retained in `agreement_type_raw`.

## Adapter QA gates

The adapter fails its QA status if any of these are false:

1. at least one record is present;
2. deterministic IDs are unique;
3. every record has a sending institution label;
4. every record has a receiving institution label;
5. every record retains the authoritative source URL;
6. the adapter itself has not inferred UNITIDs;
7. source program text is retained.

The adapter also reports, but does not yet gate on:

- record count;
- duplicate-ID count;
- distinct sending institutions;
- distinct receiving institutions;
- normalized agreement-type counts.

## Identity coverage baseline — next stage

After the first authoritative snapshot is saved and normalized, run the existing institution-identity architecture against both sides independently and report:

- sending labels total/distinct;
- receiving labels total/distinct;
- exact authoritative-ID matches where available;
- reviewed UNITID matches;
- unresolved labels;
- ambiguous labels;
- sending UNITID match rate;
- receiving UNITID match rate.

Do not remove a transfer agreement because either UNITID is unresolved.

## Program/CIP coverage baseline — later stage

Report separately:

- rows with program-specific evidence;
- rows with parseable source/destination program evidence;
- reviewed sending-program CIP matches;
- reviewed receiving-program CIP matches;
- unresolved program labels;
- broad/general agreements where CIP mapping is not applicable.

A low CIP match rate must not be treated as a failed transfer-source ingestion if the source itself is a general agreement.

## Regression floors

The first successfully ingested authoritative snapshot becomes the baseline. Subsequent builds should fail or require explicit review for unexplained large drops in:

- total agreements;
- distinct sending institutions;
- distinct receiving institutions;
- each major agreement-type family;
- reviewed institution identity match rates.

Because SUNY may revise the public inventory, regression floors should allow documented source changes rather than freezing a permanent count.

## Semantic safeguards

- `Major Specific` means the agreement is program-specific; it does not by itself prove every course applies to the major.
- `General Articulation` is not automatically a guaranteed-admission relationship.
- `Dual Admission` may support an admission guarantee only after the source conditions are captured; the type label alone is insufficient for a user-facing guarantee statement.
- `Dual Enrollment` is not equivalent to transfer articulation.
- No current-table row is assigned a CIP, UNITID, credit count, minimum grade, or degree-applicability claim by this adapter alone.

## Execution dependency

The adapter is implemented and source semantics are documented, but the repository does not yet contain a saved authoritative SUNY STEP CSV snapshot. Therefore **no production record count, match rate, or regression baseline is claimed yet**.

The next step is to capture/export the current authoritative table, execute the adapter, save the normalized output/QA report or reproducible snapshot manifest, and then run the institution identity crosswalk.