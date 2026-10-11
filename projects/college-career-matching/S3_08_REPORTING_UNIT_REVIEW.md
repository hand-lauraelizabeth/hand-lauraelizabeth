# S3-08 — Reporting-unit identity and Pacifica city-label audit

**Verified on (UTC):** 2026-10-11T00:25:15.943529+00:00

**Status:** eight extended identifiers and one changed-city record audited against SHA-pinned official 2024 and 2025 NCES IPEDS directories, the 6,243-school national source and official Pacifica institutional pages. No parent/branch relationship or geographic campus point is approved.

## Important identifier integrity distinction

[NCES IPEDS guidance](https://nces.ed.gov/ipeds/use-the-data/institutional-groupings-in-ipeds) distinguishes **six-digit IPEDS UNITID** from an **eight-digit federal OPE ID** that has a two-digit branch or additional-location suffix. The same NCES source warns that neither ID has a simple one-to-one relationship with a physical campus. The eight IDs found in the national Scorecard-derived file are eight digits, absent from 2024/2025 IPEDS UNITIDs, but their six-digit prefixes are valid separate IPEDS UNITIDs. **This is a candidate numeric relationship only, not evidence of parentage or a campus identity.**

### Eight extended identifiers (2026 Scorecard snapshot labels)

| Display ID (not verified IPEDS UNITID) | Source-reported school | City / state | Six-digit prefix | NCES 2025 prefix institution |
|---|---|---|---|---|
| 13508111 | Keiser University-Port St Lucie | Port St Lucie, FL | 135081 | Keiser University-Ft Lauderdale |
| 13508113 | Keiser University-Ft Myers | Ft Myers, FL | 135081 | Keiser University-Ft Lauderdale |
| 15098715 | Ivy Tech Community College-Marion | Marion, IN | 150987 | Ivy Tech Community College |
| 17706523 | Columbia College - Fort Stewart | Ft. Stewart, GA | 177065 | Columbia College |
| 24297202 | NUC University - Rio Grande | Rio Grande, PR | 242972 | NUC University |
| 24297205 | NUC University - Mayaguez | Mayaguez, PR | 242972 | NUC University |
| 24297213 | NUC University - IBC Technical Division - Mayaguez | Mayaguez, PR | 242972 | NUC University |
| 24297216 | NUC University - IBC Technical Division - Manati | Manati, PR | 242972 | NUC University |

**Identity decisions:** all eight **HOLD — reporting unit relation unverified**. The six-digit prefix is an investigation lead only; no inheritance of the prefix school address/coordinates, OPEID eligibility or accreditation is allowed.

**National identifier audit:** 6-digit: 5787, 8-digit: 456. 456 national search keys are not six digits. They must not be described as verified IPEDS UNITIDs until provenance is corrected.

## One changed city — Pacifica Graduate Institute, UNITID 115746

- Official HD2024 city: **Carpinteria**.
- Official HD2025 city: **Santa Barbara CA**.
- June 2026 Scorecard-derived city: **Santa Barbara CA**.
- [Pacifica's current visitor page](https://www.pacifica.edu/visitors/) lists **Lambert campus, 249 Lambert Road, Carpinteria**, and **Ladera campus, 801 Ladera Lane, Santa Barbara**.
- [Pacifica's dated campus transition notice](https://www.pacifica.edu/pacificas-campus-transition/) places its transition into winter 2027, so the changed administrative city label does not show a single current instructional campus.
- [California Bureau for Private Postsecondary Education](https://search-bppe.dca.ca.gov/institutionDetail?schoolCode=77183565) separately lists mailing and physical addresses, but these address roles must not be conflated.

**Decision: HOLD — multi-campus city-label change**. The Scorecard and IPEDS labels do not license choosing one point, using a city internal point as the campus entrance, or showing travel time.

## Evidence and remaining release gates

- Official downloaded NCES HD2024 ZIP SHA-256: `d98425c123d7c0e872aec6e83960dfb501884818bf17385c340790f3d1f28345`.
- Official downloaded NCES HD2025 ZIP SHA-256: `aadad9277a2255c85813b6d206475ddbf8a7330d79cc0236c2ecae685b00f1bf`.
- 6,243-row Scorecard-based JSON SHA-256: `478f9e05da1fecd0154fcb28acd0dbdae57ad4c8f22af009f82e311c3febe3bd`.
- All audited institution identities retain null for any proposed campus coordinate or geographic release match; the S3-05 three-entry research-only registry remains unchanged.
- Full detailed status and source page hashes are in [machine-readable aggregate evidence](./research_aggregate/s3_08_reporting_unit_audit.json); a nine-case review ledger is separately retained as a CI artifact.
- Further work should audit *all* non-six-digit keys for semantic mislabeling and create a verified institutional identifier taxonomy before new distance UI.
- No WordPress edits, public data replacement, publication or distance feature.
