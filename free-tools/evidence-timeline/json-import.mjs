import {normalizeExact} from './exact-core.mjs';
export const SCHEMA='evidence-timeline-v1';
export const MAX_BYTES=5000000;
const fields=['sourceId','date','claim','status','kind','group'];
export function parseExactJSON(raw) {
  if(typeof raw!=='string') throw Error('Expected JSON text');
  let data;
  try { data=JSON.parse(raw.replace(/^\uFEFF/,'')); }
  catch { throw Error('Invalid JSON syntax'); }
  if(!data||typeof data!=='object'||Array.isArray(data)||data.schema!==SCHEMA||!Array.isArray(data.records)) throw Error('Unexpected evidence JSON schema');
  if(Object.keys(data).some(k=>k!=='schema'&&k!=='records')) throw Error('Unexpected top-level field');
  for(const [i,r] of data.records.entries()){
    if(!r||typeof r!=='object'||Array.isArray(r)||fields.some(k=>!Object.hasOwn(r,k))||Object.keys(r).some(k=>!fields.includes(k))) throw Error('Invalid fields in record '+(i+1));
    if(fields.some(k=>typeof r[k]!=='string')) throw Error('Non-text field in record '+(i+1));
  }
  return normalizeExact(data.records);
}
export async function readExactJSON(file){
  if(!file||!/\.json$/i.test(file.name||'')) throw Error('Choose a JSON export');
  if(file.size>MAX_BYTES) throw Error('File exceeds 5000000 bytes');
  const bytes=await file.arrayBuffer();
  if(bytes.byteLength>MAX_BYTES) throw Error('File exceeds 5000000 bytes');
  let value;
  try { value=new TextDecoder('utf-8',{fatal:true}).decode(bytes); }
  catch { throw Error('Invalid UTF-8'); }
  if(value.includes('\u0000')) throw Error('NUL byte is not accepted');
  return parseExactJSON(value);
}
