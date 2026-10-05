# Campus Context Preference Contract

**Status:** governed request semantics and candidate-level normalization implemented; production reference snapshots and release authorization remain gated.

## Purpose

Represent campus/community preferences as explicit, independently weighted user priorities instead of hiding them inside one generic campus-fit or accessibility score.

## Preference dimensions

The request contract supports four separate soft-priority dimensions:

- `transit_access_fit` — convenience of public-transit access near the school;
- `walkability_fit` — walkability/location-efficiency context for everyday needs;
- `housing_context_fit` — the user's preference for housing availability/choice context;
- `accessibility_evidence_fit` — availability of documented disability-services evidence.

These dimensions are distinct from hard constraints. A visitor may require a condition, prioritize it softly, do both, or skip it.

## Explicit weighting only

Each dimension enters a request only when the visitor explicitly supplies an importance value. No default importance is inferred, and skipped priorities receive no hidden weight.

Keeping these dimensions separate prevents a transit preference from silently increasing the importance of walkability, housing, or disability-services documentation.

## Evidence semantics

### Transit

Transit proximity is not proof that vehicles, stations, sidewalks, curb cuts, or the path between campus and transit are accessible. Any later normalized transit score must identify its distance/radius policy and source vintage.

### Walkability

EPA walkability/location-efficiency evidence must retain its dataset vintage. It is not a physical-accessibility score and must not be presented as current-year ground truth when the source is older.

### Housing

Housing availability and a universal full-time first-time residency requirement are separate source fields. A housing-choice preference does not establish roommate/private-room availability.

### Disability-services evidence

This dimension concerns documented evidence availability only. It is not a rating of accommodation quality, responsiveness, legal compliance, or physical campus accessibility.

Missing evidence remains unknown. It must never be converted into a zero-quality score.

## Relationship to recommendation scoring

The request layer preserves the visitor's explicit priorities. Candidate-level normalization is implemented through a versioned campus-context feature registry and a pinned institution-level reference population. Numeric transit/walkability evidence uses empirical midrank percentiles against that reference; housing and disability-services evidence use exact categorical semantics.

The implemented normalization policy follows these rules:

1. name the source field;
2. define direction/operator semantics;
3. provide an explicit reference range or category rule when needed;
4. preserve missing/suppressed/not-published states;
5. report evidence coverage separately from desirability;
6. pass sensitivity and explanation QA before release.

## Browser behavior

The public explorer should consume these governed request definitions rather than maintain a separate hidden weighting system. UI labels may be concise, but they must preserve the distinctions above.
