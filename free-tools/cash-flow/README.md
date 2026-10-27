# Cash Flow & Bill Timing Simulator

A free, browser-local planning tool for testing how income dates, bill dates, and recurring payment timing could affect **end-of-day** balances. Add dated events, compare a shifted event schedule against the baseline, and export the scenario as CSV. No account, bank connection, or remote upload is required.

## Use

Serve this directory with a local static HTTP server (for example, `python3 -m http.server 8000` from within `free-tools/cash-flow`), then open `http://localhost:8000`. JavaScript modules generally cannot run directly from a `file://` URL.

Enter positive amounts for income and negative amounts for bills. Select an event and shift it by −60 to +60 calendar days to see a what-if scenario. For repeating events, **each occurrence is shifted independently**: a monthly January 31 bill shifted one day does not permanently reanchor subsequent bills to the first of the month.

The model accepts up to 200 events across 366 calendar days, within 1900–2100. It uses whole-cent arithmetic. Monthly recurring dates use the original day of month when possible and the final day of shorter months otherwise. Projections do not model settlement time, pending transactions, overdraft fees, interest, credit access, or individual banks' rules; they are **not verified account balances or financial advice**.

## Projected below-zero days

After calculating, the tool separately summarizes baseline and shifted-scenario dates with a **negative projected end-of-day balance**. It shows the number of such dates, first date, lowest balance and longest consecutive span. Zero is not negative. The summary updates only when you calculate and clears when inputs change; the detailed daily balances and exported scenario remain the underlying evidence. A negative projected closing balance is a planning flag, **not a prediction of an overdraft, bank fee, or payment outcome**. Intraday posting order, available balance and holds are not modeled.

## Compare which dates change

The scenario summary also distinguishes dates that were below zero in the baseline but are **no longer below zero** in the shifted scenario from dates that become **newly below zero**. It reports counts and the first date in each category, comparing the same calendar dates only. A shift can improve some dates and worsen others; a lower minimum alone does not capture that tradeoff. This is a projected end-of-day comparison, not a payment-clearance, fee, or overdraft determination. Changing any input clears the old summary.

## Export and spreadsheet safety

Export creates a UTF-8 CSV with date, daily change, end-of-day balance, event IDs, and event labels. Numeric balances retain two decimal places. Text resembling spreadsheet formulas is prefixed with an apostrophe before CSV quoting; this changes the original text and is only a **defense in depth**, not a universal guarantee against formula execution in every spreadsheet program or import setting.

When opening CSV in Excel, Google Sheets, or another spreadsheet program, inspect the import preview and explicitly treat **Event IDs** and **Event labels** as **text**, especially when untrusted names or labels are present. Check date and currency formatting, and do not enable formula execution from imported text. The CSV contains planning estimates only; verify important decisions against actual financial records.

## Automated validation

From the repository root, run the deterministic tests with Node.js:

```sh
node free-tools/cash-flow/engine.test.mjs
node free-tools/cash-flow/shortfalls.test.mjs
node free-tools/cash-flow/boundary.test.mjs
node free-tools/cash-flow/occurrence-anchor-regression.test.mjs
node free-tools/cash-flow/security-accessibility.test.mjs
node free-tools/cash-flow/csv-interop-fixture.mjs | python3 free-tools/cash-flow/csv-interop-import.test.py
```

GitHub Actions also runs HTTP-served browser tests in Chromium, Firefox, and WebKit, including axe-core automated WCAG scans and Pixel/iPhone touch emulation. These checks cannot establish physical-device behavior, native browser zoom, or real screen-reader experience. **Actual Excel/Google Sheets CSV reopening, native 200%/400% zoom, assistive-technology walkthroughs, and physical mobile-device tests remain outstanding release checks.**

References: Consumer Financial Protection Bureau, *Your Money, Your Goals*; OWASP CSV Injection; WCAG 2.2. Last reviewed October 14, 2026.
