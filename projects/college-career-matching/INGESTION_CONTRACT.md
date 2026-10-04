# College + Career Matching Tool — Ingestion Contract

This contract defines how public source data enter the matcher. Recommendation scoring stays downstream of source retrieval, normalization, QA, and join validation.

## Pipeline layers

Every production source moves through four explicit layers:

1. **Raw snapshot** — unchanged source response or downloaded file.
2. **Staging** — source-native columns with parsing/type cleanup only.
3. **Normalized** — canonical keys, units, null states, categories, and source metadata.
4. **Model-ready** — joined analytical tables used by later fit and explanation logic.

Raw snapshots are immutable. A new retrieval or source release creates a new snapshot rather than overwriting the prior one.

## Snapshot metadata

| Field | Requirement |
| --- | --- |
| source_id | Must match source_manifest.json |
| retrieved_at | UTC ISO-8601 timestamp |
| source_release | Human-readable release/version |
| source_url | Exact official source used |
| raw_filename | Original or deterministic filename |
| sha256 | Hash of raw bytes |
| release_type | Provisional/final/versioned where applicable |
| reference_period | Year/month/projection window represented |
| parser_version | Git commit or parser version |
| row_count_raw | Count after parsing, before filtering |

## Canonical keys

### Institution — UNITID

- College Scorecard id maps to UNITID.
- Never use institution name as the primary join when UNITID exists.
- UNITID must be unique in each normalized institution identity table.

### Program — UNITID + CIP6 + AWLEVEL

- Normalize CIP to a documented six-digit representation.
- Retain the original source code alongside the normalized value.
- Keep award level separate; do not silently collapse certificate, associate, bachelor, master, and doctoral rows.

### Occupation — SOC6 and ONET_SOC_CODE

- Keep ONET_SOC_CODE as the detailed O*NET identifier.
- Derive base SOC6 through an explicit, versioned rule or crosswalk.
- Do not let BLS summary occupation rows masquerade as detailed occupations.

### Geography — AREA

- Preserve OEWS national, state, metropolitan, and nonmetropolitan grains.
- Do not collapse geographic rows during ingestion.

## Null, suppression, and zero

Zero, null, suppressed, not applicable, and not collected are distinct states. PrivacySuppressed values, BLS suppression markers, blanks, and source sentinel codes must never be converted silently to zero.

## Source-specific contracts

### College Scorecard

- API: https://api.data.gov/ed/collegescorecard/v1/schools.json
- API key comes from the COLLEGE_SCORECARD_API_KEY environment variable; never commit a key.
- Use an explicit fields allow-list.
- Follow pagination to completion.
- Persist each metric's reporting/reference year.
- Preserve PrivacySuppressed as unavailable.
- Do not assume all latest metrics describe the same year.

### IPEDS

Current MVP files:

- HD2025 — institution directory/identity.
- C2025_A — 2024-25 awards/degrees by 6-digit CIP and award level.

Rules:

- label snapshots provisional or final;
- parse each file with the matching year's dictionary;
- a final release creates a new snapshot rather than overwriting the provisional one;
- aggregate demographic dimensions only through explicit transformations with reconciliation checks.

### CIP ↔ SOC

Use the official NCES/BLS CIP 2020 ↔ SOC 2018 crosswalk.

- Preserve every valid CIP6-SOC6 relationship.
- Remove only exact duplicate pairs.
- Do not force a one-occupation-per-major model.
- Do not describe the crosswalk as observed graduate outcomes.

### O*NET 31.0

Use the pinned 31.0 CSV release. Minimum normalized tables: occupation, skills, knowledge, abilities, interests, work activities, work context, education/training/experience, related occupations, and technology skills.

Retain O*NET element IDs and scale IDs; importance and level scales remain distinct during ingestion.

### BLS Employment Projections

Use 2025–2035 Table 1.2.

- line-item occupations are the default detailed table;
- summary rows remain separate;
- preserve source units before any normalization;
- keep education, experience, and on-the-job-training fields categorical;
- carry projection base/end years on every row.

### BLS OEWS

Use the May 2025 all-data release.

- preserve AREA, AREA_TITLE, and OCC_CODE;
- retain suppression state;
- preserve geographic grain;
- validate wage percentiles where present;
- keep current wages distinct from future outlook.

## First normalized tables

| Table | Natural key | Purpose |
| --- | --- | --- |
| institution | UNITID | School identity and stable descriptors |
| program_completion | UNITID + CIP6 + AWLEVEL + reference_year | Program availability/scale |
| cip_soc_bridge | CIP6 + SOC6 + crosswalk_version | Education-to-occupation possibilities |
| occupation | ONET_SOC_CODE + onet_version | Occupation identity/content |
| occupation_skill | ONET_SOC_CODE + element_id + scale_id + onet_version | Skill/knowledge/ability dimensions |
| occupation_outlook | SOC6 + projection_cycle | Growth/openings/preparation |
| occupation_wage | AREA + OCC_CODE + reference_period | Current geographic employment/wages |
| source_snapshot | source_id + retrieved_at + sha256 | Reproducibility and source lineage |

## Join contracts

**Scorecard ↔ IPEDS:** join UNITID; one-to-one or unmatched; no fuzzy name override of a valid conflicting identifier.

**IPEDS program ↔ CIP/SOC:** join normalized CIP6; expected many-to-many; never select one occupation merely to force uniqueness.

**O*NET ↔ BLS projections:** explicit O*NET-SOC to SOC6 mapping; summary BLS rows excluded from detailed joins.

**O*NET ↔ OEWS:** join SOC6/OCC_CODE while preserving AREA; one occupation may have many geographic wage rows.

## Refresh sequence

1. Discover the new official release.
2. Record release/version and source URL.
3. Save an immutable raw snapshot.
4. Compute SHA-256.
5. Validate source schema.
6. Normalize with the matching source dictionary/version.
7. Run key, type, range, and suppression checks.
8. Run cross-source join tests.
9. Compare counts, missingness, and join rates with the prior snapshot.
10. Promote only after QA passes.

## Production exclusion

Private Handshake/Symplicity/student/advising records, private employer contacts, profile-level LinkedIn pulls, and historical licensed Lightcast extracts without current reuse rights are not public production sources. They informed the architecture; they do not feed the public matcher.
