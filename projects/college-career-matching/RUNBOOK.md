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

College Scorecard requires an API key from api.data.gov.

Set the key in the environment rather than adding it to a file committed to the repository:

```bash
export COLLEGE_SCORECARD_API_KEY="..."
python scripts/college_career_ingest.py \
  --source college_scorecard \
  --output-dir projects/college-career-matching/data/snapshots
```

The prototype uses an explicit field allow-list and paginates until the API-reported total has been retrieved.

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

The output keeps accreditation separate from institution identity and writes an explainable community-college pathway proxy. The proxy includes public `SECTOR=4` institutions plus public `INSTCAT=4` institutions, so associate-focused institutions that sit in a four-year sector because they offer bachelor's degrees are not silently dropped. The flag is a discovery/coverage proxy, not a legal or mission designation.
