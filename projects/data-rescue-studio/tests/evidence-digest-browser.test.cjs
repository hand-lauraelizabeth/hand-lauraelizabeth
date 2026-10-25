'use strict';
// HTTP-served, synthetic-only browser regression: original-byte SHA-256 in downloaded evidence.
const assert=require('node:assert/strict');
const {createServer}=require('node:http');
const {readFileSync}=require('node:fs');
const {join,dirname}=require('node:path');
const {createHash}=require('node:crypto');
const {chromium,firefox,webkit}=require('playwright');
const root=join(__dirname,'..');
const allow=new Map([['/','index.html'],['/index.html','index.html'],['/rescue-core.js','rescue-core.js'],['/file-reader.js','file-reader.js'],['/reconcile-core.js','reconcile-core.js'],['/reconcile-ui.js','reconcile-ui.js']]);
const server=createServer((req,res)=>{
 const path=allow.get(new URL(req.url,'http://localhost').pathname);
 if(!path){res.writeHead(404).end('Not found');return;}
 try{res.writeHead(200,{'Content-Type':path.endsWith('.html')?'text/html; charset=utf-8':'text/javascript; charset=utf-8','Cache-Control':'no-store'});res.end(readFileSync(join(root,path)));}
 catch{res.writeHead(500).end('Asset unavailable');}
});
let checks=0;
const eq=(actual,expected,message)=>{assert.deepEqual(actual,expected,message);checks++;};
const ok=(value,message)=>{assert.ok(value,message);checks++;};
const bytes=Buffer.from('\uFEFFID,ID,Note,Blank\r\n0007,0007,"=1+2",\r\n0007,0007,"=1+2",\r\n0008,0008,"café\nline two",""\r\n','utf8');
const sha256=createHash('sha256').update(bytes).digest('hex');
async function run(name,type,url){
 const browser=await type.launch({headless:true});
 try{
  const page=await browser.newPage({acceptDownloads:true,viewport:{width:1280,height:800}});
  const errors=[],outside=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>{if(!request.url().startsWith(url)&&!request.url().startsWith('blob:'+url))outside.push(request.url());});
  const response=await page.goto(url,{waitUntil:'networkidle'});
  eq(response.status(),200,name+' served HTTP');
  ok(await page.locator('#saveJson').isDisabled(),name+' evidence export initially disabled');
  await page.locator('#file').setInputFiles({name:'synthetic.csv',mimeType:'text/csv',buffer:bytes});
  await page.waitForFunction(()=>document.querySelector('#saveJson')?.disabled===false);
  ok((await page.locator('#status').innerText()).includes('No file was transmitted'),name+' local-only notice');
  await page.locator('#dedupe').check();
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#saveJson').click()]);
  eq(download.suggestedFilename(),'data-rescue-evidence.json',name+' download filename');
  const json=JSON.parse(readFileSync(await download.path(),'utf8'));
  eq(json.source.fileName,'synthetic.csv',name+' original filename');
  eq(json.source.byteCount,bytes.length,name+' original UTF-8 byte count');
  eq(json.source.digestAlgorithm,'SHA-256',name+' digest algorithm');
  eq(json.source.sha256,sha256,name+' downloaded hash equals independent Node oracle');
  eq(json.headers,['ID','ID','Note','Blank'],name+' raw duplicate headers');
  eq(json.records.map(x=>x.sourceRecord),[2,3,4],name+' logical record IDs');
  eq(json.records[0].values,['0007','0007','=1+2',''],name+' exact source strings');
  eq(json.records[1].values,json.records[0].values,name+' dedupe toggle does not alter evidence');
  eq(json.records[2].values[2],'café\nline two',name+' Unicode and multiline');
  ok((await page.locator('#status').innerText()).includes('Original-byte SHA-256 included'),name+' visible fingerprint status');
  await page.locator('#reset').click();
  ok(await page.locator('#saveJson').isDisabled(),name+' reset invalidates evidence');
  await page.locator('#sample').click();
  const [sampleDownload]=await Promise.all([page.waitForEvent('download'),page.locator('#saveJson').click()]);
  const sample=JSON.parse(readFileSync(await sampleDownload.path(),'utf8'));
  ok(!Object.hasOwn(sample.source,'sha256'),name+' synthetic sample never claims original-byte fingerprint');
  await page.locator('#reset').click();
  await page.locator('#file').setInputFiles({name:'broken.csv',mimeType:'text/csv',buffer:Buffer.from([0xff,0xfe])});
  await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('Unable to open file'));
  ok(await page.locator('#saveJson').isDisabled(),name+' malformed UTF-8 cannot export stale evidence');
  await page.setViewportSize({width:320,height:800});
  const width=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  ok(width<=1,name+' 320 CSS-pixel page reflow');
  eq(errors,[],name+' no unhandled browser errors');
  eq(outside,[],name+' no external requests');
  await page.close();
  console.log(name+': passed browser upload/download, byte oracle, reset, invalid-input and 320px checks');
 }finally{await browser.close();}
}
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port+'/';
 try{
  for(const [name,type] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]])await run(name,type,url);
  console.log('PASS: '+checks+' HTTP-served original-byte SHA-256 download assertions (3 engines).');
  console.log('Native assistive technology, actual browser zoom, physical mobile, 5MB responsiveness and spreadsheet-app reopening still pending.');
 }finally{await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
