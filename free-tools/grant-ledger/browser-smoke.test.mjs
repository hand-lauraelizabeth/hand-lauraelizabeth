import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {chromium} from 'playwright';
const files=['index.html','styles.css','app.mjs','core.mjs','view.mjs','render.mjs'];
const server=createServer(async(req,res)=>{
 const name=req.url==='/'?'index.html':req.url.slice(1);
 if(!files.includes(name)){res.writeHead(404);res.end();return;}
 res.setHeader('Content-Type',name.endsWith('.html')?'text/html':name.endsWith('.css')?'text/css':'text/javascript');
 res.end(await readFile(new URL(name,import.meta.url)));
});
let browser;
try {
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:320,height:720},acceptDownloads:true});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const response=await page.goto('http://127.0.0.1:'+server.address().port+'/',{waitUntil:'networkidle'});
 assert.equal(response.status(),200);
 assert.equal(await page.locator('#categoryForm').count(),1);
 await page.locator('#categoryForm [name=categoryId]').fill('CAT');
 await page.locator('#categoryForm [name=label]').fill('Operations');
 await page.locator('#categoryForm [name=budget]').fill('100.00');
 await page.locator('#categoryForm button[type=submit]').click();
 assert.equal(await page.locator('#budgetRows tr').count(),1);
 await page.locator('#expenseForm [name=transactionId]').fill('TX1');
 await page.locator('#expenseForm [name=sourceId]').fill(' SRC-01 ');
 await page.locator('#expenseForm [name=date]').fill('2026-02-15');
 await page.locator('#expenseForm [name=categoryId]').selectOption('CAT');
 await page.locator('#expenseForm [name=amount]').fill('10.00');
 await page.locator('#expenseForm [name=percent]').fill('50');
 await page.locator('#expenseForm [name=allocationBasis]').fill('Timesheet');
 await page.locator('#expenseForm [name=evidenceRef]').fill('DOC-01');
 await page.locator('#expenseForm button[type=submit]').click();
 assert.equal(await page.locator('#expenseRows tr').count(),1);
 assert.ok((await page.locator('#totals').innerText()).includes('Assigned $5.00'));
 assert.ok((await page.locator('#expenseRows').textContent()).includes(' SRC-01 '));
 assert.equal(errors.length,0);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1),false);
 await page.evaluate(()=>{document.documentElement.style.fontSize='200%';});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1),false);
 console.log('9 HTTP-served Chromium smoke assertions PASS');
} finally {if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
