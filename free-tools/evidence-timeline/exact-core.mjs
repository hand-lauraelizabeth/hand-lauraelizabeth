// Source identifiers are exact: no trimming or Unicode normalization.
export function normalizeExact(rows) {
  if (!Array.isArray(rows) || rows.length > 10000) throw Error('At most 10000 records allowed');
  const ids=new Set();
  const statuses=['reported','corroborated','disputed','unresolved'];
  const kinds=['source','observation','inference'];
  const validDate=s=>{
    if(typeof s!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
    const [y,m,d]=s.split('-').map(Number);
    if(y<1||m<1||m>12) return false;
    const leap=y%4===0&&(y%100!==0||y%400===0);
    const days=[31,leap?29:28,31,30,31,30,31,31,30,31,30,31];
    return d>=1&&d<=days[m-1];
  };
  return rows.map((r,i)=>{
    if(!r||typeof r!=='object'||Array.isArray(r)) throw Error('Invalid record '+(i+1));
    const {sourceId,date,claim,status='reported',kind='source',group=''}=r;
    if(typeof sourceId!=='string'||!sourceId.trim()||sourceId.length>120||ids.has(sourceId)) throw Error('Invalid or duplicate source ID '+(i+1));
    ids.add(sourceId);
    if(!validDate(date)) throw Error('Invalid date for '+sourceId);
    if(typeof claim!=='string'||!claim.trim()||claim.length>20000) throw Error('Invalid claim for '+sourceId);
    if(!statuses.includes(status)||!kinds.includes(kind)||typeof group!=='string'||group.length>120) throw Error('Invalid classification for '+sourceId);
    return {sourceId,date,claim,status,kind,group};
  }).sort((a,b)=>a.date<b.date?-1:a.date>b.date?1:a.sourceId<b.sourceId?-1:a.sourceId>b.sourceId?1:0);
}
