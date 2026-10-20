/** FT-07 local JSON reopen. Files never leave this browser. */
import {evaluateWithProvenance} from './evidence-coverage.mjs';
export const MAX_IMPORT_BYTES=5_000_000;
export function decodeWorkspaceBytes(bytes){
 if(!(bytes instanceof Uint8Array))throw Error('Choose a JSON file to reopen.');
 if(!bytes.byteLength||bytes.byteLength>MAX_IMPORT_BYTES)throw Error('JSON file must be between 1 byte and 5,000,000 bytes.');
 let raw;
 try{raw=new TextDecoder('utf-8',{fatal:true}).decode(bytes)}catch{throw Error('File is not valid UTF-8 JSON.');}
 if(raw.charCodeAt(0)===0xFEFF)raw=raw.slice(1);
 if(raw.includes('\0'))throw Error('File contains a NUL character.');
 let obj;try{obj=JSON.parse(raw)}catch{throw Error('File does not contain valid JSON.');}
 if(!obj||typeof obj!=='object'||Array.isArray(obj)||obj.schema!=='rfp-evaluation-v1')throw Error('Unsupported RFP workspace version.');
 // Recompute derived comparisons; do not trust serialized results or declarations.
 if(!Array.isArray(obj.vendors))throw Error('Invalid vendor records.');
 const vendors=obj.vendors.map(v=>{
  if(!v||typeof v!=='object')throw Error('Invalid vendor record.');
  const cents=v.priceCents;
  if(cents!==null&&(!Number.isSafeInteger(cents)||cents<0||cents>999999999999))throw Error('Invalid saved price cents.');
  return {id:v.id,name:v.name,conflict:v.conflict,price:cents===null?'':(cents/100).toFixed(2)};
 });
 const result=evaluateWithProvenance({criteria:obj.criteria,vendors,ratings:obj.ratings});
 return {criteria:result.criteria.map(c=>({...c,weight:String(c.weight)})),vendors:result.vendors.map(v=>({id:v.id,name:v.name,conflict:v.conflict,price:v.priceCents===null?'':(v.priceCents/100).toFixed(2)})),ratings:result.ratings.map(r=>({...r,score:r.score===null?'':String(r.score)}))};
}
export async function readWorkspaceFile(file){
 if(!file||typeof file.arrayBuffer!=='function')throw Error('Choose a JSON file to reopen.');
 // The accept attribute is advisory: validate the filename and declared type too.
 if(typeof file.name!=='string'||!/\.json$/i.test(file.name))throw Error('Choose a file with a .json extension.');
 if(file.type&&!['application/json','text/json','application/octet-stream'].includes(file.type.toLowerCase()))throw Error('File type is not JSON.');
 if(!Number.isSafeInteger(file.size)||file.size<1||file.size>MAX_IMPORT_BYTES)throw Error('JSON file must be between 1 byte and 5,000,000 bytes.');
 const buffer=await file.arrayBuffer();
 if(!(buffer instanceof ArrayBuffer)||buffer.byteLength!==file.size)throw Error('File size changed while reading. Re-select the JSON file.');
 return decodeWorkspaceBytes(new Uint8Array(buffer));
}
