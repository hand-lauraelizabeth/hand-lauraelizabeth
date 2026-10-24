import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFileSync} from 'node:fs';
import {dirname, join, extname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium, firefox, webkit} from 'playwright';

const here=dirname(fileURLToPath(import.meta.url));
const browserName=process.argv[2]||'chromium';
const engines={chromium,firefox,webkit};
assert.ok(Object.hasOwn(engines,browserName),'supported browser required');
const files=new Set(['index.html','styles.css','app.mjs','housing-core.mjs']);
const mime={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.mjs':'text/javascript; charset=utf-8'};
const server=createServer((req,res)=>{
  const name=decodeURIComponent((req.url||'/').split('?')[0]).replace(/^\//,'')||'index.html';
  if(!files.has(name)){res.writeHead(404);res.end();return;}
  res.writeHead(200,{'Content-Type':mime[extname(name)],'Cache-Control':'no-store'});
  res.end(readFileSync(join(here,name)));
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const url=`http://127.0.0.1:${server.address().port}/`;
let browser; let count=0;
try{
  browser=await engines[browserName].launch({headless:true});
  const page=await browser.newPage({viewport:{width:320,height:700},acceptDownloads:true});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url,{waitUntil:'load'});
  await page.locator('#status').waitFor();
  for(const [width,scale] of [[320,100],[320,200],[375,200],[1280,400],[1280,100]]){
    await page.setViewportSize({width,height:700});
    await page.evaluate(s=>{document.documentElement.style.fontSize=s+'%';},scale);
    const sizes=await page.evaluate(()=>({viewport:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth}));
    if(sizes.scroll>sizes.viewport+1){const offenders=await page.evaluate(()=>[...document.querySelectorAll('*')].filter(el=>el.getBoundingClientRect().right>document.documentElement.clientWidth+1).slice(0,12).map(el=>({tag:el.tagName,id:el.id,cls:el.className,right:Math.round(el.getBoundingClientRect().right),scroll:el.scrollWidth,client:el.clientWidth})));assert.fail(`horizontal overflow at ${width}px/${scale}%: ${JSON.stringify({sizes,offenders})}`);}
    count++;
  }
  await page.setViewportSize({width:320,height:700});
  await page.evaluate(()=>{document.documentElement.style.fontSize='200%';});
  await page.locator('#source-id').fill('000-A/１');
  await page.locator('#source-label').fill('Synthetic receipt');
  await page.locator('#source-form button').click();
  assert.match(await page.locator('#status').innerText(),/1 sources/);count++;
  await page.locator('#source-id').fill('000-A/１');
  await page.locator('#source-form button').click();
  assert.equal(await page.locator('#error').getAttribute('hidden'),null);
  assert.equal(await page.evaluate(()=>document.activeElement.id),'error');count+=2;
  const downloadPromise=page.waitForEvent('download');
  await page.locator('#download').click();
  const download=await downloadPromise;
  assert.equal(download.suggestedFilename(),'housing-evidence-ledger.json');count++;
  const body=readFileSync(await download.path(),'utf8');
  assert.ok(body.includes('000-A/１'),'original Unicode and zero-padded ID retained');count++;
  assert.deepEqual(errors,[],'no JavaScript errors');count++;
  console.log(`PASS: ${count} FT-12 ${browserName} served-browser assertions (320px reflow and 200%/400% text resize are separate CSS tests, not native zoom)`);
  await page.close();
}finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
