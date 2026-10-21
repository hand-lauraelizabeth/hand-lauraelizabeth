import {buildEvidenceMatrix} from './review-matrix.mjs';
export function filterEvidenceRows(records,query='',mode='all'){
 const q=String(query).toLocaleLowerCase();
 return buildEvidenceMatrix(records).filter(r=>
  (!q||[r.sourceId,r.group,r.claim].some(v=>String(v??'').toLocaleLowerCase().includes(q)))&&
  (mode==='all'||(mode==='compare'&&r.relatedCount>1)||(mode==='single'&&r.relatedCount===1)||(mode==='ungrouped'&&r.relatedCount===0)));
}
export function renderEvidenceRows(tbody,rows){
 tbody.replaceChildren();
 for(const r of rows.slice(0,250)){
  const tr=document.createElement('tr');
  for(const key of ['sourceId','date','group','reviewFlag','kind','status','claim']){
   const cell=document.createElement(key==='sourceId'?'th':'td');
   if(key==='sourceId')cell.scope='row';
   cell.textContent=String(r[key]??'');
   tr.append(cell);
  }
  tbody.append(tr);
 }
}
