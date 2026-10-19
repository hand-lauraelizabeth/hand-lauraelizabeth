import assert from 'node:assert/strict';
import {TOOLS} from './catalog.mjs';
import {validateCatalog,filterTools} from './directory.mjs';
let n=0;const ok=(x)=>{assert.ok(x);n++};
ok(validateCatalog());ok(TOOLS.length===17);ok(TOOLS.filter(t=>t.status==='live').length===6);ok(TOOLS.filter(t=>t.status==='development').length===11);ok(TOOLS.every(t=>t.status!=='development'||!t.url));
for(const t of TOOLS){ok(filterTools(TOOLS,{query:t.title}).some(x=>x.id===t.id));ok(filterTools(TOOLS,{category:t.category}).some(x=>x.id===t.id));}
ok(filterTools(TOOLS,{status:'preview'}).length===0);ok(filterTools(TOOLS,{query:'no-such-resource'}).length===0);ok(filterTools(TOOLS,{query:'  TEXT lens '}).length===1);
for(const mutation of [r=>r.push({...r[0]}),r=>r[0].url='javascript:alert(1)',r=>r[0].status='released',r=>r[6].url='https://example.com',r=>r[0].url='https://example.com']){
 const rows=structuredClone(TOOLS);mutation(rows);assert.throws(()=>validateCatalog(rows));n++;
}
console.log('FT-15 Node catalog assertions PASS:',n);