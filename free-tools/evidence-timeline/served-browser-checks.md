# Evidence & Timeline Builder: Browser Verification

The browser test exercises the standalone Evidence & Timeline Builder with synthetic records. Run it locally from the repository root after installing Playwright and its Chromium browser.

```sh
npm install --no-save playwright@1.55.1
npx playwright install chromium
node free-tools/evidence-timeline/served-browser-smoke.cjs
```

The test serves the tool from a loopback HTTP origin, so browser module loading and the page's Content Security Policy remain active. It checks form entry, review-status filtering, and 320-pixel reflow. The test does not upload records to an external service.

Passing automated checks does not replace manual screen-reader, browser zoom, cross-browser, or spreadsheet interoperability testing.
