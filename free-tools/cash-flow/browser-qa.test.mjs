// Real HTTP-served browser smoke tests; no production deployment or bank data.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {join,dirname} from 'node:path';
import {chromium,firefox,webkit,devices} from 'playwright';

const root=dirname(fileURLToPath(import.meta.url));
const assets=new Map([
  ['/','index.html'], ['/index.html','index.html'], ['/style.css','style.css'],
  ['/app.mjs','app.mjs'], ['/engine.mjs','engine.mjs'], ['/axe.min.js','node_modules/axe-core/axe.min.js']
]);
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.js':'text/javascript; charset=utf-8'};
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
    page.on('request',request=>{if(!request.url().startsWith(baseURL)&&!request.url().startsWith('blob:'+baseURL))offsite.push(request.url());});
    const response=await page.goto(baseURL,{waitUntil:'networkidle'});
    check(response.status()===200,name+': HTTP response failed');
    check((await page.title())==='Cash Flow & Bill Timing Simulator',name+': page title');
    check(await page.locator('#export').isDisabled(),name+': CSV export must begin disabled');
    check(await page.getByRole('main').count()===1,name+': main landmark');
    check(await page.getByRole('table',{name:'Projected end-of-day balances'}).count()===1,name+': table accessible name');
    check(await page.locator('#status[role="status"]').count()===1,name+': projection status announcement');
    check(await page.locator('#csv-warning[role="status"]').count()===1,name+': CSV risk status announcement');
    check(await page.getByRole('alert').count()===1,name+': error announcement');
    for(const id of ['start','end','opening','event-id','event-label','event-amount','event-date','event-repeat','shift-id','shift-days']){
      const label=await page.locator('#'+id).evaluate(el=>el.labels?.[0]?.textContent?.trim()||'');
      check(label.length>0,name+': unlabeled control '+id);
    }
    await page.keyboard.press('Tab');
    check((await page.evaluate(()=>document.activeElement.id))==='start',name+': first keyboard tab target');
    const firstFocus=await page.locator('#start').evaluate(el=>getComputedStyle(el).outlineWidth);
    check(parseFloat(firstFocus)>=3,name+': keyboard focus indicator missing');
    // Native date inputs can include internal month/day/year Tab stops.
    // Verify DOM control order while allowing repeated focus within one date widget.
    const visited=['start'];
    for(let step=0;step<45&&visited.at(-1)!=='calculate';step++){
      await page.keyboard.press('Tab');
      const current=await page.evaluate(()=>{
        const el=document.activeElement;
        return el.id||(el.tagName==='BUTTON'?el.textContent.trim():'');
      });
      if(current&&current!==visited.at(-1))visited.push(current);
    }
    const expected=['start','end','opening','event-id','event-label','event-amount','event-date','event-repeat','Add event','shift-id','shift-days','calculate'];
    assert.deepEqual(visited,expected,name+': keyboard control traversal order');
    checks++;

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
    // Axe is served from the same origin to respect the app's restrictive CSP.
    await page.addScriptTag({url:baseURL+'axe.min.js'});
    const audit=await page.evaluate(async()=>await window.axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}}));
    assert.deepEqual(audit.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)})),[],name+': automated WCAG accessibility violations');
    checks++;

    const [download]=await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button',{name:'Export scenario CSV'}).click()
    ]);
    const csv=readFileSync(await download.path(),'utf8');
    check(download.suggestedFilename()==='cash-flow-scenario.csv',name+': CSV filename');
    check(csv.startsWith('"Date","Change (USD)","End-of-day balance (USD)","Event IDs","Event labels"\r\n'),name+': CSV header');
    check(csv.includes('"2024-03-31",-20.00,60.00,"rent","Rent"'),name+': CSV shifted value');
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

    await page.locator('#calculate').click();
    check(await page.locator('#export').isDisabled(),name+': unsafe CSV download blocked');
    check(await page.locator('#export-json').isEnabled(),name+': lossless JSON available');
    check((await page.locator('#csv-warning').innerText()).includes('CSV export unavailable'),name+': visible CSV warning');
    const [jsonDownload]=await Promise.all([
      page.waitForEvent('download'),
      page.locator('#export-json').click()
    ]);
    const json=JSON.parse(readFileSync(await jsonDownload.path(),'utf8'));
    check(json.schema==='cash-flow-scenario/v1',name+': JSON schema');
    check(json.days.some(day=>day.events.some(event=>event.id==='formula'&&event.label==='=HYPERLINK("https://example.invalid")')),name+': exact formula-like text preserved in JSON');
    check(!errors.length,name+': uncaught JS exceptions: '+errors.join('; '));
    check(!offsite.length,name+': unexpected external requests: '+offsite.join('; '));
    await page.close();
    console.log(name+': PASS browser UI, keyboard, 320/640px reflow, HTTP CSP, local-only requests, CSV download ('+checks+' cumulative assertions)');
  }finally{await browser.close();}
}
async function testMobile(label,type,profile){
  // Emulated device touch/viewport is not a real iOS or Android device.
  const browser=await type.launch({headless:true});
  try{
    const context=await browser.newContext({...devices[profile],acceptDownloads:true});
    const page=await context.newPage(),errors=[],offsite=[];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('request',request=>{if(!request.url().startsWith(baseURL)&&!request.url().startsWith('blob:'+baseURL))offsite.push(request.url());});
    const response=await page.goto(baseURL,{waitUntil:'networkidle'});
    check(response.status()===200,label+': served HTTP');
    check(await page.evaluate(()=>matchMedia('(pointer: coarse)').matches),label+': emulated touch pointer');
    const sizes=await page.evaluate(()=>({viewport:document.documentElement.clientWidth,page:document.documentElement.scrollWidth}));
    check(sizes.page<=sizes.viewport+1,label+': horizontal page overflow on emulated mobile');
    check(await page.getByRole('button',{name:'Add event'}).isVisible(),label+': add button visible');

    await fill(page,'start','2026-10-14');
    await fill(page,'end','2026-10-16');
    await fill(page,'opening','500.00');
    await fill(page,'event-id','rent');
    await fill(page,'event-label','Rent');
    await fill(page,'event-amount','-200.00');
    await fill(page,'event-date','2026-10-15');
    await page.locator('#event-repeat').selectOption('once');
    await page.getByRole('button',{name:'Add event'}).tap();
    check((await page.locator('#events').textContent()).includes('Rent'),label+': touch adds event');
    await page.getByRole('button',{name:'Calculate projection'}).tap();
    await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('Calculated 3 days'));
    check((await page.locator('#summary').textContent()).includes('Scenario end 300.00 USD'),label+': touch calculates expected result');
    check(await page.locator('#results tr').count()===3,label+': results visible');
    const [download]=await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button',{name:'Export scenario CSV'}).tap()
    ]);
    const csv=readFileSync(await download.path(),'utf8');
    check(csv.includes('"2026-10-15",-200.00,300.00,"rent","Rent"'),label+': touch CSV download contents');
    await fill(page,'opening','400.00');
    check(await page.getByRole('button',{name:'Export scenario CSV'}).isDisabled(),label+': stale export blocked after edit');
    check(await page.locator('#results tr').count()===0,label+': stale results invalidated');
    await page.getByRole('button',{name:'Remove rent'}).tap();
    check((await page.locator('#events').textContent()).includes('No events added.'),label+': touch removes event');
    check(errors.length===0,label+': no page exceptions: '+errors.join('; '));
    check(offsite.length===0,label+': no offsite requests: '+offsite.join('; '));
    await context.close();
    console.log(label+': PASS touch-emulated add, calculate, download, invalidate, remove, responsive layout.');
  }finally{await browser.close();}
}

try{
  for(const [name,browser] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]]){
    await testBrowser(name,browser);
  }
  await testMobile('Pixel 7 / Chromium emulation',chromium,'Pixel 7');
  await testMobile('iPhone 13 / WebKit emulation',webkit,'iPhone 13');
  console.log(checks+' HTTP-served browser, axe WCAG scan and mobile-emulation assertions PASS.');
  console.log('Manual native zoom, assistive technology, physical mobile hardware, and spreadsheet-app CSV reopening remain pending.');
}finally{
  await new Promise(resolve=>server.close(resolve));
}
