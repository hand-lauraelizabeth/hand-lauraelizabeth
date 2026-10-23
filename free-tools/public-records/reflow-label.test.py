"""Synthetic-only Chromium reflow check; run with Python Playwright installed.
Checks text enlargement, not native browser zoom or screen-reader support.
"""
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
HTML = (HERE / "index.html").read_text(encoding="utf-8")
CSS = (HERE / "styles.css").read_text(encoding="utf-8")
FIX = "font-weight:600;min-width:0;overflow-wrap:anywhere}input,select"
assert FIX in CSS

def document(css):
    html = HTML.replace('<link rel="stylesheet" href="styles.css">', f"<style>{css}</style>")
    html = html.replace('<script type="module" src="app.mjs"></script>', "")
    return html.replace('<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'self\'; style-src \'self\'; connect-src \'none\'; img-src \'none\'; object-src \'none\'; base-uri \'none\'; form-action \'none\'">', "")

async def main():
    async with async_playwright() as p:
        opts = {"headless": True, "args": ["--no-sandbox"]}
        executable = os.getenv("FT09_CHROMIUM_PATH", "/usr/bin/chromium")
        if Path(executable).exists():
            opts["executable_path"] = executable
        browser = await p.chromium.launch(**opts)
        checks = 0
        for width in (320, 375):
            for rem in (2, 4):
                page = await browser.new_page(viewport={"width": width, "height": 800})
                await page.set_content(document(CSS))
                await page.evaluate(f'document.body.style.fontSize="{rem}rem"')
                dims = await page.evaluate('({scroll:document.documentElement.scrollWidth,inner:innerWidth,labels:document.querySelectorAll("label").length})')
                assert dims["labels"] >= 14 and dims["scroll"] <= dims["inner"], (width, rem, dims)
                checks += 1
                await page.close()
        baseline = CSS.replace(FIX, "font-weight:600;min-width:0}input,select")
        page = await browser.new_page(viewport={"width": 320, "height": 800})
        await page.set_content(document(baseline))
        await page.evaluate('document.body.style.fontSize="4rem"')
        dims = await page.evaluate('({scroll:document.documentElement.scrollWidth,inner:innerWidth})')
        assert dims["scroll"] > dims["inner"], ("negative control unexpectedly passed", dims)
        checks += 1
        await page.close()
        await browser.close()
        print(f"PASS: {checks} Chromium reflow and negative-control assertions")

if __name__ == "__main__":
    asyncio.run(main())
