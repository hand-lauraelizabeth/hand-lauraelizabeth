const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const {createServer} = require('node:http');
const {readFile} = require('node:fs/promises');
const {join, extname} = require('node:path');
const root = __dirname;
const types={'.html':'text/html','.mjs':'text/javascript','.css':'text/css'};
const server=createServer(async (req,res)=>{
  const name=decodeURIComponent((req.url||'/').slice(1)||'index.html');
  if(!/^[a-zA-Z0-9.-]+$/.test(name)){res.writeHead(400);res.end();return;}
  try { const body=await readFile(join(root,name));res.writeHead(200,{'Content-Type':types[extname(name)]||'text/plain'});res.end(body); }
  catch {res.writeHead(404);res.end();}
});
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const browser=await chromium.launch();
  try {
    const page=await browser.newPage();
    const response=await page.goto('http://127.0.0.1:'+server.address().port+'/index.html');
    assert.equal(response.status(),200);
    assert.equal(await page.locator('#resume-json').count(),1);
    assert.equal(await page.locator('#csv').isDisabled(),true);
    console.log('PASS: 3 served FT-05 browser checks');
  } finally {await browser.close();server.close();}
})().catch(error=>{console.error(error);process.exitCode=1;server.close();});
