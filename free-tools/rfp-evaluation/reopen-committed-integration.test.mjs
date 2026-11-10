import assert from 'node:assert/strict';
import {readWorkspaceFile, decodeWorkspaceBytes, MAX_IMPORT_BYTES} from './reopen.mjs';
import {evaluateMatrix, exportMatrixJSON} from './core.mjs';

// Synthetic identifiers only. No uploaded procurement records or network calls.
const input={
 criteria:[{id:'C-001',label:'Documentation',weight:100,mandatory:true,sourceRef:'RFP-001'}],
 vendors:[{id:'0007',name:'Example vendor',conflict:'none',price:'0.01'}],
 ratings:[{vendorId:'0007',criterionId:'C-001',score:5,evidenceRef:'DOC-001',reviewer:'Reviewer A'}]
};
const saved=evaluateMatrix(input);
const encode=value=>new TextEncoder().encode(typeof value==='string'?value:JSON.stringify(value));
const bytes=encode(exportMatrixJSON(saved));
const file=(size=bytes.byteLength,buffer=bytes.buffer,name='workspace.JSON',type='application/json')=>({name,type,size,arrayBuffer:async()=>buffer});
let assertions=0;
const eq=(a,b)=>{assert.deepEqual(a,b);assertions++};
const rejects=async (f,re)=>{await assert.rejects(f,re);assertions++};
const throws=(f,re)=>{assert.throws(f,re);assertions++};
const reopened=await readWorkspaceFile(file());
eq(reopened.vendors[0].id,'0007');
eq(reopened.vendors[0].price,'0.01');
eq(reopened.ratings[0].evidenceRef,'DOC-001');
eq(reopened.criteria[0].sourceRef,'RFP-001');
eq(reopened.criteria[0].mandatory,true);
eq(MAX_IMPORT_BYTES,5_000_000);
for(const size of [bytes.byteLength-1,bytes.byteLength+1,NaN,Infinity,-1,0,1.5,'200',5_000_001])
 await rejects(()=>readWorkspaceFile(file(size)),/size changed|between 1 byte/);
await rejects(()=>readWorkspaceFile(file(bytes.byteLength,new Uint8Array(bytes))),/size changed/);
for(const name of ['workspace.csv','workspace.json.exe'])
 await rejects(()=>readWorkspaceFile(file(bytes.byteLength,bytes.buffer,name)),/\.json extension/);
await rejects(()=>readWorkspaceFile(file(bytes.byteLength,bytes.buffer,'workspace.json','text/csv')),/type is not JSON/);
await rejects(()=>readWorkspaceFile({name:'workspace.json',type:'application/json',size:2,arrayBuffer:async()=>new ArrayBuffer(1)}),/size changed/);
const malicious={...saved,comparisons:[{vendorId:'0007',scorePercent:999}],disclaimer:'Approved award'};
const decoded=decodeWorkspaceBytes(encode(malicious));
eq(Object.hasOwn(decoded,'comparisons'),false);
eq(Object.hasOwn(decoded,'disclaimer'),false);
eq(decoded.ratings[0].evidenceRef,'DOC-001');
const duplicate={...saved,vendors:[saved.vendors[0],saved.vendors[0]]};
throws(()=>decodeWorkspaceBytes(encode(duplicate)),/Duplicate vendor ID/);
const missing={...saved,ratings:[{...saved.ratings[0],criterionId:'MISSING'}]};
throws(()=>decodeWorkspaceBytes(encode(missing)),/Unknown rating reference/);
const wrongVersion={...saved,schema:'unsupported'};
throws(()=>decodeWorkspaceBytes(encode(wrongVersion)),/Unsupported RFP workspace version/);
throws(()=>decodeWorkspaceBytes(new Uint8Array([0xff])),/UTF-8/);
throws(()=>decodeWorkspaceBytes(encode('{invalid')),/valid JSON/);
throws(()=>decodeWorkspaceBytes(encode(JSON.stringify(saved)+'\0')),/NUL/);
const withBOM=new Uint8Array([0xef,0xbb,0xbf,...bytes]);
eq(decodeWorkspaceBytes(withBOM).vendors[0].id,'0007');
console.log(`FT-07 committed JSON integration: ${assertions}/${assertions} assertions PASS`);
