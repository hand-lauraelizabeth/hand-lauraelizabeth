// Browser-level regression tests for the local-first Syllabus & Assessment Alignment Builder.
// Run: npm install --no-save playwright@1.56.1 && npx playwright install chromium && node resources/curriculum-lesson-design/tests/syllabus-browser.cjs
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const { join } = require("node:path");
const { pathToFileURL } = require("node:url");
const { readFileSync } = require("node:fs");
const url = pathToFileURL(join(__dirname,"..","syllabus-assessment-builder.html")).href;
let checks=0;
function check(b,m){assert.ok(b,m);checks++}
async function sample(page){
 page.once("dialog", d=>d.accept());
 await page.locator("#sy-sample").click();
 check((await page.locator("#sy-objective-list .item").count())===2,"sample objective count");
 check((await page.locator("#sy-session-list .item").count())===3,"sample session count");
 check((await page.locator("#sy-assessment-list .item").count())===2,"sample assessment count");
 check((await page.locator("#sy-matrix tr").count())===2,"sample matrix count");
}
async function run(){
 const browser=await chromium.launch({headless:true});
 let failed=[];
 try{
 for(const view of [
  {width:1280,height:800,name:"desktop"},{width:390,height:844,name:"mobile"},
  {width:320,height:700,name:"narrow"},{width:640,height:720,name:"200-percent-simulated-zoom"}]){
  const context=await browser.newContext({viewport:{width:view.width,height:view.height},acceptDownloads:true});
  const page=await context.newPage();
  const jsErrors=[],requests=[];
  page.on("pageerror",e=>jsErrors.push(String(e)));
  page.on("request",r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});
  await page.goto(url,{waitUntil:"load"});
  check((await page.locator("h1").textContent()).includes("Syllabus"),view.name+" heading");
  check((await page.locator("#sy-status").getAttribute("role"))==="status",view.name+" status region");
  check((await page.locator("#sy-objective-text").getAttribute("required"))!==null,view.name+" objective required");
  await sample(page);
  check((await page.locator("#sy-flags").innerText()).includes("Accessibility"),view.name+" unverified policies flagged");
  const noOverflow=await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2);
  check(noOverflow,view.name+" no horizontal document overflow");
  check(jsErrors.length===0,view.name+" no JS errors: "+jsErrors);
  check(requests.length===0,view.name+" no outbound network calls: "+requests);
  await context.close();
 }
 // A full editable-workflow test on desktop.
 const context=await browser.newContext({viewport:{width:1240,height:850},acceptDownloads:true});
 const page=await context.newPage();
 await page.goto(url,{waitUntil:"load"});
 await sample(page);
 let item=page.locator("#sy-assessment-list .item").last();
 await item.getByRole("button",{name:"Edit"}).click();
 await page.locator("#sy-assessment-weight").fill("80");
 await page.locator("#sy-assessment-submit").click();
 check((await page.locator("#sy-flags").innerText()).includes("80%"),"grade total warning");
 await page.locator("#sy-session-list .item").last().getByRole("button",{name:"Edit"}).click();
 await page.locator("#sy-session-week").fill("Week 2");
 await page.locator("#sy-session-submit").click();
 check((await page.locator("#sy-flags").innerText()).includes("Week 2 has 5"),"workload aggregation warning");
 // Export should contain live edited data.
 const wait=page.waitForEvent("download");
 await page.locator("#sy-export-json").click();
 const download=await wait, location=await download.path();
 const exported=JSON.parse(readFileSync(location,"utf8"));
 check(exported.kind==="leh-syllabus-studio","JSON format");
 check(exported.assessments.some(a=>a.weight===80),"export includes edited grade");
 check(exported.sessions.some(s=>s.week==="Week 2"),"export includes edited sessions");
 // Reimport same exported plan; local only.
 page.once("dialog",d=>d.accept());
 await page.locator("#sy-import").setInputFiles({name:"syllabus.json",mimeType:"application/json",buffer:Buffer.from(JSON.stringify(exported))});
 await page.waitForFunction(()=>document.querySelector("#sy-status").textContent.includes("imported"));
 check((await page.locator("#sy-objective-list .item").count())===2,"roundtrip objectives");
 check((await page.locator("#sy-session-list .item").count())===3,"roundtrip sessions");
 // Cross-tool Canvas version-1 import from synthetic fixture.
 const canvas={format:"leh-curriculum-canvas",version:1,
 fields:{title:"Synthetic ESOL",audience:"Adults learning email communication",task:"Compose email",format:"Live",
 access:"Plain-text materials",feedback:"Instructor response"},
 objectives:[{sentence:"Learners will compose a clear request."}],
 modules:[{name:"Email practice",target:"1",activity:"Draft a message",evidence:"Revised email"}]};
 page.once("dialog",d=>d.accept());
 await page.locator("#sy-import").setInputFiles({name:"curriculum.json",mimeType:"application/json",buffer:Buffer.from(JSON.stringify(canvas))});
 await page.waitForFunction(()=>document.querySelector("#sy-status").textContent.includes("imported"));
 check((await page.locator("#sy-objective-list .item").count())===1,"Canvas objective import");
 check((await page.locator("#sy-assessment-list .item").count())===1,"Canvas evidence import");
 check((await page.locator("#sy-assessment-list .item").innerText()).includes("Formative"),"Canvas evidence remains ungraded");
 check((await page.locator("#sy-flags").innerText()).includes("No graded assessments"),"ungraded design needs human decision");
 // Invalid import should preserve the good working plan.
 await page.locator("#sy-import").setInputFiles({name:"bad.json",mimeType:"application/json",buffer:Buffer.from('{"kind":"bad"}')});
 await page.waitForFunction(()=>document.querySelector("#sy-status").textContent.includes("Import rejected"));
 check((await page.locator("#sy-objective-list .item").count())===1,"invalid import does not mutate plan");
 // Form create, map, edit, remove.
 await page.locator("#sy-objective-text").fill("Learners will compare email openings.");
 await page.locator("#sy-objective-submit").click();
 check((await page.locator("#sy-objective-list .item").count())===2,"add objective");
 await page.locator("#sy-objective-list .item").last().getByRole("button",{name:"Edit"}).click();
 await page.locator("#sy-objective-text").fill("Learners will revise email openings.");
 await page.locator("#sy-objective-submit").click();
 check((await page.locator("#sy-objective-list").innerText()).includes("revise email"),"edit objective");
 page.once("dialog",d=>d.accept());
 await page.locator("#sy-objective-list .item").last().getByRole("button",{name:"Remove"}).click();
 check((await page.locator("#sy-objective-list .item").count())===1,"remove objective");
 await context.close();
 console.log("Syllabus browser regression PASS, checks="+checks);
 }finally{await browser.close()}
}
run().catch(e=>{console.error(e);process.exitCode=1});