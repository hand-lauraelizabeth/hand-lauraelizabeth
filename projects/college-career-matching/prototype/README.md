# College + Career Matching — Service Contract Prototype

This is a **synthetic service-contract harness**, not the primary public interaction design, not a production matcher, and not an authoritative college-data release. It exists to exercise governed service boundaries while the current-data snapshot continues through release gates. The zero-friction visitor-facing interaction is maintained separately in `../public-explorer.html` and on the portfolio site.

## Run locally

From `projects/college-career-matching/prototype`:

```bash
python app.py
```

Open the local address printed by the server.

## Flow

1. Choose a decision starting point.
2. Enter explicit must-haves.
3. Set only priorities the user actually cares about.
4. Review a shortlist with evidence and unknowns.
5. Select 2–5 programs for side-by-side comparison.
6. Return to answers and revise priorities/constraints.

## Service metadata

The prototype now loads the governed `/metadata` contract before `/options`. It verifies that both responses describe the same data version and displays the data/model versions plus the explicit non-production authorization state. Review eligibility is therefore not silently rendered as deployment approval.

## Guardrails represented in the prototype

- institution × program is the candidate grain;
- no universal or automatic winner;
- missing evidence is displayed as unavailable, never zero;
- net price is labeled as net price, not generic cost;
- current labor-market evidence is separate from long-term outlook;
- comparison is evidence-oriented rather than a rank table;
- synthetic fixtures are explicitly labeled and must not be presented as current college facts.

## Production boundary

The browser prototype currently uses synthetic contract fixtures only. Production activation should replace fixture access with the governed `/metadata`, `/options`, `/match`, candidate-detail, and `/compare` service contracts after a current product snapshot passes its release gate. The browser should remain a renderer/interactor and must not independently reinterpret model semantics.
