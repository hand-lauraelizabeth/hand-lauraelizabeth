import {readExactJSON} from './json-import.mjs';
import {filterEvidenceRows,renderEvidenceRows} from './matrix-ui.mjs';
import {exportEvidenceCSV} from './core.mjs';
const $=id=>document.getElementById(id);
const upload=$('source-json'),search=$('matrix-search'),mode=$('matrix-mode'),body=$('matrix-body'),status=$('matrix-status'),exportButton=$('matrix-export');
let records=[],matched=[];
function render(){
  matched=filterEvidenceRows(records,search.value,mode.value);
  renderEvidenceRows(body,matched);
  status.textContent=records.length?matched.length+' of '+records.length+' records match; first '+Math.min(250,matched.length)+' displayed.':'Choose an evidence JSON export.';
  exportButton.disabled=!matched.length;
}
upload.addEventListener('change',async()=>{
  const file=upload.files?.[0];if(!file)return;
  upload.disabled=true;
  try{
    const next=await readExactJSON(file);
    if(!records.length||confirm('Replace current evidence records?')){
      records=next;render();
    }
  }catch(e){status.textContent='Import failed: '+String(e.message||e);}
  finally{upload.disabled=false;upload.value='';}
});
search.addEventListener('input',render);
mode.addEventListener('change',render);
exportButton.addEventListener('click',()=>{
  if(!matched.length)return;
  const csv=exportEvidenceCSV(matched);
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download='evidence-matrix.csv';a.click();
  setTimeout(()=>URL.revokeObjectURL(url),2000);
});
render();
