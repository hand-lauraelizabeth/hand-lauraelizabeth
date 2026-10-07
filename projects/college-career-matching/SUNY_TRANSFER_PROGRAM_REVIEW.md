# SUNY STEP program review layer

**Status:** review scaffold implemented; CIP assignment intentionally gated.

Institution identity and program identity are separate problems. The current STEP identity baseline resolves the campus labels, but a source program title such as `Business Administration A.S.` is not itself a validated CIP.

`suny_transfer_program_review.py` creates one review row per unique:

`side + UNITID + source program text`

The review queue preserves the agreement IDs that use the wording, parses common degree markers for reviewer convenience, and keeps CIP blank.

## Mapping order

A program/CIP mapping may become accepted only through:

1. source-published CIP;
2. authoritative institution program identifier that resolves to CIP;
3. separately reviewed program-name + award-level crosswalk;
4. otherwise unresolved.

Title similarity alone can create a suggestion for human review later, but it must never auto-populate `reviewed_cip`.

## Review queue fields

- stable review ID
- sending/receiving side
- reviewed institution UNITID
- STEP institution label
- exact STEP program text
- parsed degree marker
- normalized title
- agreement count + supporting agreement IDs
- suggested CIP (blank in the initial scaffold)
- suggestion basis
- review status
- reviewed CIP / authoritative program ID
- review note

## Product gate

Transfer-program evidence should not reach recommendation scoring until the reviewed mapping is specific enough to support the claim being made. Institution identity coverage alone is not program-equivalency coverage.
