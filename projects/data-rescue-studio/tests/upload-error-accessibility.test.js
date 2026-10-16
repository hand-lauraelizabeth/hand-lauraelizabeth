'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const rescue=require('../rescue-core.js');
class Element {
 constructor(){this.value='';this.files=[];this.disabled=true;this.options=[];this.handlers={};this.attrs={};this.textContent='';this.focused=false;}
 addEventListener(type,handler){this.handlers[type]=handler;}
 replaceChildren(...children){this.options=children;this.value='';}
 append(...children){this.options.push(...children);}
 setAttribute(name,value){this.attrs[name]=value;}
 focus(){this.focused=true;}
}
const ids=['compareFile','compareStatus','compareMetrics','compareResults','compareExport','compareRun','compareClear','leftKey','rightKey'];
const elements=Object.fromEntries(ids.map(id=>[id,new Element()]));
const win={DataRescue:rescue,DataReconcile:require('../reconcile-core.js'),DataRescueFileReader:{read:async(file,parse)=>parse(await file.text())}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'..','reconcile-ui.js'),'utf8'),{
 window:win,document:{getElementById:id=>elements[id],createElement:()=>new Element()}
});
const input=elements.compareFile,status=elements.compareStatus;
let checks=0;
function check(condition,message){assert.ok(condition,message);checks++;}
(async()=>{
 const first=rescue.parseDelimited('ID,Name\n1,Ada');
 win.DataRescueCompareUI.setPrimary(first,'one.csv');
 check(input.attrs['aria-describedby']==='compareStatus','status associated with upload input');
 check(input.attrs['aria-invalid']==='false','no false error state on initialization');
 input.files=[{name:'unsafe.exe',size:4,text:async()=>{throw Error('should not read')}}];
 await input.handlers.change();
 check(input.attrs['aria-invalid']==='true','invalid extension exposed to AT');
 check(status.tabIndex===-1,'error summary programmatically focusable');
 check(status.focused,'error receives focus');
 check(status.textContent.includes('.csv or .tsv'),'specific correction displayed');
 check(elements.compareExport.disabled,'error cannot expose export');
 status.focused=false;
 input.files=[{name:'good.csv',size:12,text:async()=> 'ID,Name\n1,Bea'}];
 await input.handlers.change();
 check(input.attrs['aria-invalid']==='false','valid input clears invalid state');
 check(!status.focused,'success does not steal focus');
 check(!elements.rightKey.disabled,'successful load enables identifier choice');
 input.files=[{name:'bad.csv',size:20,text:async()=>{throw Error('Invalid UTF-8 text')}}];
 await input.handlers.change();
 check(input.attrs['aria-invalid']==='true','read error exposed');
 check(status.focused,'read error receives focus');
 check(elements.rightKey.disabled && elements.compareExport.disabled,'read error disables stale results');
 elements.compareClear.handlers.click();
 check(input.attrs['aria-invalid']==='false','clear resets error state');
 let rejectOld;
 input.files=[{name:'slow.csv',size:10,text:()=>new Promise((resolve,reject)=>{rejectOld=reject})}];
 const pending=input.handlers.change();
 elements.compareClear.handlers.click();
 status.focused=false;
 rejectOld(Error('stale read failure'));
 await pending;
 check(!status.focused,'stale async failure cannot move focus');
 check(input.attrs['aria-invalid']==='false','stale async failure cannot set invalid state');
 console.log('PASS: '+checks+' accessible reconciliation upload behavior checks.');
})().catch(err=>{console.error(err);process.exitCode=1});
