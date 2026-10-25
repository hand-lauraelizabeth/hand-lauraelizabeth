import assert from 'node:assert/strict';
import {buildHousingLedger, exportHousingJSON} from './housing-core.mjs';
import {parseHousingJSON, readHousingJSONFile} from './housing-import.mjs';

const source={sourceId:'000-Δ/１',kind:'receipt',label:'Synthetic <img src=x onerror=alert(1)>',date:'2026-10-01'};
const event={eventId:'000-E/ß',date:'2026-10-02',category:'deposit',description:'Synthetic note\r\n=1+1',sourceIds:[source.sourceId],amountCents:null};
const ledger=buildHousingLedger({sources:[source],events:[event]});
const original=exportHousingJSON(ledger);
const enc=new TextEncoder();
const mock=(bytes,{name='evidence.json',size=bytes.length,read=bytes}={})=>({
  name,size,async arrayBuffer(){return read.buffer.slice(read.byteOffset,read.byteOffset+read.byteLength);}
});
let count=0;
const check=(fn)=>{fn();count++;};
const reject=async (f,label)=>{await assert.rejects(f,undefined,label);count++;};
check(()=>assert.deepEqual(parseHousingJSON(original),ledger));
check(()=>assert.equal(parseHousingJSON(original).sources[0].sourceId,'000-Δ/１'));
check(()=>assert.equal(parseHousingJSON(original).events[0].description,'Synthetic note\r\n=1+1'));
check(()=>assert.equal(exportHousingJSON(parseHousingJSON(original)),original));
const valid=enc.encode(original);
check(()=>assert.ok(valid.byteLength>0));
check(()=>assert.equal(valid.length,Buffer.byteLength(original,'utf8')));
const cases=[
 ['empty', ''],
 ['not-json','{'],
 ['wrong-schema',JSON.stringify({...ledger,schema:'other-v2'})],
 ['extra-root',JSON.stringify({...ledger,unrecognized:'data'})],
 ['extra-source',JSON.stringify({...ledger,sources:[{...source,unexpected:'data'}]})],
 ['extra-event',JSON.stringify({...ledger,events:[{...ledger.events[0],unexpected:'data'}]})],
 ['missing-source',JSON.stringify({...ledger,sources:[]})],
 ['wrong-findings',JSON.stringify({...ledger,findings:[]})],
 ['wrong-disclaimer',JSON.stringify({...ledger,disclaimer:'Incorrect'})],
 ['unsafe-source-id',JSON.stringify({...ledger,sources:[{...source,sourceId:'bad\u0000'}]})],
 ['duplicate-source',JSON.stringify({...ledger,sources:[source,source]})],
 ['invalid-calendar',JSON.stringify({...ledger,events:[{...ledger.events[0],date:'2026-02-30'}]})],
 ['unknown-source-link',JSON.stringify({...ledger,events:[{...ledger.events[0],sourceIds:['missing']}]})],
 ['fractional-cents',JSON.stringify({...ledger,events:[{...ledger.events[0],amountCents:0.5}]})],
];
for(const [label,text] of cases)check(()=>assert.throws(()=>parseHousingJSON(text),undefined,label));
await reject(()=>readHousingJSONFile(null),'missing file');
await reject(()=>readHousingJSONFile(mock(valid,{name:'evidence.csv'})),'wrong extension');
await reject(()=>readHousingJSONFile(mock(valid,{size:valid.length+1})),'partial read');
await reject(()=>readHousingJSONFile(mock(valid,{size:valid.length-1})),'oversized read');
await reject(()=>readHousingJSONFile(mock(valid,{size:0})),'empty metadata');
await reject(()=>readHousingJSONFile(mock(valid,{size:5_000_001})),'large metadata');
await reject(()=>readHousingJSONFile(mock(valid,{size:NaN})),'invalid metadata');
await reject(()=>readHousingJSONFile(mock(new Uint8Array([0xc3,0x28]))),'invalid UTF8');
await reject(()=>readHousingJSONFile({name:'x.json',size:1,arrayBuffer:async()=>new Uint8Array([123])}),'non-ArrayBuffer');
const imported=await readHousingJSONFile(mock(valid));
check(()=>assert.deepEqual(imported,ledger));
const withBom=new Uint8Array([0xef,0xbb,0xbf,...valid]);
const bomImported=await readHousingJSONFile(mock(withBom));
check(()=>assert.deepEqual(bomImported,ledger));
for(let seed=0;seed<200;seed++){
  const id='000-'+seed+'-é';
  const scenario=buildHousingLedger({sources:[{...source,sourceId:id}],events:[{...event,eventId:'E-'+seed,sourceIds:[id],amountCents:seed}]});
  const roundtrip=await readHousingJSONFile(mock(enc.encode(exportHousingJSON(scenario))));
  check(()=>assert.equal(roundtrip.events[0].sourceIds[0],id));
  check(()=>assert.equal(roundtrip.events[0].amountCents,seed));
  check(()=>assert.equal(exportHousingJSON(roundtrip),exportHousingJSON(scenario)));
}
console.log('PASS: '+count+' FT-12 strict JSON reopen assertions');
