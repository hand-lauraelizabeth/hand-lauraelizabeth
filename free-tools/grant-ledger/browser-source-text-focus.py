"""Synthetic Chromium regression: source IDs remain text; errors receive focus.

DOM-injected module execution; not a test of HTTP CSP or native zoom.
"""
import asyncio, os
from pathlib import Path
from playwright.async_api import async_playwright

root=Path(__file__).resolve().parent
core=(root/'core.mjs').read_text().replace('export ','')
view=(root/'view.mjs').read_text().replace('export ','')
render=(root/'render.mjs').read_text().replace("import {formatMoney} from './core.mjs';",'const {formatMoney}=window.core;').replace('export ','')
app=(root/'app.mjs').read_text()
for line in [
    "import {calculateLedger,exportTransactionsCSV,exportBudgetCSV,exportJSON} from './core.mjs';",
    "import {buildInterface} from './view.mjs';",
    "import {renderLedger} from './render.mjs';",
]:
    assert line in app
    app=app.replace(line,'')
app='const {calculateLedger,exportTransactionsCSV,exportBudgetCSV,exportJSON}=window.core;const {buildInterface}=window.view;const {renderLedger}=window.render;'+app
js='\n'.join([
    '{'+core+';window.core={calculateLedger,exportTransactionsCSV,exportBudgetCSV,exportJSON,formatMoney};}',
    '{'+view+';window.view={buildInterface};}',
    '{'+render+';window.render={renderLedger};}',
    '{'+app+'}',
])
html=(root/'index.html').read_text()
html=html.replace('<script type="module" src="app.mjs"></script>','')
html=html.replace('<link rel="stylesheet" href="styles.css">','')
html=html.replace('<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'self\'; style-src \'self\'; connect-src \'none\'; img-src \'none\'; object-src \'none\'; base-uri \'none\'; form-action \'none\'">','')

async def main():
    async with async_playwright() as p:
        kw={'executable_path':os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE']} if os.getenv('PLAYWRIGHT_CHROMIUM_EXECUTABLE') else {}
        b=await p.chromium.launch(**kw)
        page=await b.new_page(viewport={'width':320,'height':720})
        await page.set_content(html)
        await page.add_style_tag(content=(root/'styles.css').read_text())
        await page.add_script_tag(content=js)
        for name,value in {'categoryId':'C1','label':'Operations','budget':'100.00'}.items():
            await page.locator(f'#categoryForm [name="{name}"]').fill(value)
        await page.locator('#categoryForm button[type=submit]').click()
        source='<strong>Case A-001</strong>'
        for name,value in {'transactionId':'T1','sourceId':source,'date':'2026-02-15','amount':'2.00','percent':'50','allocationBasis':'Timesheet','evidenceRef':'Proof'}.items():
            await page.locator(f'#expenseForm [name="{name}"]').fill(value)
        await page.locator('#expenseForm [name=categoryId]').select_option('C1')
        await page.locator('#expenseForm button[type=submit]').click()
        assert await page.locator('#expenseRows tr').count()==1
        assert source in await page.locator('#expenseRows').text_content()
        assert await page.locator('#expenseRows strong').count()==0
        for name,value in {'transactionId':'T2','sourceId':'S2','date':'2026-02-16','amount':'-2'}.items():
            await page.locator(f'#expenseForm [name="{name}"]').fill(value)
        await page.locator('#expenseForm [name=categoryId]').select_option('C1')
        await page.locator('#expenseForm button[type=submit]').click()
        assert await page.locator('#expenseRows tr').count()==1
        assert await page.locator('#error').is_visible()
        assert await page.evaluate('document.activeElement.id')=='error'
        assert not await page.evaluate('document.documentElement.scrollWidth>document.documentElement.clientWidth+1')
        print('7 Chromium source-text and error-focus assertions PASS (DOM-injected)')
        await b.close()
asyncio.run(main())
