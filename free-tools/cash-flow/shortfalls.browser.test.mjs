// HTTP-served, synthetic-only end-of-day shortfall acceptance in three browsers.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium,firefox,webkit} from 'playwright';
const root=dirname(fileURLToPath(import.meta.url));
const assets=new Map([['/','index.html'],['/index.html','index.html'],['/style.css','style.css'],
 ['/app.mjs','app.mjs'],['/engine.mjs','engine.mjs'],['/plan.mjs','plan.mjs'],['/shortfalls.mjs','shortfalls.mjs']]);
const server=createServer((req,res)=>{
 const file=assets.get(new URL(req.url,'http://localhost').pathname);
 if(!file){res.writeHead(404).end('Not found');return;}
 try{res.writeHead(200,{'Content-Type':file.endsWith('.html')?'text/html':file.endsWith('.css')?'text/css':'text/javascript','Cache-Control':'no-store'}).end(readFileSync(join(root,file)));}
 catch{res.writeHead(500).end('Asset unavailable');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const url='http://127.0.0.1:'+server.address().port+'/';
let checks=0;
const check=(condition,message)=>{assert.ok(condition,message);checks++;};
try{
 for(const [name,type] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]]){
  const browser=await type.launch({headless:true});
  try{
   const page=await browser.newPage({viewport:{width:375,height:740},acceptDownloads:true});
   const offsite=[],errors=[];
   page.on('request',r=>{if(!r.url().startsWith(url)&&!r.url().startsWith('blob:'+url))offsite.push(r.url());});
   page.on('pageerror',e=>errors.push(e.message));
   await page.goto(url,{waitUntil:'networkidle'});
   check(await page.locator('#shortfall-summary[role="status"][aria-atomic="true"]').count()===1,name+' shortfall summary accessible status');
   await page.locator('#start').fill('2026-10-01');
   await page.locator('#end').fill('2026-10-05');
   await page.locator('#opening').fill('100.00');
   async function add(id,label,amount,date){
    await page.locator('#event-id').fill(id);
    await page.locator('#event-label').fill(label);
    await page.locator('#event-amount').fill(amount);
    await page.locator('#event-date').fill(date);
    await page.getByRole('button',{name:'Add event'}).click();
   }
   await add('bill-0001','Rent','-150.00','2026-10-02');
   await add('pay-0002','Paycheck','100.00','2026-10-04');
   await page.locator('#shift-id').selectOption('bill-0001');
   await page.locator('#shift-days').fill('3');
   await page.locator('#calculate').click();
   const summary=await page.locator('#shortfall-summary').innerText();
   check(summary.includes('Baseline: 2 projected below-zero end-of-day dates'),name+' baseline shortfall count');
   check(summary.includes('first 2026-10-02'),name+' baseline first date');
   check(summary.includes('lowest -50.00 USD'),name+' baseline lowest balance');
   check(summary.includes('longest consecutive span 2 days'),name+' baseline consecutive span');
   check(summary.includes('Scenario: no projected below-zero end-of-day dates'),name+' shifted scenario removes modeled below-zero days');
   check(summary.includes('intraday funds or overdraft rules'),name+' explicit modeling limitation');
   const balances=await page.locator('#results tr').evaluateAll(rows=>rows.map(r=>[...r.querySelectorAll('td')].map(c=>c.textContent)));
   assert.deepEqual(balances,[
    ['2026-10-01','0.00','100.00','100.00'],
    ['2026-10-02','0.00','-50.00','100.00'],
    ['2026-10-03','0.00','-50.00','100.00'],
    ['2026-10-04','100.00','50.00','200.00'],
    ['2026-10-05','-150.00','50.00','50.00']
   ],name+' table daily balances');checks++;
   const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#export-json').click()]);
   const json=JSON.parse(readFileSync(await download.path(),'utf8'));
   check(json.days.map(d=>d.balanceCents).join(',')==='10000,10000,10000,20000,5000',name+' JSON scenario remains exact');
   check(json.days[4].events[0].id==='bill-0001',name+' original event ID preserved');
   await page.locator('#shift-days').fill('0');
   check((await page.locator('#shortfall-summary').textContent())==='',name+' edit invalidates stale shortfall summary');
   check(await page.locator('#export-json').isDisabled(),name+' edit invalidates stale JSON');
   await page.locator('#calculate').click();
   const noShift=await page.locator('#shortfall-summary').innerText();
   check(noShift.includes('Scenario: 2 projected below-zero end-of-day dates'),name+' scenario recalculated after shift removal');
   check(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1),name+' 375px no horizontal page overflow');
   check(errors.length===0,name+' no uncaught exceptions: '+errors.join('; '));
   check(offsite.length===0,name+' no offsite requests: '+offsite.join('; '));
   console.log(name+' FT-04 shortfall browser acceptance PASS');
  }finally{await browser.close();}
 }
 console.log(checks+' FT-04 cross-browser shortfall assertions PASS');
}finally{await new Promise(resolve=>server.close(resolve));}
