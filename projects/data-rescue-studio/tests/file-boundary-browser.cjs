'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {createServer}=require('node:http'),{chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch();
 let n=0;
 const ok=(v,label)=>{assert.ok(v,label);n++;};
 const upload=async(page,id,name,data)=>page.locator(id).setInputFiles({name,mimeType:'text/csv',buffer:Buffer.isBuffer(data)?data:Buffer.from(data)});
 const oversized=Buffer.alloc(5000001,0x20);
 // Serve the real interfaces from an isolated origin under a restrictive CSP.
 const assets=new Set(['index.html','history-preview.html','rescue-core.js','file-reader.js','reconcile-core.js','comparison-issue-index.js','provenance-core.js','reconcile-ui.js','history-core.js','history-ui.js']);
 const server=createServer((req,res)=>{
  const asset=new URL(req.url,'http://localhost').pathname.slice(1);
  if(!assets.has(asset)){res.writeHead(404).end('Not found');return;}
  try{
   res.writeHead(200,{'Content-Type':asset.endsWith('.html')?'text/html; charset=utf-8':'text/javascript; charset=utf-8',
    'Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'none'; object-src 'none'; base-uri 'none'",
    'Cache-Control':'no-store'});
   res.end(fs.readFileSync(path.resolve(__dirname,'..',asset)));
  }catch{res.writeHead(500).end('Asset unavailable');}
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const origin='http://127.0.0.1:'+server.address().port;
 try{
  for(const [html,selector] of [['index.html','#status'],['history-preview.html','#loadStatus']]){
   const page=await browser.newPage({acceptDownloads:true,viewport:{width:320,height:820}});
   const errors=[],requests=[];
   page.on('pageerror',err=>errors.push(err.message));
   page.on('request',r=>{if(/^https?:/.test(r.url())&&!r.url().startsWith(origin+'/'))requests.push(r.url());});
   await page.goto(origin+'/'+html,{waitUntil:'networkidle'});
   const status=async part=>{
    try {await page.waitForFunction(([id,value])=>document.querySelector(id)?.textContent.includes(value),[selector,part],{timeout:10000});}
    catch(error){
     const observed=await page.locator(selector).textContent().catch(()=>'<missing status>');
     throw Error(html+': expected status '+JSON.stringify(part)+'; observed '+JSON.stringify(observed)+'; page errors '+JSON.stringify(errors)+'; '+error.message);
    }
   };
   const boot=await page.evaluate(()=>({
    reader:typeof window.DataRescueFileReader?.read,
    compare:typeof window.DataRescueCompareUI?.setPrimary,
    missing:['compareIdentifier','compareIdentifierFind','compareIdentifierClear','compareFindingFilter','comparePrev','compareNext','comparePageStatus','compareJson','compareIndex'].filter(id=>!document.getElementById(id))
   }));
   ok(boot.reader==='function'&&boot.compare==='function'&&boot.missing.length===0,html+': complete reconciliation UI boots without missing controls');
   ok(errors.length===0,html+': no initial script errors');
   await upload(page,'#file','corrupt.csv',Buffer.from([0x49,0x44,0x0a,0xc3,0x28]));
   await status('Invalid UTF-8');
   ok(await page.locator('#save').isDisabled(),html+': invalid UTF-8 fails closed');
   await upload(page,'#file','binary.csv',Buffer.from([0x49,0x44,0x0a,0x00,0x31]));
   await status('NUL characters');
   ok(await page.locator('#save').isDisabled(),html+': NUL bytes fail closed');
   await upload(page,'#file','misnamed.csv.exe','ID\n1');
   await status('.csv or .tsv');
   ok(await page.locator('#save').isDisabled(),html+': disguised extension fails closed');
   // Untrusted filenames can contain embedded newlines or bidi overrides.
   // Neither may be echoed as an apparently normal source in evidence/status.
   for(const [label,name] of [
    ['line break','report\nprivate.csv'],
    ['bidi override','report\u202Etxt.csv'],
    ['bidi isolate','report\u2066private.csv']
   ]){
    await upload(page,'#file',name,'ID\n1');
    await status('unsupported control or direction');
    ok(await page.locator('#save').isDisabled(),html+': '+label+' filename blocked before parsing');
    ok(await page.locator('#file').getAttribute('aria-invalid')==='true',html+': '+label+' upload error announced');
    ok(await page.locator(selector).evaluate(node=>document.activeElement===node),html+': '+label+' error focus recovered');
   }
   await upload(page,'#file','oversize.csv',oversized);
   await status('5 MB');
   ok(await page.locator('#save').isDisabled(),html+': 5 MB over-limit blocked');
   await upload(page,'#file','bad.csv','id,value\n1,2,3');
   await status('No data was discarded');
   ok(await page.locator('#save').isDisabled(),html+': malformed row blocked');
   const good=Buffer.concat([Buffer.from([0xef,0xbb,0xbf]),Buffer.from('Name,Note\n=1+2,\u00e9\n+2,note\n@SUM(A1),other\n -4,more')]);
   await upload(page,'#file','valid.CSV',good);
   await page.waitForFunction(id=>document.querySelector(id)?.textContent.includes('Loaded'),selector);
   ok(await page.locator('#save').isEnabled(),html+': BOM and non-ASCII UTF-8 accepted');
   ok(await page.locator('#file').getAttribute('aria-invalid')===null,html+': successful first-file retry clears invalid state');
   const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#save').click()]);
   const csv=fs.readFileSync(await download.path(),'utf8');
   ok(csv.includes('"\t=1+2"')&&csv.includes('"\t+2"')&&csv.includes('"\t@SUM(A1)"')&&csv.includes('"\t -4"'),html+': local CSV spreadsheet precaution prefixes formula-like rows');
   ok(csv.includes('\u00e9'),html+': Unicode characters preserved on export');

   if(html==='history-preview.html'){
    // Fault injection: browser download APIs can fail even after valid local parsing.
    // The source, manifest, and retry controls must survive both failure modes.
    await page.evaluate(()=>{
     window.__ft02DownloadOriginals={create:URL.createObjectURL,revoke:URL.revokeObjectURL,click:HTMLAnchorElement.prototype.click};
     URL.createObjectURL=()=>{throw Error('synthetic private URL failure');};
    });
    await page.locator('#save').click();
    ok((await page.locator('#loadStatus').textContent()).includes('download could not be started'),html+': blocked CSV URL reports a text error');
    ok(await page.locator('#loadStatus').evaluate(node=>document.activeElement===node),html+': CSV export error receives focus');
    ok(await page.locator('#file').getAttribute('aria-invalid')===null,html+': valid upload not mislabeled invalid after CSV export failure');
    ok(await page.locator('#save').isEnabled(),html+': CSV export remains retryable');
    await page.locator('#historyExport').click();
    ok((await page.locator('#historyStatus').textContent()).includes('download could not be started'),html+': blocked manifest URL reports a text error');
    ok(await page.locator('#historyStatus').evaluate(node=>document.activeElement===node),html+': manifest export error receives focus');
    ok(await page.locator('#historyExport').isEnabled(),html+': manifest export remains retryable');
    await page.evaluate(()=>{
     const originals=window.__ft02DownloadOriginals;
     URL.createObjectURL=originals.create;
     window.__ft02Revoked=0;
     URL.revokeObjectURL=function(...args){window.__ft02Revoked++;return originals.revoke.apply(URL,args);};
     HTMLAnchorElement.prototype.click=function(){throw Error('synthetic private click failure');};
    });
    await page.locator('#save').click();
    ok((await page.locator('#loadStatus').textContent()).includes('download could not be started'),html+': blocked CSV click reports a text error');
    await page.locator('#historyExport').click();
    ok((await page.locator('#historyStatus').textContent()).includes('download could not be started'),html+': blocked manifest click reports a text error');
    const cleanup=await page.evaluate(()=>({revoked:window.__ft02Revoked,anchors:document.querySelectorAll('a[download]').length}));
    ok(cleanup.revoked===2&&cleanup.anchors===0,html+': failed CSV and manifest clicks revoke both URLs and remove both anchors');
    await page.evaluate(()=>{
     const originals=window.__ft02DownloadOriginals;
     URL.createObjectURL=originals.create;
     URL.revokeObjectURL=originals.revoke;
     HTMLAnchorElement.prototype.click=originals.click;
    });
    const [retriedCsv]=await Promise.all([page.waitForEvent('download'),page.locator('#save').click()]);
    ok(fs.readFileSync(await retriedCsv.path(),'utf8').includes('"\\t=1+2"'),html+': working-copy CSV retry preserves spreadsheet precaution');
    ok((await page.locator('#loadStatus').textContent()).includes('download started'),html+': successful CSV retry does not claim saved');
    const [manifestDownload]=await Promise.all([page.waitForEvent('download'),page.locator('#historyExport').click()]);
    const manifestText=fs.readFileSync(await manifestDownload.path(),'utf8');
    const manifest=JSON.parse(manifestText);
    ok(typeof manifest==='object'&&!manifestText.includes('=1+2')&&!manifestText.includes('é'),html+': manifest retry is valid JSON without original cell values');
    ok((await page.locator('#historyStatus').textContent()).includes('download started'),html+': successful manifest retry does not claim saved');
    ok((await page.locator('#historyStatus').getAttribute('role'))==='status',html+': manifest success clears prior alert role');
   }

   await upload(page,'#compareFile','misleading\u202Etxt.csv','Code,Value\n1,ok');
   await page.waitForFunction(()=>document.querySelector('#compareStatus')?.textContent.includes('unsupported control or direction'));
   ok(await page.locator('#compareRun').isDisabled(),html+': second-file bidi metadata rejected');
   ok(await page.locator('#compareFile').getAttribute('aria-invalid')==='true',html+': second-file error linked to input');
   ok(await page.locator('#compareStatus').evaluate(node=>document.activeElement===node),html+': second-file error receives focus');
   await upload(page,'#compareFile','right.csv',Buffer.from([0x49,0x44,0x0a,0xc3,0x28]));
   await page.waitForFunction(()=>document.querySelector('#compareStatus').textContent.includes('Invalid UTF-8'));
   ok(await page.locator('#compareRun').isDisabled(),html+': secondary invalid UTF-8 blocks reconciliation');
   await upload(page,'#compareFile','right.csv',oversized);
   await page.waitForFunction(()=>document.querySelector('#compareStatus').textContent.includes('5 MB'));
   ok(await page.locator('#compareRun').isDisabled(),html+': secondary over-limit blocked');
   await upload(page,'#compareFile','valid.tsv','Code\tValue\n1\tok');
   await page.waitForFunction(()=>document.querySelector('#compareStatus').textContent.includes('Loaded second file'));
   ok(await page.locator('#rightKey').isEnabled(),html+': valid TSV second file accepted');
   await page.locator('#leftKey').selectOption({index:1});
   await page.locator('#rightKey').selectOption({index:1});
   ok(await page.locator('#compareRun').isEnabled(),html+': comparison becomes available with both keys');
   await page.locator('#compareRun').click();
   await page.waitForFunction(()=>document.querySelector('#compareStatus')?.textContent.includes('Comparison complete'));
   ok(await page.locator('#compareJson').isEnabled()&&await page.locator('#compareIndex').isEnabled(),html+': exact and privacy-minimized comparison exports enabled');
   ok(await page.locator('#compareFindingFilter').isEnabled(),html+': findings filters enabled after comparison');
   await page.locator('#reset').click();
   ok(await page.locator('#compareRun').isDisabled(),html+': first-file reset disables comparison');
   ok((await page.locator('#compareFile').inputValue())==='',html+': reset clears sensitive second-file reference');
   ok(errors.length===0,html+': no uncaught JS errors');
   ok(requests.length===0,html+': no remote requests');
   ok((await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth))<=1,html+': 320px horizontal reflow');
   await page.close();
  }
  console.log('PASS: '+n+' Chromium byte-boundary, error-state and export assertions across two review interfaces.');
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(err=>{console.error(err);process.exitCode=1;});
