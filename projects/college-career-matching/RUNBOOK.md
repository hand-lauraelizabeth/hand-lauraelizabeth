# Reproduce the College + Career Data Build

The College + Career Matching Tool keeps source retrieval separate from recommendation scoring. The ingestion prototype can be run with the Python standard library; no project-specific package install is required.

## List configured sources

```bash
python scripts/college_career_ingest.py --list-sources
```

## Inspect a source without downloading it

```bash
python scripts/college_career_ingest.py --source cip_soc_crosswalk_2020_2018 --dry-run
```

A dry run resolves the production source URL(s) and confirms that the source exists in the manifest.

## Ingest a public download source

```bash
python scripts/college_career_ingest.py \
  --source cip_soc_crosswalk_2020_2018 \
  --output-dir projects/college-career-matching/data/snapshots
```

The same command pattern works for:

- `ipeds_directory_2025`
- `ipeds_completions_2025`
- `onet_31_0`
- `bls_employment_projections_2025_2035`
- `bls_oews_may_2025`
- `dapip_accreditation`

Each run creates a timestamped snapshot containing:

- the raw source file(s);
- `source_snapshot.json` with version, URL, timestamp, and SHA-256;
- normalized CSV output where the adapter is implemented;
- `reports/qa.json`.

Generated data directories are ignored by Git so the repository contains reproducible code and source definitions rather than duplicated federal datasets.

## College Scorecard

College Scorecard institution enrichment no longer requires an API key. The source manifest points to the official featured June 10, 2026 institution-level bulk ZIP.

Try the direct official download path first:

```bash
python scripts/college_career_ingest.py \
  --source college_scorecard \
  --output-dir projects/college-career-matching/data/snapshots
```

As observed on October 4, 2026, the official Scorecard bulk CDN returns HTTP 403 to GitHub-hosted Actions runners even with browser-compatible headers. This is a transport limitation rather than a parser/QA failure. If the file is downloaded through a normal browser or another permitted route, ingest that same official ZIP directly:

```bash
python scripts/college_career_ingest.py \
  --source college_scorecard \
  --source-file /path/to/Most-Recent-Cohorts-Institution_06102026.zip \
  --output-dir projects/college-career-matching/data/snapshots
```

Both paths retain the official source URL/release in provenance, copy the raw ZIP into the timestamped snapshot, compute a source hash, normalize the same logical Scorecard fields, preserve privacy-suppressed values as missing, and run the same QA checks. The optional `[live-scorecard-smoke]` workflow step is therefore a non-blocking CDN transport probe; parser correctness is enforced by the local bulk-ZIP fixture in the regular test suite.

## Validate the source contract

```bash
python scripts/validate_college_career_sources.py
python scripts/test_college_career_ingestion.py
```

These checks run in GitHub Actions on relevant changes.

## Live source smoke test

The main validation workflow includes an opt-in live CIP↔SOC ingestion test. A commit whose message contains:

`[live-source-smoke]`

runs the real federal-source download and normalization path in GitHub Actions. Ordinary portfolio commits do not depend on external source availability.

## Current boundary

The pipeline uses public federal sources for production. Historical Lightcast, Handshake, Symplicity, employer-contact, LinkedIn profile, and student-level records informed schema design and validation strategy but are not configured as public production inputs.

The live smoke test is expected to produce at least one normalized row; a zero-row parse is treated as a failure rather than a successful download.\n\nRecommendation scoring remains disabled until live source snapshots and cross-source join QA pass.


## IPEDS live smoke path

A commit message containing `[live-ipeds-smoke]` runs the current HD2025 institution-directory and C2025_A completions adapters against the official NCES complete-data-file endpoints.

Each successful HD2025 run also writes `reports/institution_coverage.json` with state/territory, control, sector, level, degree-granting, and public-sector coverage markers. The report deliberately does not treat `SECTOR=4` as the entire community-college universe.


## O*NET live smoke path

A commit message containing `[live-onet-smoke]` downloads the configured O*NET 31.0 occupation/content tables and verifies that the occupation universe and related content normalize successfully.

A successful O*NET run also writes `reports/career_coverage.json`, including the total detailed occupation universe and occupation coverage by each O*NET content table.


## BLS live smoke path

A commit message containing `[live-bls-smoke]` downloads O*NET 31.0, BLS Employment Projections 2025–2035, and May 2025 OEWS, then runs:

```bash
python scripts/college_career_ingest.py --build-career-joins \
  --output-dir projects/college-career-matching/data/snapshots
```

The resulting `career_source_coverage.json` reports O*NET base-SOC coverage against detailed BLS projection rows and OEWS detailed occupations by source `AREA_TYPE`. BLS summary/aggregate occupation rows remain available in normalized source tables but do not enter the default detailed join.

## Accreditation + community-college coverage path

DAPIP uses the current CSV bulk export exposed by the official U.S. Department of Education Download Files interface. The adapter records the raw ZIP and requires all three current members: `InstitutionCampus.csv`, `AccreditationRecords.csv`, and `AccreditationActions.csv`.

A commit message containing `[live-dapip-smoke]` downloads current HD2025 and DAPIP snapshots, then runs:

```bash
python scripts/college_career_ingest.py --build-institution-coverage \
  --output-dir projects/college-career-matching/data/snapshots
```

The output keeps accreditation separate from institution identity and writes an explicit many-to-many `dapip_ipeds_bridge.csv` by exploding DAPIP's `IpedsUnitIds` field without discarding the raw multi-ID value. The community-college pathway proxy includes public `SECTOR=4`, public `INSTCAT=4`, and public 2021 Carnegie Basic associate/baccalaureate-associate categories (codes 1–14 and 23). The flag is a discovery/coverage proxy, not a legal, state-system, or mission designation.


## Program coverage path

A commit message containing \`[live-program-smoke]\` downloads the current HD2025 institution directory, C2025_A completions data, and the official CIP 2020 ↔ SOC 2018 crosswalk, then runs:

\`\`\`bash
python scripts/college_career_ingest.py --build-program-coverage \
  --output-dir projects/college-career-matching/data/snapshots
\`\`\`

The report writes \`program_coverage.json\` plus \`program_coverage_flags.csv\` at the institution + CIP6 + award-level grain. The normalized completions source retains \`MAJORNUM\`; default program coverage uses first-major (\`MAJORNUM=1\`) rows and reports second-major rows separately so the same program is not double-counted. It reports institution coverage, distinct observed CIP6 codes, award-level counts, direct CIP↔SOC mapping coverage, and explicit unmapped CIPs.

IPEDS summary/total CIP rows are excluded from specific-program coverage. The normalizer treats a source serialization of \`99\` as CIP \`99.0000\` rather than \`00.0099\`. A missing CIP↔SOC mapping remains a coverage gap rather than a quality penalty or a reason to remove the program.


## Integrated model-ready path

A commit message containing `[live-model-ready-smoke]` downloads the current unauthenticated production sources—HD2025, C2025_A, CIP 2020 ↔ SOC 2018, O*NET 31.0, BLS 2025–2035 projections, May 2025 national OEWS, and the live DAPIP bulk export—then runs:

```bash
python scripts/college_career_ingest.py --build-model-ready \
  --output-dir projects/college-career-matching/data/snapshots
```

The build writes:

- `institution_identity_resolution.csv` — exact-identifier review clusters while preserving every UNITID as a distinct recommendation entity;
- `institution_model.csv` — institution context, accreditation/community-college flags, provenance, and optional Scorecard enrichment when a Scorecard snapshot exists;
- `program_model.csv` — first-major (`MAJORNUM=1`) institution + CIP6 + award-level rows, with second-major presence retained as context;
- `program_occupation_pathway.csv` — streamed many-to-many CIP↔SOC↔O*NET pathways enriched with BLS projections and national OEWS data;
- `model_ready_qa.json` — identity-review, row-count, enrichment-coverage, regression-gate, and scoring-gate checks.
- `model_ready_manifest.json` — exact source snapshot lineage (release, retrieval time, SHA-256/reference period where available), table grains, identity policy, and pathway policy.

Shared DAPIP or exact OPEID relationships are review signals, not automatic merges. Program rows with no direct CIP↔SOC mapping remain present with an explicit coverage-gap pathway row. The pathway file is streamed during construction so the full federal universe does not need to be held in memory.


## GitHub-hosted runner access note for BLS

The BLS adapters use the official 2025–2035 Employment Projections and May 2025 OEWS bulk sources. In October 2026 validation, GitHub-hosted Actions runners received HTTP 403 responses from both `www.bls.gov` bulk-file URLs and BLS's `download.bls.gov` programmatic-download host, while the same releases remained publicly documented on BLS web pages. This is treated as a source/network access limitation, not as a successful live-data test and not as a parser failure.

The `[live-bls-smoke]` path is therefore intended for an environment from which BLS permits bulk downloads (for example a local or self-hosted runner). Unit tests, source-contract validation, release metadata, and join logic remain active in ordinary CI; recommendation scoring stays gated until a real BLS snapshot and O*NET↔BLS coverage report have been produced.

## Product snapshot release-readiness path

Before replacing the public explorer's synthetic fixture with an authoritative product snapshot, generate an observation-only profile:

```bash
python projects/college-career-matching/product_snapshot_release_profile.py \\
  --snapshot /path/to/product_snapshot.csv \\
  --manifest /path/to/product_snapshot_manifest.json \\
  --output /path/to/release_profile.json
```

The profile reports counts, completeness, coverage, source vintages, hashes, and interface-option buildability but does not invent release thresholds.

After an explicit policy is configured and `product_snapshot_release_gate.py` returns `ELIGIBLE_FOR_ACTIVATION_REVIEW`, build the hash-pinned review bundle:

```bash
python projects/college-career-matching/product_snapshot_activation_bundle.py \\
  --snapshot /path/to/product_snapshot.csv \\
  --manifest /path/to/product_snapshot_manifest.json \\
  --release-decision /path/to/release_decision.json \\
  --model-version MODEL_VERSION \\
  --output /path/to/activation_review_bundle.json
```

That bundle still sets `production_authorized: false`; the public explorer remains in fixture mode until a separate human activation decision is recorded.

## Browser runtime and deployment switch

The public explorer is fixture-first. Generate a runtime config with no activation record to make that state explicit:

```bash
python projects/college-career-matching/service_runtime_config.py \\
  --fixture-url ./prototype/contract-fixtures.json \\
  --output /path/to/service-runtime.json
```

That output is always `mode: fixture` and `production_authorized: false`.

A production runtime can be emitted only from a previously validated production activation record and an explicit HTTPS service base URL:

```bash
python projects/college-career-matching/service_runtime_config.py \\
  --activation-record /path/to/service_activation_record.json \\
  --service-base-url https://service.example.org \\
  --output /path/to/service-runtime.json
```

The runtime pins the authorized `data_version`, `model_version`, snapshot SHA-256, and activation-bundle SHA-256. The browser then checks `/metadata` against those identities before accepting production mode.

To inject a governed runtime into a static explorer build:

```bash
python projects/college-career-matching/public_explorer_deployment.py \\
  --source projects/college-career-matching/public-explorer.html \\
  --runtime-config /path/to/service-runtime.json \\
  --output /path/to/deployed-explorer.html
```

This deployment step does not create or infer approval. Without a valid production activation record, the generated runtime remains fixture mode.
