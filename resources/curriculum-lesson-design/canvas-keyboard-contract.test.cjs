'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'interactive-canvas.html'),'utf8');
let count=0;
for(const id of ['context','objectives','sequence','review']){
 assert.match(source,new RegExp('role="tab"[^>]*id="lc-tab-'+id+'"[^>]*aria-controls="lc-'+id+'"'));count++;
 assert.match(source,new RegExp('role="tabpanel"[^>]*id="lc-'+id+'"[^>]*aria-labelledby="lc-tab-'+id+'"'));count++;
}
for(const key of ['ArrowRight','ArrowLeft','Home','End']){assert.ok(source.includes('event.key==="'+key+'"'));count++;}
for(const token of ['event.preventDefault()','switchTo(tabs[next].dataset.panel)','b.tabIndex=a?0:-1','one("#lc-tab-"+name).focus()','aria-selected','lc-export','lc-save']){assert.ok(source.includes(token),token);count++;}
console.log('PASS: '+count+' curriculum canvas keyboard/export contract assertions.');
