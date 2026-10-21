# Example RFP workspace

Open `synthetic-workspace.json` in the RFP & Vendor Evaluation Matrix to explore weighted criteria, source references, review flags, and exports without uploading confidential information.

All supplier names, prices, ratings, reviewers, and evidence identifiers are fictional. The example deliberately includes a missing score, a missing evidence reference, an undisclosed price, a declared conflict, and a mandatory criterion below the illustrative review threshold.

The `comparisons` field contains an intentionally incorrect saved score. The application should ignore that saved calculation and recompute comparisons from the underlying criteria and ratings when reopening the file.

The tool supports transparent human review. It does not determine awards, eligibility, or procurement compliance. CSV exports may be blocked when text could be interpreted as executable spreadsheet content; use JSON for exact, lossless records.
