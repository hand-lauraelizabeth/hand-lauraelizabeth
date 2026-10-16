const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
class E{
 constructor(){this.value='';this.files=[];this.disabled=true;this.options=[];this.handlers={};this.textContent='';}
 addEventListener(k,v){this.handlers[k]=v}
 replaceChildren(...v){this.options=v;this.value=''}
 append(...v){this.options.push(...v)}
}
const ids=['compareFile','compareStatus','compareMetrics','compareResults','compareExport','compareRun','compareClear','leftKey','rightKey'];
const nodes=Object.fromEntries(ids.map(id=>[id,new E()]));
const win={DataRescue:{MAX_BYTES:5000000,parseDelimited(){throw Error('unexpected parse')}}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'..','reconcile-ui.js'),'utf8'),{
 window:win,document:{getElementById:id=>nodes[id],createElement:()=>new E()}
});
(async()=>{
 let reads=0;
 nodes.compareFile.files=[{name:'untrusted.csv',size:8,text:async()=>{reads++;return 'ID,Name'}}];
 await nodes.compareFile.handlers.change();
 assert.equal(reads,0);
 assert.match(nodes.compareStatus.textContent,/Strict local file reader is unavailable/);
 assert.equal(nodes.compareStatus.className,'error');
 assert.equal(nodes.rightKey.disabled,true);
 assert.equal(nodes.compareRun.disabled,true);
 assert.equal(nodes.compareExport.disabled,true);
 console.log('PASS: 6 missing-reader UI regression checks.');
})().catch(e=>{console.error(e);process.exitCode=1});
