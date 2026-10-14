// Real HTTP-served browser smoke tests; no production deployment or bank data.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {join,dirname} from 'node:path';
import {chromium,firefox,webkit} from 'playwright';

const root=dirname(fileURLToPath(import.meta.url));
const assets=new Map([
  ['/','index.html'], ['/index.html','index.html'], ['/style.css','style.css'],
  ['/app.mjs','app.mjs'], ['/engine.mjs','engine.mjs']
]);
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.mjs':'text/javascript; charset=utf-8'};
const server=createServer((req,res)=>{
  const name=assets.get(new URL(req.url,'http://localhost').pathname);
  if(!name){res.writeHead(404).end('Not found');return;}
  const ext=name.slice(name.lastIndexOf('.'));
  try{
    res.writeHead(200,{'Content-Type':types[ext],'Cache-Control':'no-store'});
    res.end(readFileSync(join(root,name)));
  }catch{res.writeHead(500).end('Asset unavailable');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const baseURL='http://127.0.0.1:'+server.address().port+'/';
let checks=0;
const check=(condition,message)=>{assert.ok(condition,message);checks++};
const fill=async(page,id,value)=>page.locator('#'+id).fill(value);
async function testBrowser(name,type){
  const browser=await type.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1280,height:800},acceptDownloads:true});
    const errors=[],offsite=[];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('request',request=>{if(!request.url().startsWith(baseURL))offsite.push(request.url());});
    const response=await page.goto(baseURL,{waitUntil:'networkidle'});
    check(response.status()===200,name+': HTTP response failed');
    check((await page.title())==='Cash Flow & Bill Timing Simulator',name+': page title');
    check(await page.locator('#export').isDisabled(),name+': CSV export must begin disabled');
    check(await page.getByRole('main').count()===1,name+': main landmark');
    check(await page.getByRole('table',{name:'Projected end-of-day balances'}).count()===1,name+': table accessible name');
    check(await page.getByRole('status').count()===1,name+': status announcement');
    check(await page.getByRole('alert').count()===1,name+': error announcement');
    for(const id of ['start','end','opening','event-id','event-label','event-amount','event-date','event-repeat','shift-id','shift-days']){
      const label=await page.locator('#'+id).evaluate(el=>el.labels?.[0]?.textContent?.trim()||'');
      check(label.length>0,name+': unlabeled control '+id);
    }
    await page.keyboard.press('Tab');
    check((await page.evaluate(()=>document.activeElement.id))==='start',name+': first keyboard tab target');

    await fill(page,'start','2024-02-01');
    await fill(page,'end','2024-05-10');
    await fill(page,'opening','100.00');
    await fill(page,'event-id','rent');
    await fill(page,'event-label','Rent');
    await fill(page,'event-amount','-20.00');
    await fill(page,'event-date','2024-01-30');
    await page.locator('#event-repeat').selectOption('monthly');
    await page.getByRole('button',{name:'Add event'}).click();
    check((await page.locator('#events li').allTextContents()).join(' ').includes('Rent'),name+': event added');
    await page.locator('#shift-id').selectOption('rent');
    await fill(page,'shift-days','1');
    await page.locator('#calculate').focus();
    await page.keyboard.press('Enter'); // explicit keyboard activation
    await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('Calculated 100 days'));
    check(await page.locator('#export').isEnabled(),name+': scenario CSV enabled');
    const actual=await page.locator('#results tr').evaluateAll(rows=>
      rows.map(row=>[...row.querySelectorAll('td')].map(cell=>cell.textContent))
        .filter(cells=>cells[1]!=='0.00')
        .map(cells=>[cells[0],cells[1]]));
    assert.deepEqual(actual,[['2024-03-01','-20.00'],['2024-03-31','-20.00'],['2024-05-01','-20.00']],name+': recurring shift drift');
    checks++;
    check((await page.locator('#summary').textContent()).includes('Scenario end 40.00 USD'),name+': scenario balance');

    const [download]=await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button',{name:'Export scenario CSV'}).click()
    ]);
    const csv=readFileSync(await download.path(),'utf8');
    check(download.suggestedFilename()==='cash-flow-scenario.csv',name+': CSV filename');
    check(csv.startsWith('"Date","Change (USD)","End-of-day balance (USD)","Event IDs","Event labels"\r\n'),name+': CSV header');
    check(csv.includes('2024-03-31,-20.00,60.00,"rent","Rent"'),name+': CSV shifted value');
    check(csv.endsWith('\r\n'),name+': CSV CRLF rows');

    // Equivalent CSS viewport widths for 200% and 400% reflow at a 1280px viewport;
    // NOT a substitute for manual native browser zoom testing.
    for(const width of [640,320]){
      await page.setViewportSize({width,height:800});
      const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
      check(overflow<=1,name+': page horizontal overflow at CSS viewport '+width+'px ('+overflow+')');
      check(await page.getByRole('button',{name:'Calculate projection'}).isVisible(),name+': calculate hidden at '+width+'px');
    }
    await page.reload({waitUntil:'networkidle'});
    check(await page.locator('#export').isDisabled(),name+': session not persisted to storage');
    const inlineExecuted=await page.evaluate(()=>{
      const script=document.createElement('script');
      script.textContent='window.__cspInlineProbe=1';
      document.body.appendChild(script);
      return window.__cspInlineProbe===1;
    });
    check(!inlineExecuted,name+': inline scripts not blocked by HTTP-served CSP');
    await fill(page,'event-id','formula');
    await fill(page,'event-label','=HYPERLINK("https://example.invalid")');
    await fill(page,'event-amount','1.00');
    await fill(page,'event-date','2026-10-14');
    await page.getByRole('button',{name:'Add event'}).click();
    check((await page.locator('#events li').allTextContents()).join('').includes('=HYPERLINK('),name+': formula text visible safely');
    check(await page.locator('#events a').count()===0,name+': unsafe label created HTML');
    check(!errors.length,name+': uncaught JS exceptions: '+errors.join('; '));
    check(!offsite.length,name+': unexpected external requests: '+offsite.join('; '));
    await page.close();
    console.log(name+': PASS browser UI, keyboard, 320/640px reflow, HTTP CSP, local-only requests, CSV download ('+checks+' cumulative assertions)');
  }finally{await browser.close();}
}
try{
  for(const [name,browser] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]]){
    await testBrowser(name,browser);
  }
  console.log(checks+' HTTP-served cross-browser FT-04 assertions PASS.');
  console.log('Manual native browser zoom, screen-reader AT, mobile OS, and spreadsheet-app CSV reopening remain pending.');
}finally{
  await new Promise(resolve=>server.close(resolve));
}
