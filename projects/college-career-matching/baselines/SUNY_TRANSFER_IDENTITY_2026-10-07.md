# SUNY STEP transfer identity baseline — 2026-10-07

**Status:** PASS  
**Source:** SUNY STEP Transfer Agreement Inventory  
**Current snapshot:** 528 records (R283–R876)  
**IPEDS reference:** HD2025 provisional, 5,985 institutions

## Observed identity coverage

The reviewed STEP-label registry resolves all **58 / 58** unique campus labels against the active New York IPEDS reference. At the agreement level, both sending and receiving UNITID are resolved for **528 / 528** records.

This baseline is intentionally narrow. It establishes **institution identity**, not program equivalency or recommendation quality.

The current agreement snapshot contains 483 articulation agreements, 19 dual-admission records, 1 dual-enrollment record, and 25 records classified as other. Destination-program wording is present on 411 records.

## Relationship preservation

Institution-grain UNITIDs do not erase source context:

- Cornell CALS remains a statutory-college / parent-institution relationship.
- NYS College of Ceramics remains a statutory-college / parent-institution relationship.
- SUNY Plattsburgh at Queensbury remains an extension-site / parent-institution relationship.

## Guardrail

No fuzzy or token candidate is auto-accepted. Reviewed registry mappings are revalidated against each active IPEDS snapshot by UNITID, New York state, and normalized institutional name.

Program/CIP mapping remains unresolved. The next gate is a source-preserving program/destination review layer before transfer evidence is allowed to influence product-grain recommendations.

**Live workflow:** https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/37637044456
