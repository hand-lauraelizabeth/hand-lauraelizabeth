export const MATRIX_LIMIT=10000;
export function buildEvidenceMatrix(records){
 if(!Array.isArray(records)||records.length>MATRIX_LIMIT)throw Error('Too many records');
 const counts=new Map();
 for(const r of records){
  if(typeof r?.sourceId!=='string'||typeof r?.group!=='string')throw Error('Invalid record');
  if(r.group.trim())counts.set(r.group,(counts.get(r.group)||0)+1);
 }
 const rows=records.map(r=>{
  const relatedCount=r.group.trim()?counts.get(r.group):0;
  return {...r,relatedCount,reviewFlag:relatedCount>1?'Compare manually':relatedCount?'Single-record group':'Ungrouped'};
 });
 const cmp=(a,b)=>a<b?-1:a>b?1:0;
 rows.sort((a,b)=>cmp(a.relatedCount===0,b.relatedCount===0)||cmp(a.group,b.group)||cmp(a.date,b.date)||cmp(a.sourceId,b.sourceId));
 return rows;
}
