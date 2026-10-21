/** Local public-records organizer. No deadline, legal-status, or agency-eligibility determination. */
const jurisdictions = new Set(['federal','state','local','other']);
const stages = new Set(['draft','submitted','acknowledged','processing','responded','closed','unknown']);
const eventKinds = new Set(['submitted','acknowledged','agency-message','clarification','response','appeal','note']);
const headers = ['recordType','requestId','eventId','date','jurisdiction','agency','stage','kind','sourceId','description'];
const text = (v, max, label, required=false) => {
  if (typeof v !== 'string' || v.length > max || (required && !v.trim())) throw new Error(`Invalid ${label}`);
  if (v.includes('\0')) throw new Error(`Invalid ${label}`);
  return v;
};
const date = (v, label, required=false) => {
  text(v,10,label,required);
  if (!v && !required) return v;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) throw new Error(`Invalid ${label}`);
  const [y,m,d]=v.split('-').map(Number), dt=new Date(Date.UTC(y,m-1,d));
  if (dt.getUTCFullYear()!==y || dt.getUTCMonth()!==m-1 || dt.getUTCDate()!==d) throw new Error(`Invalid ${label}`);
  return v;
};
export function validateWorkspace(value) {
  if (!value || typeof value!=='object' || Array.isArray(value)) throw new Error('Workspace must be an object');
  if (value.version !== 1 || !Array.isArray(value.requests) || !Array.isArray(value.events)) throw new Error('Unsupported workspace format');
  if (value.requests.length>1000 || value.events.length>10000) throw new Error('Workspace record limit exceeded');
  const ids=new Set(), eventIds=new Set();
  const requests=value.requests.map(r=>{
    if (!r || typeof r!=='object' || Array.isArray(r)) throw new Error('Invalid request');
    const id=text(r.id,120,'request ID',true);
    if (ids.has(id)) throw new Error('Duplicate request ID'); ids.add(id);
    const jurisdiction=text(r.jurisdiction,20,'jurisdiction',true);
    const stage=text(r.stage,20,'stage',true);
    if (!jurisdictions.has(jurisdiction) || !stages.has(stage)) throw new Error('Invalid request classification');
    return {id,jurisdiction,agency:text(r.agency,300,'agency',true),stage,
      submittedOn:date(r.submittedOn,'submitted date'),agencyTrackingId:text(r.agencyTrackingId,200,'agency tracking ID'),
      description:text(r.description,5000,'description',true)};
  });
  const events=value.events.map(e=>{
    if (!e || typeof e!=='object' || Array.isArray(e)) throw new Error('Invalid event');
    const id=text(e.id,120,'event ID',true), requestId=text(e.requestId,120,'request ID',true);
    if (eventIds.has(id)) throw new Error('Duplicate event ID'); eventIds.add(id);
    if (!ids.has(requestId)) throw new Error('Event refers to unknown request');
    const kind=text(e.kind,30,'event kind',true);
    if (!eventKinds.has(kind)) throw new Error('Invalid event kind');
    return {id,requestId,date:date(e.date,'event date',true),kind,
      sourceId:text(e.sourceId,200,'source ID'),description:text(e.description,5000,'event description',true)};
  });
  return {version:1,requests,events};
}
export const emptyWorkspace=()=>({version:1,requests:[],events:[]});
export function chronology(workspace) {
  const data=validateWorkspace(workspace);
  return [...data.events].sort((a,b)=>a.date.localeCompare(b.date)||a.id.localeCompare(b.id));
}
export function reviewFlags(workspace) {
  const w=validateWorkspace(workspace);
  return w.requests.map(r=>({requestId:r.id, flags:[
    ...(!r.submittedOn && r.stage!=='draft' ? ['Submission date not recorded']:[]),
    ...(!r.agencyTrackingId && ['submitted','acknowledged','processing','responded','closed'].includes(r.stage)?['Agency tracking ID not recorded']:[]),
    ...(r.stage==='responded' && !w.events.some(e=>e.requestId===r.id && e.kind==='response')?['Response event not recorded']:[])
  ]})).filter(x=>x.flags.length);
}
const safeCell=v=>{
  const s=String(v??'');
  const normalized=s.normalize('NFKC');
  const leading=normalized.replace(/^[\p{Cf}\p{M}\s\uFEFF]+/u,'');
  // Fail closed: spreadsheet applications may discard escaping on reopening or resaving.
  // JSON remains lossless, preserving exact IDs and original strings.
  if (/[\u061C\u200E\u200F\u202A-\u202E\u2066-\u206F\u0085\u2028\u2029]/u.test(normalized)
    || /^[=+@-]/u.test(leading)
    || /[,;"'\t\r\n][\p{Cf}\p{M}\s\uFEFF]*[=+@-]/u.test(normalized)
    || /[\u0000-\u0008\u000B\u000C\u000E-\u001F]/u.test(normalized))
    throw new Error('CSV export blocked: potentially executable or misleading spreadsheet content. Use JSON to preserve exact records.');
  return '"'+s.replaceAll('"','""')+'"';
};
export function exportCSV(workspace) {
  const w=validateWorkspace(workspace);
  const rows=[headers];
  for (const r of w.requests) rows.push(['request',r.id,'',r.submittedOn,r.jurisdiction,r.agency,r.stage,'',r.agencyTrackingId,r.description]);
  for (const e of chronology(w)) rows.push(['event',e.requestId,e.id,e.date,'','','',e.kind,e.sourceId,e.description]);
  return rows.map(row=>row.map(safeCell).join(',')).join('\r\n')+'\r\n';
}
export function exportJSON(workspace) {return JSON.stringify(validateWorkspace(workspace),null,2)+'\n';}
