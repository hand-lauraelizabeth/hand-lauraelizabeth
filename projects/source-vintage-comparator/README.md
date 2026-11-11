# Source Vintage Comparator — review candidate

**Status:** Review-only prototype; not a live website release. Open [the browser exercise](./index.html) from this branch or download this folder and open `index.html` locally. No server, account, package installation, or external data source is required.

## What the exercise does
Learners compare two records by subject/identifier, evidence date, evidence type, population/credential/definition, and source identifier. The fictional example deliberately contrasts historical completions with a current catalog snapshot. A warning identifies evidence boundaries; it does **not** authenticate either source, confirm that a program is currently offered, or establish licensure or admissions eligibility.

The applied capstone asks for a bounded conclusion and a further verification step. The reflection check tests whether fields are present, **not** whether the conclusion is correct.

## Privacy and evidence
Use fictional or public records only. The worksheet is processed in the browser; its TXT download contains the fields entered by the learner and the review warnings. **Do not enter private records or personal identifiers.** Do not distribute an exported TXT without reviewing its contents. A source identifier is a citation aid, not a guarantee of source quality. Historical completions, current offerings, admissions policy, and score distributions are distinct evidence categories.

## Minimum review acceptance
1. Open `index.html` locally and load the fictional example. Review comparability; confirm the historical/current mismatch is explained without asserting that either record proves a current offering.
2. Download the reviewed TXT and inspect its actual content for both records, source identifiers, dates, warnings, and absence of unrelated browser data.
3. Change one record after review. Export must become disabled until a new review; clearing a required field must not permit export.
4. Test a future evidence date, differing source identifiers, missing inputs, and a corrected comparison. Warnings must describe uncertainty rather than fabricate a result.
5. Operate all controls using keyboard alone, confirm visible focus and announced feedback, and check layout at a 320px viewport. Record actual outcomes rather than treating this checklist as completed testing.
6. Run relevant scoped CI against the exact candidate commit; distinguish any unrelated portfolio-wide failure.

## Release boundary
Keep this candidate on its review branch until browser acceptance, applicable CI, and item-specific publication authorization are documented. The existing live College + Career Matcher must not be replaced or modified by this exercise. Do not use this README as public-facing communication to the site owner.
