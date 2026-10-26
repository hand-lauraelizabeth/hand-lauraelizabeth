// HTTP-served, synthetic-only editable plan import/export acceptance tests.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
import {chromium,firefox,webkit} from 'playwright';
const root=dirname(fileURLToPath(import.meta.url));
const assets=new Map([['/','index.html'],['/index.html','index.html'],['/style.css','style.css'],
 ['/app.mjs','app.mjs'],['/engine.mjs','engine.mjs'],['/plan.mjs','plan.mjs']]);
const server=createServer((req,res)=>{
 const file=assets.get(new URL(req.url,'http://localhost').pathname);
 if(!file){res.writeHead(404).end('Not found');return;}
 try{res.writeHead(200,{'Content-Type':file.endsWith('.html')?'text/html':file.endsWith('.css')?'text/css':'text/javascript'}).end(readFileSync(join(root,file)));}
 catch{res.writeHead(500).end('Asset unavailable');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const url='http://127.0.0.1:'+server.address().port+'/',expect=(condition,message)=>{assert.ok(condition,message);checks++};
let checks=0;
const upload=(page,content,name='cash-flow-plan.json',mimeType='application/json')=>page.locator('#load-plan').setInputFiles({name,mimeType,buffer:Buffer.isBuffer(content)?content:Buffer.from(content)});
async function download(page,button){
 const [file]=await Promise.all([page.waitForEvent('download'),page.locator(button).click()]);
 return readFileSync(await file.path(),'utf8');
}
try{
 for(const [name,type] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]]){
  const browser=await type.launch({headless:true});
  try{
   const page=await browser.newPage({viewport:{width:320,height:720},acceptDownloads:true});
   const offsite=[],errors=[];
   page.on('request',r=>{if(!r.url().startsWith(url)&&!r.url().startsWith('blob:'+url))offsite.push(r.url())});
   page.on('pageerror',e=>errors.push(e.message));
   await page.goto(url,{waitUntil:'networkidle'});
   expect(await page.locator('#save-plan').isVisible(),name+' save control');
   expect(await page.getByLabel('Reopen a saved plan JSON').count()===1,name+' labeled import');
   await page.locator('#start').fill('2026-10-25');
   await page.locator('#end').fill('2026-11-25');
   await page.locator('#opening').fill('123.45');
   await page.locator('#event-id').fill(' 00007 ');
   await page.locator('#event-label').fill('=HYPERLINK("x")');
   await page.locator('#event-amount').fill('-100.25');
   await page.locator('#event-date').fill('2026-10-31');
   await page.locator('#event-repeat').selectOption('monthly');
   await page.getByRole('button',{name:'Add event'}).click();
   await page.locator('#shift-id').selectOption(' 00007 ');
   await page.locator('#shift-days').fill('2');
   await page.locator('#calculate').click();
   expect(await page.locator('#export-json').isEnabled(),name+' calculated JSON enabled');
   const before=await download(page,'#export-json');
   const saved=await download(page,'#save-plan');
   const plan=JSON.parse(saved);
   expect(plan.schema==='cash-flow-plan/v1',name+' plan schema');
   expect(plan.events[0].id===' 00007 '&&plan.events[0].label==='=HYPERLINK("x")',name+' exact source fields');
   expect(plan.openingCents===12345&&plan.shiftDays===2&&plan.shiftId===' 00007 ',name+' exact timing inputs');
   expect(!('days' in plan),name+' plan does not misrepresent projected output as inputs');
   // Malformed and invalid plans cannot destroy an existing calculation.
   await upload(page,'{"schema":"cash-flow-plan/v1","events":[]}');
   await page.waitForFunction(()=>document.querySelector('#error')?.textContent?.length>0);
   expect(await page.locator('#export-json').isEnabled(),name+' invalid file preserves export');
   expect(await download(page,'#export-json')===before,name+' invalid file preserves JSON bytes');
   expect((await page.locator('#events').textContent()).includes(' 00007 '),name+' invalid file preserves event');
   // User declines replacement: both settings and previously calculated export survive.
   page.once('dialog',dialog=>dialog.dismiss());
   await upload(page,saved);
   await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('import cancelled'));
   expect(await download(page,'#export-json')===before,name+' cancelled import preserves JSON');
   expect(await page.locator('#opening').inputValue()==='123.45',name+' cancelled import preserves settings');
   // Change the live plan, then restore from the exact saved JSON.
   await page.locator('#opening').fill('999.00');
   expect(await page.locator('#export-json').isDisabled(),name+' edited inputs invalidate stale result');
   page.once('dialog',dialog=>dialog.accept());
   await upload(page,saved);
   await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('loaded locally'));
   expect(await page.locator('#opening').inputValue()==='123.45',name+' confirmed import restores opening');
   expect(await page.locator('#shift-id').inputValue()===' 00007 ',name+' confirmed import restores shift ID');
   expect(await page.locator('#shift-days').inputValue()==='2',name+' confirmed import restores shift days');
   expect((await page.locator('#events').textContent()).includes('=HYPERLINK("x")'),name+' exact formula-like text preserved locally');
   expect(await page.locator('#export-json').isDisabled(),name+' confirmed import invalidates prior projection');
   expect(await page.evaluate(()=>document.activeElement.id)==='event-id',name+' import restores focus');
   expect(await download(page,'#save-plan')===saved,name+' exported plan roundtrips byte-identically');
   // The shifted projection is valid, but its baseline exceeds the supported
   // balance limit. Reject before confirmation without clearing current data.
   await page.locator('#calculate').click();
   const currentScenario=await download(page,'#export-json');
   const baselineOverflow={schema:'cash-flow-plan/v1',start:'2026-10-25',end:'2026-10-25',
     openingCents:1000000000000,
     events:[{id:'synthetic-income',label:'Synthetic income',date:'2026-10-25',repeat:'once',cents:1}],
     shiftId:'synthetic-income',shiftDays:1};
   await upload(page,JSON.stringify(baselineOverflow));
   await page.waitForFunction(()=>document.querySelector('#error')?.textContent?.includes('Projected balance exceeds limit'));
   expect(await page.locator('#export-json').isEnabled(),name+' overflow import preserves existing projection');
   expect(await download(page,'#export-json')===currentScenario,name+' overflow import preserves exact scenario JSON');
   expect(await download(page,'#save-plan')===saved,name+' overflow import preserves editable plan');
   expect((await page.locator('#events').textContent()).includes(' 00007 '),name+' overflow import preserves event ID');
   await upload(page,Buffer.alloc(256001,65));
   await page.waitForFunction(()=>document.querySelector('#error')?.textContent?.includes('256,000'));
   expect(await download(page,'#save-plan')===saved,name+' oversized file preserves plan');

   // Deliberately hold a real File.arrayBuffer() read while a newer local plan
   // is imported. The obsolete read must not overwrite either the new plan or
   // its success announcement with a misleading stale-input error.
   await page.evaluate(()=>{
     window.__delayedPlanReads=[];
     const original=File.prototype.arrayBuffer;
     File.prototype.arrayBuffer=function(){
       if(!this.name.startsWith('delayed-'))return original.call(this);
       const file=this;
       return new Promise(resolve=>{
         window.__delayedPlanReads.push({name:file.name,release:()=>resolve(original.call(file))});
       });
     };
   });
   await upload(page,saved,'delayed-old.json');
   await page.waitForFunction(()=>window.__delayedPlanReads.length===1);
   const newerPlan={...plan,openingCents:45678};
   page.once('dialog',dialog=>dialog.accept());
   await upload(page,JSON.stringify(newerPlan),'newer.json');
   await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('loaded locally'));
   expect(await page.locator('#opening').inputValue()==='456.78',name+' newer import replaces opening');
   await page.evaluate(()=>window.__delayedPlanReads[0].release());
   await page.waitForTimeout(150);
   expect(await page.locator('#opening').inputValue()==='456.78',name+' obsolete import cannot replace newer plan');
   expect(await page.locator('#error').innerText()==='',name+' obsolete import cannot overwrite newer success with error');
   expect((await page.locator('#status').innerText()).includes('loaded locally'),name+' newer success announcement survives stale completion');
   expect(JSON.parse(await download(page,'#save-plan')).openingCents===45678,name+' exported editable plan retains newer value');

   // An actual user edit while a file is pending must also prevent replacement
   // and preserve the edited input without a confirmation dialog.
   await upload(page,saved,'delayed-edit.json');
   await page.waitForFunction(()=>window.__delayedPlanReads.length===2);
   await page.locator('#opening').fill('777.00');
   await page.evaluate(()=>window.__delayedPlanReads[1].release());
   await page.waitForFunction(()=>document.querySelector('#error')?.textContent?.includes('inputs changed'));
   expect(await page.locator('#opening').inputValue()==='777.00',name+' user edit wins pending import');
   expect(JSON.parse(await download(page,'#save-plan')).openingCents===77700,name+' saved plan preserves edited amount');
   expect(await page.locator('#export-json').isDisabled(),name+' user edit keeps old projection invalidated');

   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1),name+' 320px no page overflow');
   expect(errors.length===0,name+' no uncaught browser exceptions '+errors.join(';'));
   expect(offsite.length===0,name+' no outbound requests '+offsite.join(';'));
   await page.close();
   console.log(name+': editable plan import/export, validation, cancellation, focus and privacy PASS');
  }finally{await browser.close();}
 }
 console.log(checks+' FT-04 browser-local editable plan assertions PASS');
}finally{await new Promise(resolve=>server.close(resolve));}
