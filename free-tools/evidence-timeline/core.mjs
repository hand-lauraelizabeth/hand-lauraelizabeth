/* Evidence Timeline: browser-local, no network, no professional determinations. */
import { normalizeExact } from './exact-core.mjs';
export function normalizeEvidence(rows) {
  return normalizeExact(rows);
}
export function findReviewGroups(records) {
  const groups=new Map();
  for (const r of records) if(r.group) { const a=groups.get(r.group)||[]; a.push(r); groups.set(r.group,a); }
  return [...groups].filter(([,a])=>a.length>1).map(([group,items])=>({group,sourceIds:items.map(x=>x.sourceId),reviewRequired:true}));
}
export function exportEvidenceCSV(records) {
  const cols=["sourceId","date","claim","status","kind","group"];
  const safe = v => { let s=String(v??""); if (/^[\s\uFEFF]*[=+@\-\t\r＝＋－＠]/u.test(s)) s="'"+s; return '"'+s.replaceAll('"','""')+'"'; };
  return [cols.join(","),...records.map(r=>cols.map(c=>safe(r[c])).join(","))].join("\r\n")+"\r\n";
}
export function summary(records) {
  const counts={reported:0,corroborated:0,disputed:0,unresolved:0};
  for (const r of records) counts[r.status]++;
  return {total:records.length,counts,reviewGroups:findReviewGroups(records)};
}
