/* Evidence Timeline: browser-local, no network, no professional determinations. */
export function normalizeEvidence(rows) {
  if (!Array.isArray(rows) || rows.length > 10000) throw Error("Expected at most 10000 records");
  const ids = new Set();
  return rows.map((r, index) => {
    if (!r || typeof r !== "object" || Array.isArray(r)) throw Error("Invalid record "+(index+1));
    const id = String(r.sourceId ?? "").trim();
    if (!id || id.length > 120 || ids.has(id)) throw Error("Missing, duplicate or oversized source ID");
    ids.add(id);
    const date = String(r.date ?? "").trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !validDate(date)) throw Error("Invalid calendar date for "+id);
    const claim = String(r.claim ?? "").trim();
    if (!claim || claim.length > 20000) throw Error("Missing or oversized claim for "+id);
    const status = String(r.status ?? "reported");
    if (!["reported","corroborated","disputed","unresolved"].includes(status)) throw Error("Invalid status for "+id);
    const kind = String(r.kind ?? "source");
    if (!["source","observation","inference"].includes(kind)) throw Error("Invalid kind for "+id);
    const group = String(r.group ?? "").trim().slice(0,120);
    return {sourceId:id,date,claim,status,kind,group};
  }).sort((a,b)=>a.date.localeCompare(b.date)||a.sourceId.localeCompare(b.sourceId));
}
function validDate(s) { const [y,m,d]=s.split("-").map(Number); const t=new Date(Date.UTC(y,m-1,d)); return t.getUTCFullYear()===y && t.getUTCMonth()===m-1 && t.getUTCDate()===d; }
export function findReviewGroups(records) {
  const groups=new Map();
  for (const r of records) if(r.group) { const a=groups.get(r.group)||[]; a.push(r); groups.set(r.group,a); }
  return [...groups].filter(([,a])=>a.length>1).map(([group,items])=>({group,sourceIds:items.map(x=>x.sourceId),reviewRequired:true}));
}
export function exportEvidenceCSV(records) {
  const cols=["sourceId","date","claim","status","kind","group"];
  const safe = v => { let s=String(v??""); if (/^[\s\uFEFF]*[=+@\-\t\r]/u.test(s)) s="'"+s; return '"'+s.replaceAll('"','""')+'"'; };
  return [cols.join(","),...records.map(r=>cols.map(c=>safe(r[c])).join(","))].join("\r\n")+"\r\n";
}
export function summary(records) {
  const counts={reported:0,corroborated:0,disputed:0,unresolved:0};
  for (const r of records) counts[r.status]++;
  return {total:records.length,counts,reviewGroups:findReviewGroups(records)};
}
