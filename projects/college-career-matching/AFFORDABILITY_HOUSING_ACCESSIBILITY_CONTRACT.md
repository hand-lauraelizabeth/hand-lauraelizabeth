# Affordability, Housing, Setting & Accessibility Evidence Contract

**Status:** product/source contract for the zero-friction College + Career Explorer. Public UI work may use synthetic fixtures until governed source layers pass release gates.

## Design rule

Keep these as distinct evidence domains. Do not collapse cost, aid, housing, campus setting, transit, walkability, and disability-support evidence into one opaque "campus fit" or "accessibility" score.

## Affordability

### Consumer-facing fields

- **Cost of attendance:** tuition/required fees + books/supplies + living expenses and other expenses as reported/derived in IPEDS/College Scorecard.
- **Average net price after grants/scholarships:** cost of attendance minus federal, state/local, and institutional grant/scholarship aid. Loans are not subtracted.
- **Average net price by family-income band:** use the published College Scorecard/IPEDS brackets:
  - $0–30,000
  - $30,001–48,000
  - $48,001–75,000
  - $75,001–110,000
  - $110,001+
- Never present an income-band average as a personalized aid estimate.
- Do **not** derive a family-size-specific net price from institution-level public aggregates. Household size may be collected later as planning context only if an authoritative personalized-cost method is added.

### Aid context

Keep source/type visible. Candidate fields should support, where published:

- percent receiving any grant/scholarship aid;
- federal grants / Pell;
- state/local grants and scholarships;
- institutional grants and scholarships;
- Federal Work-Study participation/evidence;
- student loans, separately from grants;
- average award amounts where appropriate.

"School provides" should be reserved for institutional grants/scholarships and institution-funded aid. Federal/state aid should be labeled as recipient/participation context rather than school-funded aid.

## Campus setting

Use NCES locale rather than hand-authored labels.

Store the full locale code and expose both:
- four-category setting: City / Suburban / Town / Rural;
- detailed 12-category subtype when useful (large/midsize/small city or suburb; fringe/distant/remote town or rural).

Unknown locale remains unknown.

## Housing

From IPEDS Institutional Characteristics / Cost:

- institutionally controlled housing available: yes/no;
- reported housing capacity when available;
- whether **all** full-time, first-time degree/certificate-seeking students are required to live in institutionally controlled housing;
- on-campus food/housing charge;
- off-campus-not-with-family allowance;
- off-campus-with-family allowance.

Public filters may therefore support:
- housing available;
- housing available and not universally required (visitor has a housing choice);
- no institutionally controlled housing / commuter-oriented.

Federal source data do **not** reliably describe roommate versus single-room availability. Treat private-room/roommate configuration as optional school-specific enrichment, with source date and unknown state.

## Campus & community accessibility

Accessibility is multidimensional. Expose components separately and permit explicit priorities.

### Disability-support evidence

IPEDS reports whether/what share of undergraduates are formally registered with the institution's disability-services office. This is evidence that disability-services reporting exists; the share registered is **not** a quality score and must never be interpreted as campus physical accessibility.

Candidate fields:
- disability_services_evidence_state;
- disability_services_registered_share_or_band;
- disability_services_context_note when available.

### Public transit access

Derived geospatial evidence may use the Bureau of Transportation Statistics National Transit Map:
- distance to nearest fixed-route/fixed-guideway stop;
- count of stops within configured walk/roll radii;
- number/types of transit modes or routes where supportable;
- source vintage.

Do not equate a nearby stop with accessible transit equipment or an accessible path to that stop.

### Walkable community access

A distinct community-access layer may use the EPA Smart Location Database / National Walkability Index, with its source vintage shown, and/or geospatial proximity to everyday destinations.

Possible user-visible components:
- walkability/location-efficiency evidence;
- grocery/pharmacy/healthcare proximity;
- transit access;
- distance-to-daily-needs bands.

### Mobility-accessibility evidence

OpenStreetMap can provide wheelchair and other physical-accessibility tags for some features. Coverage is incomplete. Use:
- evidence-present / evidence-missing states;
- objective tags where available;
- no inference from missing tags.

Do not convert missing OSM accessibility tags into "not accessible."

## Preference semantics

**Hard filters** can include:
- state;
- NCES setting;
- credential;
- online availability;
- maximum average net price (overall or selected income band);
- housing available;
- housing not universally required;
- specified aid evidence available.

**Soft priorities** can include:
- lower average net price;
- institutional grant prevalence/amount;
- transit access;
- walkable daily needs;
- smaller/larger environment;
- housing choice;
- career-pathway breadth;
- transfer pathway strength.

A composite accessibility or affordability score may be shown only after the visitor explicitly selects the contributing preferences. The browser must not assign hidden default weights.

## Public-language rule

Always distinguish:
- sticker tuition;
- total cost of attendance;
- average net price after grants/scholarships;
- selected-income-band average net price;
- loans;
- school-funded institutional aid;
- outside/federal/state aid.

Unknown evidence stays visible rather than becoming zero, false, or a failed preference.
