// Portable, browser-local workspace format. Inputs are untrusted; do not execute imported content.
import {LIMITS,dateUTC,parseCents,formatCents,project} from './engine.mjs';
export const WORKSPACE_MAX_BYTES=1_000_000;
export const WORKSPACE_FORMAT='ft04-cash-flow-workspace';
export const WORKSPACE_VERSION=1;
const keys=(value,expected)=>{
  if(value===null||typeof value!=='object'||Array.isArray(value))throw Error('Expected a JSON object.');
  const actual=Object.keys(value).sort();
  if(actual.join('\0')!==[...expected].sort().join('\0'))throw Error('Workspace contains missing or unsupported fields.');
};
const boundedString=(value,max,field,allowEmpty=false)=>{
  if(typeof value!=='string'||value.length>max||(!allowEmpty&&!value.trim())||/[\u0000-\u001f\u007f]/u.test(value))throw Error(`Invalid ${field}.`);
  return value;
};
export function validateWorkspace(input){
  keys(input,['format','version','settings','events']);
  if(input.format!==WORKSPACE_FORMAT||input.version!==WORKSPACE_VERSION)throw Error('Unsupported workspace format or version.');
  const s=input.settings;
  keys(s,['start','end','opening','shiftId','shiftDays']);
  boundedString(s.start,10,'start date');boundedString(s.end,10,'end date');
  dateUTC(s.start);dateUTC(s.end);
  const openingCents=parseCents(boundedString(s.opening,20,'opening balance'));
  if(typeof s.shiftDays!=='number'||!Number.isSafeInteger(s.shiftDays)||Math.abs(s.shiftDays)>60)throw Error('Shift days must be an integer between -60 and 60.');
  if(s.shiftId!==null)boundedString(s.shiftId,50,'shift event ID');
  if(!Array.isArray(input.events)||input.events.length>LIMITS.events)throw Error('Too many events in workspace.');
  const ids=new Set();
  const events=input.events.map((e,i)=>{
    keys(e,['id','label','date','repeat','amount']);
    const id=boundedString(e.id,50,`event ${i+1} ID`);
    const label=boundedString(e.label,120,`event ${i+1} description`);
    if(ids.has(id))throw Error('Duplicate event IDs are not allowed.');
    ids.add(id);
    boundedString(e.date,10,'event date');dateUTC(e.date);
    if(!['once','weekly','monthly'].includes(e.repeat))throw Error('Unsupported event recurrence.');
    const cents=parseCents(boundedString(e.amount,20,'event amount'));
    return {id,label,date:e.date,repeat:e.repeat,cents};
  });
  project({start:s.start,end:s.end,openingCents,events,shiftId:s.shiftId,shiftDays:s.shiftDays});
  return {settings:{start:s.start,end:s.end,opening:formatCents(openingCents),shiftId:s.shiftId,shiftDays:s.shiftDays},events};
}
export function serializeWorkspace(settings,events){
  const data={format:WORKSPACE_FORMAT,version:WORKSPACE_VERSION,settings:{
    start:settings.start,end:settings.end,opening:settings.opening,
    shiftId:settings.shiftId,shiftDays:settings.shiftDays
  },events:events.map(e=>({id:e.id,label:e.label,date:e.date,repeat:e.repeat,amount:formatCents(e.cents)}))};
  const validated=validateWorkspace(data);
  const json=JSON.stringify(data,null,2)+'\n';
  if(new TextEncoder().encode(json).byteLength>WORKSPACE_MAX_BYTES)throw Error('Workspace exceeds 1 MB.');
  return {json,validated};
}
export function parseWorkspaceBytes(bytes){
  if(!(bytes instanceof Uint8Array))throw Error('Expected file bytes.');
  if(bytes.byteLength===0||bytes.byteLength>WORKSPACE_MAX_BYTES)throw Error('Workspace JSON must be 1–1,000,000 bytes.');
  let text;
  try{text=new TextDecoder('utf-8',{fatal:true}).decode(bytes)}catch{throw Error('Workspace must contain valid UTF-8.');}
  if(text.startsWith('\uFEFF'))text=text.slice(1);
  if(text.includes('\u0000'))throw Error('Workspace contains a NUL character.');
  let data;
  try{data=JSON.parse(text)}catch{throw Error('Workspace contains malformed JSON.');}
  return validateWorkspace(data);
}
