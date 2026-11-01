/** FT-12: local housing evidence chronology; not a legal or payment determination. */
// Match the maximum accepted local JSON import size, including UTF-8 multibyte text.
export const HOUSING_JSON_LIMIT = 5_000_000;
const id = (v) => {
  if (typeof v !== 'string' || !/^[^\u0000-\u001f\u007f]{1,160}$/u.test(v) || !v.trim()) throw Error('Invalid source or event ID');
  return v;
};
const note = (v, max=2000) => {
  if (typeof v !== 'string' || v.length > max || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/u.test(v)) throw Error('Invalid text');
  return v;
};
const date = (v, optional=false) => {
  if (optional && (v === null || v === undefined || v === '')) return null;
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/u.test(v)) throw Error('Invalid date format');
  const [y,m,d] = v.split('-').map(Number);
  const check = new Date(Date.UTC(y,m-1,d));
  if (y<1000 || y>9999 || check.getUTCFullYear()!==y || check.getUTCMonth()!==m-1 || check.getUTCDate()!==d) throw Error('Invalid calendar date');
  return v;
};
const unique = (arr) => { if (new Set(arr).size !== arr.length) throw Error('Duplicate ID'); };
const kinds = new Set(['rent','deposit','repair','inspection','communication','other']);
export function buildHousingLedger({sources,events}) {
  if (!Array.isArray(sources) || sources.length>2000 || !Array.isArray(events) || events.length>2000) throw Error('Too many or invalid records');
  const safeSources = sources.map(s => {
    if (!s || typeof s!=='object' || Array.isArray(s)) throw Error('Invalid source');
    return {sourceId:id(s.sourceId),kind:note(s.kind??'other',60),label:note(s.label??'',300),date:date(s.date,true)};
  });
  unique(safeSources.map(s=>s.sourceId));
  const known = new Set(safeSources.map(s=>s.sourceId));
  const safeEvents = events.map((e,index) => {
    if (!e || typeof e!=='object' || Array.isArray(e) || !kinds.has(e.category)) throw Error('Invalid event');
    const eventId=id(e.eventId);
    if (!Array.isArray(e.sourceIds) || e.sourceIds.length>30) throw Error('Invalid source links');
    const sourceIds=e.sourceIds.map(id);
    unique(sourceIds);
    if (sourceIds.some(s=>!known.has(s))) throw Error('Unknown source ID');
    const amountCents=e.amountCents??null;
    if (amountCents!==null && (!Number.isSafeInteger(amountCents) || amountCents<0 || amountCents>100000000000)) throw Error('Invalid integer cents');
    return {eventId,date:date(e.date),category:e.category,description:note(e.description??''),sourceIds,amountCents,index};
  });
  unique(safeEvents.map(e=>e.eventId));
  safeEvents.sort((a,b)=>a.date.localeCompare(b.date) || a.index-b.index);
  const findings=[];
  for (const e of safeEvents) {
    if (!e.sourceIds.length) findings.push({eventId:e.eventId,kind:'unlinked-evidence'});
    if (e.category==='deposit' && e.amountCents===null) findings.push({eventId:e.eventId,kind:'missing-deposit-amount'});
  }
  return {schema:'housing-evidence-ledger-v1',sources:safeSources,events:safeEvents.map(({index,...rest})=>rest),findings,disclaimer:'Organizational record only. No legal rights, payment status, deadlines, or deposit entitlement are determined.'};
}
/** Correct an event without changing its exact ID or any other record. Invalid edits fail atomically. */
export function reviseHousingEvent({sources,events}, eventId, changes) {
  const ledger=buildHousingLedger({sources,events});
  if (typeof eventId!=='string' || !ledger.events.some(e=>e.eventId===eventId)) throw Error('Unknown event ID');
  const fields=['date','description','sourceIds','amountCents'];
  if (!changes || typeof changes!=='object' || Array.isArray(changes) ||
      Object.keys(changes).length!==fields.length || !fields.every(k=>Object.hasOwn(changes,k))) {
    throw Error('Invalid event correction fields');
  }
  const revised=ledger.events.map(e=>e.eventId===eventId?{...e,...changes}:e);
  return buildHousingLedger({sources:ledger.sources,events:revised});
}

export function exportHousingJSON(ledger) {
  if (!ledger || ledger.schema!=='housing-evidence-ledger-v1' || !Array.isArray(ledger.events) || !Array.isArray(ledger.sources)) throw Error('Invalid ledger');
  const json = JSON.stringify(ledger,null,2)+'\n';
  if (new Blob([json]).size > HOUSING_JSON_LIMIT) {
    throw Error('JSON exceeds the 5,000,000-byte reopen limit');
  }
  return json;
}
