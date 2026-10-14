import assert from 'node:assert/strict';
import {parseWorkspaceJSON,readWorkspaceFile,MAX_IMPORT_BYTES} from './import.mjs';
import {exportJSON} from './core.mjs';
const sample={version:1,requests:[{id:'  R-1  ',jurisdiction:'federal',agency:'Synthetic Agency',stage:'draft',submittedOn:'',agencyTrackingId:'',description:'Example'}],events:[{id:' E-1 ',requestId:'  R-1  ',date:'2024-02-29',kind:'note',sourceId:'  SRC-1  ',description:'Note'}]};
const bytes=new TextEncoder().encode(exportJSON(sample));
const file=(name,contents=bytes,type='application/json',size=contents.byteLength)=>({name,type,size,arrayBuffer:async()=>contents.buffer.slice(contents.byteOffset,contents.byteOffset+contents.byteLength)});
let checks=0;
function equal(a,b){assert.deepEqual(a,b);checks++;}
async function rejects(fn){await assert.rejects(fn);checks++;}
equal(MAX_IMPORT_BYTES,5000000);
equal(parseWorkspaceJSON(exportJSON(sample)),sample);
equal((await readWorkspaceFile(file('records.json'))).requests[0].id,'  R-1  ');
equal((await readWorkspaceFile(file('records.JSON'))).events[0].sourceId,'  SRC-1  ');
await rejects(()=>readWorkspaceFile(file('records.csv')));
await rejects(()=>readWorkspaceFile(file('records.json',bytes,'text/csv')));
await rejects(()=>readWorkspaceFile(file('records.json',bytes,'application/json',5000001)));
await rejects(()=>readWorkspaceFile(file('records.json',new Uint8Array(5000001),'application/json',1)));
await rejects(()=>readWorkspaceFile(file('records.json',new Uint8Array([255,254]))));
await rejects(()=>readWorkspaceFile(file('records.json',new TextEncoder().encode(exportJSON(sample)+'\0'))));
for(const invalid of [
 {...sample,unknown:'x'},
 {...sample,requests:[{...sample.requests[0],unknown:'x'}]},
 {...sample,events:[{...sample.events[0],unknown:'x'}]},
 {...sample,events:[{...sample.events[0],requestId:'other'}]},
 {...sample,requests:[{...sample.requests[0],id:'other'}]},
 {...sample,version:2},
 {...sample,events:[{...sample.events[0],date:'2025-02-29'}]}
])await rejects(async()=>parseWorkspaceJSON(JSON.stringify(invalid)));
const bom=new Uint8Array([239,187,191,...bytes]);
equal((await readWorkspaceFile(file('records.json',bom))).events[0].id,' E-1 ');
equal(parseWorkspaceJSON(exportJSON({...sample,requests:[{...sample.requests[0],description:'=HYPERLINK("x")'}]})).requests[0].description,'=HYPERLINK("x")');
console.log(checks+' FT-09 strict JSON import checks passed');
