// Local, editable cash-flow inputs; distinct from the calculated evidence export.
// No network, persistence, bank access, or financial determination.
import {dateUTC,project,LIMITS} from './engine.mjs';
export const PLAN_SCHEMA='cash-flow-plan/v1';
export const MAX_PLAN_BYTES=256000;
const exactKeys=(obj,keys)=>obj!==null&&typeof obj==='object'&&!Array.isArray(obj)&&
  Object.keys(obj).sort().join('|')===keys.slice().sort().join('|');
const rootKeys=['schema','start','end','openingCents','events','shiftId','shiftDays'];
const eventKeys=['id','label','date','repeat','cents'];
export function validatePlan(value){
  if(!exactKeys(value,rootKeys)||value.schema!==PLAN_SCHEMA)throw Error('Unsupported plan format or fields.');
  if(typeof value.start!=='string'||typeof value.end!=='string')throw Error('Invalid plan dates.');
  dateUTC(value.start);dateUTC(value.end);
  if(!Number.isSafeInteger(value.openingCents)||Math.abs(value.openingCents)>LIMITS.maxAbsCents)throw Error('Invalid opening amount.');
  if(!Array.isArray(value.events)||value.events.length>LIMITS.events)throw Error('Invalid event list or limit.');
  const ids=new Set();
  const events=value.events.map(event=>{
    if(!exactKeys(event,eventKeys))throw Error('Invalid event fields.');
    if(typeof event.id!=='string'||!event.id.trim()||event.id.length>50||ids.has(event.id))throw Error('Invalid or duplicate event ID.');
    ids.add(event.id);
    if(typeof event.label!=='string'||!event.label.trim()||event.label.length>120)throw Error('Invalid event description.');
    if(typeof event.date!=='string')throw Error('Invalid event date.');
    dateUTC(event.date);
    if(!['once','weekly','monthly'].includes(event.repeat))throw Error('Invalid recurrence.');
    if(!Number.isSafeInteger(event.cents)||Math.abs(event.cents)>LIMITS.maxAbsCents)throw Error('Invalid event amount.');
    return {id:event.id,label:event.label,date:event.date,repeat:event.repeat,cents:event.cents};
  });
  if(value.shiftId!==null&&(typeof value.shiftId!=='string'||!ids.has(value.shiftId)))throw Error('Unknown shift event.');
  if(!Number.isInteger(value.shiftDays)||Math.abs(value.shiftDays)>60)throw Error('Invalid shift days.');
  const plan={schema:PLAN_SCHEMA,start:value.start,end:value.end,openingCents:value.openingCents,events,shiftId:value.shiftId,shiftDays:value.shiftDays};
  // The interface displays both the unshifted baseline and the shifted scenario.
  // A shifted event can leave the date window and conceal baseline overflow.
  // Reject the whole plan unless BOTH projections are arithmetically valid.
  project({...plan,shiftId:null,shiftDays:0});
  project(plan);
  return plan;
}
export function exportPlan(value){return JSON.stringify(validatePlan(value),null,2)+'\n';}
export function parsePlanJSON(text){
  if(typeof text!=='string'||!text.trim())throw Error('Empty plan file.');
  let value;
  try{value=JSON.parse(text.replace(/^\uFEFF/,''));}catch{throw Error('Invalid JSON plan file.');}
  return validatePlan(value);
}
export async function readPlanFile(file){
  if(!file||typeof file.name!=='string'||!/\.json$/i.test(file.name))throw Error('Choose a .json plan file.');
  if(file.type&&!['application/json','text/plain'].includes(file.type))throw Error('Unsupported plan file type.');
  if(!Number.isSafeInteger(file.size)||file.size<1||file.size>MAX_PLAN_BYTES)throw Error('Plan must be 1–256,000 bytes.');
  const bytes=await file.arrayBuffer();
  if(!(bytes instanceof ArrayBuffer)||bytes.byteLength!==file.size)throw Error('Plan file byte count changed.');
  let text;
  try{text=new TextDecoder('utf-8',{fatal:true}).decode(bytes);}catch{throw Error('Plan must use valid UTF-8.');}
  return parsePlanJSON(text);
}
