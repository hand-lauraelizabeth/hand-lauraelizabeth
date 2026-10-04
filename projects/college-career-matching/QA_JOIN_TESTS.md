# College + Career Matching Tool — QA & Join Tests

These are the minimum acceptance criteria for a source snapshot before it can enter recommendation work.

## Universal checks

- **FAIL:** manifest source ID missing or duplicated.
- **FAIL:** release/version metadata missing.
- **FAIL:** raw snapshot hash missing.
- **FAIL:** raw row count is zero.
- **FAIL:** required canonical key columns are absent.
- **WARN:** source schema adds/removes columns until reviewed.
- **WARN:** missingness or suppression changes materially from the prior release.

## College Scorecard

- FAIL on duplicate normalized UNITID.
- FAIL if pagination repeats/skips pages.
- FAIL if a normalized proportion is outside 0–1 before display conversion.
- FAIL if PrivacySuppressed becomes zero.
- WARN when a metric's reference year changes unexpectedly.

## IPEDS

- FAIL on null/duplicate UNITID in the directory table.
- FAIL if release type is not recorded.
- FAIL if a parser uses a dictionary from another year.
- FAIL on invalid CIP6.
- FAIL if completions become negative after normalization.
- FAIL if demographic aggregation double-counts totals.

## CIP ↔ SOC

- FAIL on invalid CIP6 or SOC6.
- FAIL if duplicate identical pairs remain.
- FAIL if processing forces one SOC per CIP or one CIP per SOC.
- INFO: report occupations per CIP and CIPs per occupation.

## O*NET

- FAIL if occupation identity is not unique at ONET_SOC_CODE + version.
- FAIL if element/scale identifiers are dropped.
- FAIL if a scale value exists without its scale ID.
- WARN if an occupation or element disappears in a new release.

## BLS Employment Projections

- FAIL if summary rows enter detailed joins by default.
- FAIL if projection years are missing.
- FAIL if employment/opening units are changed without a named transformation.
- WARN on material SOC coverage change.

## BLS OEWS

- FAIL if AREA + OCC_CODE grain is lost.
- FAIL if suppression markers become zero.
- FAIL if P25 > median or median > P75 where all three are reported.
- FAIL if one AREA code maps to conflicting AREA titles within a release.

## Cross-source join checks

### Scorecard ↔ IPEDS

- UNITID unique on each side.
- Comparable-universe match rate defaults to at least 95%.
- Unmatched rows are categorized rather than silently discarded.
- No fuzzy-name repair of a valid conflicting UNITID.

### IPEDS programs ↔ CIP/SOC

- Preserve many-to-many cardinality.
- Every matched pathway carries crosswalk version.
- Unmatched CIP means no direct crosswalk pathway, not a zero-quality program.

### O*NET ↔ Employment Projections

- Use explicit SOC normalization.
- Report detailed-occupation match rate.
- Summary BLS codes do not count as detailed matches.

### O*NET ↔ OEWS

- Preserve geography.
- Report coverage separately by national/state/metro/nonmetro grain.
- Missing wages stay missing before any later scoring.

## Coverage regression gates

Live coverage reports can be run with `--enforce-coverage-baseline`. The configured floors in `coverage_baselines.json` are deliberately conservative: they are intended to catch silent source truncation, parser regressions, lost join coverage, or accidental filtering—not to freeze federal datasets at exact historical counts.

- **Institution gate:** protects the IPEDS institution universe, DAPIP identifier coverage, current institutional-accreditation coverage, and public community-college pathway representation.
- **Program gate:** protects completions row volume, summary-CIP detection, institution + CIP6 + award-level coverage, distinct CIP6 coverage, and direct CIP↔SOC mapping rates.
- **Career gate:** protects O*NET occupation/base-SOC coverage, BLS detailed-projection coverage, and national OEWS detailed-occupation coverage.
- A source-version change that legitimately moves below a floor requires explicit investigation and a reviewed baseline update; the gate must not be weakened automatically to make CI pass.
- Reports retain the actual value, configured minimum, and pass/fail result for every guarded metric.

## Recommendation gate

Recommendation scoring remains disabled until:

- every production-core source has a passing snapshot;
- normalized tables exist;
- key uniqueness checks pass;
- CIP↔SOC cardinality checks pass;
- institution, program, and occupation join/coverage reports exist;
- all enabled coverage-regression gates pass for the source snapshot being promoted;
- source versions/reference years reach the explanation layer;
- private institutional sources are absent from production configuration.

## Interpretation safeguards

- Do not rank primarily by selectivity or commercial prestige.
- Do not present CIP↔SOC as proof of graduate outcomes.
- Do not equate posting volume with the whole labor market.
- Do not treat high wages as universally preferable without user context.
- Do not penalize entities merely because a federal source suppresses data.
- Keep user weights adjustable and expose recommendation drivers.
