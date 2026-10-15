const {chromium}=require("playwright");
const axe=require("axe-core");
const {join}=require("node:path");
const {pathToFileURL}=require("node:url");
const file=pathToFileURL(join(__dirname,"..","syllabus-assessment-builder.html")).href;
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const [name,width] of [["desktop",1280],["narrow-mobile",320]]){
   const context=await browser.newContext({viewport:{width,height:800}});
   const page=await context.newPage();
   await page.goto(file,{waitUntil:"load"});
   await page.addScriptTag({content:axe.source});
   for(const stage of ["empty","sample"]){
    if(stage==="sample"){page.once("dialog",d=>d.accept());await page.locator("#sy-sample").click();}
    const r=await page.evaluate(async()=>await axe.run(document,{
      runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21a","wcag21aa","wcag22aa"]}
    }));
    const problems=r.violations.map(x=>({id:x.id,impact:x.impact,description:x.help,
      nodes:x.nodes.map(n=>({selector:n.target,failure:n.failureSummary})).slice(0,5)}));
    if(problems.length){console.error("AXE FAIL",name,stage,JSON.stringify(problems,null,2));process.exitCode=1;}
    else console.log("AXE PASS",name,stage,"rules passed="+r.passes.length,"incomplete="+r.incomplete.length);
   }
   await context.close();
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
