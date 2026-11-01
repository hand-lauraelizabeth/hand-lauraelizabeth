import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile, mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve, dirname, extname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium, firefox, webkit} from 'playwright';

// Runs the actual shipped browser UI over loopback HTTP, not a DOM mock.
// All data is synthetic. The HTTP response repeats the page's restrictive CSP.
const root=dirname(fileURLToPath(import.meta.url));
const mime={'.html':'text/html','.mjs':'text/javascript','.css':'text/css','.json':'application/json'};
const csp="default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'";
const server=createServer(async(req,res)=>{
  const url=new URL(req.url,'http://127.0.0.1');
  const path=resolve(root,'.'+decodeURIComponent(url.pathname));
  if(!path.startsWith(root+'/')||!Object.hasOwn(mime,extname(path))){res.writeHead(404);res.end();return;}
  try{const body=await readFile(path);res.writeHead(200,{'content-type':mime[extname(path)]+'; charset=utf-8','content-security-policy':csp,'cache-control':'no-store'});res.end(body);}
  catch{res.writeHead(404);res.end();}
});
await new Promise((ok,fail)=>server.once('error',fail).listen(0,'127.0.0.1',ok));
const port=server.address().port;
const temp=await mkdtemp(join(tmpdir(),'ft07-browser-'));
let assertions=0;
function check(ok,msg){assert.ok(ok,msg);assertions++;}
async function textDownload(page,selector){
  const [download]=await Promise.all([page.waitForEvent('download',{timeout:10000}),page.locator(selector).click()]);
  const file=await download.path();
  return {name:download.suggestedFilename(),text:await readFile(file,'utf8')};
}
try{
  for(const [name,engine] of Object.entries({chromium,firefox,webkit})){
    const browser=await engine.launch({headless:true});
    try{
      const context=await browser.newContext({acceptDownloads:true,viewport:{width:375,height:812}});
      const page=await context.newPage();const failures=[];
      page.on('pageerror',e=>failures.push(e.message));
      page.on('response',r=>{if(r.status()>=400)failures.push('HTTP '+r.status()+' '+r.url());});
      await page.goto('http://127.0.0.1:'+port+'/index.html',{waitUntil:'networkidle'});
      check(await page.locator('#criteria-list .entry').count()===1,name+' initial criterion');
      check(await page.locator('#vendors-list .entry').count()===1,name+' initial vendor');
      await page.locator('#criterion-1-id').fill('C-0001');
      await page.locator('#criterion-1-label').fill('Delivery');
      await page.locator('#criterion-1-weight').fill('100');
      await page.locator('#criterion-1-sourceRef').fill('REQ-0001');
      await page.locator('#criterion-1-mandatory').check();
      await page.locator('#vendor-1-id').fill('V-0007');
      await page.locator('#vendor-1-name').fill('Example\u202E vendor');
      await page.locator('#vendor-1-price').fill('10.00');
      await page.locator('#vendor-1-conflict').selectOption('none');
      await page.locator('#rating-1-vendorId').fill('V-0007');
      await page.locator('#rating-1-criterionId').fill('C-0001');
      await page.locator('#rating-1-score').fill('4');
      await page.locator('#rating-1-evidenceRef').fill('EV-0001');
      await page.locator('#rating-1-reviewer').fill('QA');
      await page.locator('#rating-1-note').fill('Reviewed');
      await page.locator('button[type=submit]').click();
      check(await page.locator('#results-section').isVisible(),name+' evaluated locally');
      check((await page.locator('#result-summary').innerText()).includes('1 of 1 vendor–criterion pairs scored'),name+' scored coverage visible');
      check((await page.locator('#result-summary').innerText()).includes('1 scored pairs have visible evidence and criterion source'),name+' documented coverage visible');
      check((await page.locator('#status').innerText()).includes('1 of 1 vendor–criterion pairs scored'),name+' coverage announced through pre-existing status region');
      check((await page.locator('#status').innerText()).includes('1 scored pairs have visible criterion source, evidence and reviewer identifiers'),name+' combined reference coverage announced');
      check(await page.locator('#criterion-coverage-body tr').count()===1,name+' criterion gap row');
      check((await page.locator('#criterion-coverage-body tr').first().innerText()).includes('C-0001'),name+' exact criterion ID');
      check((await page.locator('#criterion-coverage-body tr').first().locator('td').allTextContents()).join(',')==='1,1,0,0',name+' full criterion reference coverage');
      check(await page.locator('#criterion-coverage-body th[scope=row]').count()===1,name+' semantic criterion row header');
      check(await page.locator('#vendor-coverage-body tr').count()===1,name+' vendor gap row');
      check((await page.locator('#vendor-coverage-body tr').first().locator('th').textContent())==='V-0007',name+' exact vendor ID in row header');
      check((await page.locator('#vendor-coverage-body tr').first().locator('td').allTextContents()).join(',')==='1,1,0,0',name+' complete vendor reference coverage');
      check(await page.locator('#vendor-coverage-body th[scope=row]').count()===1,name+' semantic vendor row header');
      await page.locator('#download-matrix').click();
      check((await page.locator('#error').textContent()).includes('CSV export blocked'),name+' matrix blocked');
      check(await page.evaluate(()=>document.activeElement?.id)==='error',name+' blocked export focuses error');
      await page.locator('#download-coverage').click();
      check((await page.locator('#error').textContent()).includes('CSV export blocked'),name+' provenance blocked');
      const json=await textDownload(page,'#download-json');
      const parsed=JSON.parse(json.text);
      check(json.name==='rfp-evidence.json',name+' JSON downloaded');
      check(parsed.vendors[0].name==='Example\u202E vendor',name+' JSON retains exact unsafe text');
      check(parsed.vendors[0].id==='V-0007'&&parsed.criteria[0].sourceRef==='REQ-0001',name+' exact IDs');

      // Browser-level fault injection: failed downloads must preserve local results,
      // focus the text alert, clean resources and allow byte-identical retry.
      await page.evaluate(()=>{window.__ft07Create=URL.createObjectURL;URL.createObjectURL=()=>{throw Error('PRIVATE TEST PATH');};});
      await page.locator('#download-json').click();
      check((await page.locator('#error').innerText()).includes('browser could not start this download'),name+' blocked object URL has actionable error');
      check(!(await page.locator('#error').innerText()).includes('PRIVATE TEST PATH'),name+' browser exception redacted');
      check(await page.evaluate(()=>document.activeElement?.id)==='error',name+' blocked object URL focuses error');
      check(await page.locator('#results-section').isVisible(),name+' failed URL retains results');
      check(await page.locator('a[download]').count()===0,name+' failed URL leaves no link');
      await page.evaluate(()=>{URL.createObjectURL=window.__ft07Create;});
      await page.evaluate(()=>{
        window.__ft07Click=HTMLAnchorElement.prototype.click;
        window.__ft07Revoke=URL.revokeObjectURL;
        window.__ft07Revoked=[];
        URL.revokeObjectURL=function(url){window.__ft07Revoked.push(url);return window.__ft07Revoke.call(URL,url);};
        HTMLAnchorElement.prototype.click=function(){if(this.hasAttribute('download'))throw Error('PRIVATE CLICK PATH');return window.__ft07Click.call(this);};
      });
      await page.locator('#download-coverage').click();
      check((await page.locator('#error').innerText()).includes('browser could not start this download'),name+' blocked link has actionable error');
      check(!(await page.locator('#error').innerText()).includes('PRIVATE CLICK PATH'),name+' click exception redacted');
      check(await page.evaluate(()=>document.activeElement?.id)==='error',name+' blocked link focuses error');
      check(await page.locator('a[download]').count()===0,name+' blocked link cleaned');
      check(await page.evaluate(()=>window.__ft07Revoked.length)===1,name+' failed blob URL revoked');
      check(await page.locator('#results-section').isVisible(),name+' failed click retains results');
      await page.evaluate(()=>{HTMLAnchorElement.prototype.click=window.__ft07Click;URL.revokeObjectURL=window.__ft07Revoke;});
      const recovered=await textDownload(page,'#download-json');
      check(recovered.text===json.text,name+' retry exact JSON bytes preserved');
      check((await page.locator('#status').innerText()).includes('download started locally'),name+' status does not assert file saved');

      await page.locator('#vendor-1-name').fill('Café 供應商');
      await page.locator('button[type=submit]').click();
      const safe=await textDownload(page,'#download-matrix');
      check(safe.text.includes('"V-0007"')&&safe.text.includes('Café 供應商'),name+' safe CSV recovery');
      await page.locator('#rating-1-note').fill('Reviewed\u2066 note');
      await page.locator('button[type=submit]').click();
      await page.locator('#download-evidence').click();
      check((await page.locator('#error').textContent()).includes('CSV export blocked'),name+' rating CSV blocked');
      await page.locator('#rating-1-note').fill('Reviewed note');
      await page.locator('button[type=submit]').click();
      const rating=await textDownload(page,'#download-evidence');
      check(rating.text.includes('"EV-0001"'),name+' safe ratings CSV recovery');
      const coverage=await textDownload(page,'#download-coverage');
      check(coverage.text.includes('"REQ-0001"'),name+' safe coverage CSV recovery');
      // Missing reviewer attribution is visible and included in the exported audit,
      // without changing the numeric score or discarding exact evidence.
      await page.locator('#rating-1-reviewer').fill('');
      await page.locator('button[type=submit]').click();
      check((await page.locator('#result-summary').innerText()).includes('1 scored pairs missing a visible reviewer identifier'),name+' reviewer coverage disclosed');
      check((await page.locator('#criterion-coverage-body tr').first().locator('td').allTextContents()).join(',')==='1,0,0,1',name+' criterion gap reflects reviewer omission');
      check((await page.locator('#vendor-coverage-body tr').first().locator('td').allTextContents()).join(',')==='1,0,0,1',name+' vendor gap reflects reviewer omission');
      check((await page.locator('#result-summary').innerText()).includes('0 scored pairs have visible criterion source, evidence and reviewer identifiers'),name+' missing reviewer lowers combined reference coverage');
      check((await page.locator('#result-summary').innerText()).includes('1 scored pairs missing at least one of those references'),name+' combined gap visible');
      check((await page.locator('#result-body').innerText()).includes('Reviewer identifier missing: C-0001'),name+' unattributed score flagged');
      check((await page.locator('#result-body').innerText()).includes('80.0%'),name+' reviewer omission does not invent or withhold numeric score');
      const unattributed=await textDownload(page,'#download-coverage');
      check(unattributed.text.includes('Reviewer identifier missing'),name+' reviewer omission appears in audit CSV');
      await page.locator('#rating-1-reviewer').fill('QA');
      await page.locator('button[type=submit]').click();
      check(!(await page.locator('#result-summary').innerText()).includes('1 scored pairs missing a visible reviewer identifier'),name+' reviewer recovery updates counts');
      check((await page.locator('#result-summary').innerText()).includes('1 scored pairs have visible criterion source, evidence and reviewer identifiers'),name+' combined reference coverage recovers');
      // Coverage must never treat missing source/evidence as documented or missing score as zero.
      await page.locator('#criterion-1-sourceRef').fill('');
      await page.locator('button[type=submit]').click();
      check((await page.locator('#result-summary').innerText()).includes('0 scored pairs missing evidence or source')===false,name+' missing source reduces documented coverage');
      check((await page.locator('#result-summary').innerText()).includes('1 scored pairs missing evidence or source'),name+' missing source count');
      check((await page.locator('#result-body').innerText()).includes('Incomplete'),name+' missing source withholds score');
      await page.locator('#criterion-1-sourceRef').fill('REQ-0001');
      await page.locator('#rating-1-score').fill('');
      await page.locator('button[type=submit]').click();
      check((await page.locator('#result-summary').innerText()).includes('0 of 1 vendor–criterion pairs scored'),name+' missing score not treated as zero');
      check((await page.locator('#result-summary').innerText()).includes('1 missing scores'),name+' missing score explicitly counted');
      check((await page.locator('#vendor-coverage-body tr').first().locator('td').allTextContents()).join(',')==='0,0,1,0',name+' vendor gap distinguishes missing score');
      await page.locator('#rating-1-score').fill('4');
      await page.locator('button[type=submit]').click();
      // Removing an entry is destructive: keyboard cancellation must preserve the
      // current evaluated workspace, while confirmation must invalidate exports.
      for(const [kind,list] of [['criterion','criteria-list'],['vendor','vendors-list'],['rating','ratings-list']]){
        const row=page.locator('#'+list+' .entry').first();
        const remove=row.locator('[data-remove]');
        const before=await page.locator('#'+list+' .entry').count();
        let prompt='';
        page.once('dialog',async dialog=>{prompt=dialog.message();await dialog.dismiss();});
        await remove.focus();await remove.press('Enter');
        check(prompt.includes('Remove this '+kind+' entry'),name+' '+kind+' native confirmation shown');
        check(!prompt.includes('C-0001')&&!prompt.includes('V-0007'),name+' '+kind+' prompt does not disclose source IDs');
        check(await page.locator('#'+list+' .entry').count()===before,name+' '+kind+' cancellation retains entry');
        if(kind==='criterion'){
          check(await page.locator('#results-section').isVisible(),name+' cancellation preserves evaluated results');
          const unchanged=JSON.parse((await textDownload(page,'#download-json')).text);
          check(unchanged.criteria[0].id==='C-0001'&&unchanged.vendors[0].id==='V-0007',name+' cancellation preserves exact JSON');
        }
        page.once('dialog',dialog=>dialog.accept());
        await remove.focus();await remove.press('Enter');
        check(await page.locator('#'+list+' .entry').count()===before-1,name+' '+kind+' confirmation removes one entry');
        check(await page.locator('#results-section').isHidden(),name+' '+kind+' removal invalidates previous results');
        check(await page.evaluate(()=>document.activeElement?.id)==='add-'+kind,name+' '+kind+' removal restores keyboard focus');
      }
      check(failures.length===0,name+' no HTTP failures or uncaught browser errors: '+failures.join(' | '));
      await context.close();
      console.log('PASS '+name+' HTTP/CSP/unsafe CSV/JSON fidelity/recovery/focus');
    }finally{await browser.close();}
  }
  console.log('PASS '+assertions+' cross-browser assertions (synthetic only)');
}finally{
  await new Promise(resolve=>server.close(resolve));
  await rm(temp,{recursive:true,force:true});
}
