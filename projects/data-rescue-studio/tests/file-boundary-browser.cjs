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
   const status=async part=>page.waitForFunction(([id,value])=>document.querySelector(id)?.textContent.includes(value),[selector,part]);
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
