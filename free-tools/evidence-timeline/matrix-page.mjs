import {readExactJSON} from './json-import.mjs';
import {filterEvidenceRows,renderEvidenceRows} from './matrix-ui.mjs';
import {exportEvidenceCSV} from './core.mjs';
const $=id=>document.getElementById(id);
const upload=$('source-json'),search=$('matrix-search'),mode=$('matrix-mode'),body=$('matrix-body'),status=$('matrix-status'),error=$('matrix-error'),exportButton=$('matrix-export'),clearButton=$('matrix-clear');
let records=[],matched=[];
let importSequence=0; // Ignore stale async reads after a newer selection.
function render(){
  matched=filterEvidenceRows(records,search.value,mode.value);
  renderEvidenceRows(body,matched);
  status.textContent=records.length?matched.length+' of '+records.length+' records match; first '+Math.min(250,matched.length)+' displayed.':'Choose an evidence JSON export.';
  exportButton.disabled=!matched.length;
  clearButton.disabled=!records.length && !upload.disabled;
}
upload.addEventListener('change',async()=>{
  const file=upload.files?.[0];if(!file)return;
  const sequence=++importSequence;
  upload.disabled=true;
  clearButton.disabled=false;
  try{
    const next=await readExactJSON(file);
    if(sequence!==importSequence)return;
    if(error)error.textContent='';
    if(!records.length||confirm('Replace current evidence records?')){
      records=next;render();
    }
  }catch(e){if(sequence===importSequence){const message='Import failed: '+String(e.message||e)+'. Existing records remain available.';if(error)error.textContent=message;else status.textContent=message;}}
  finally{if(sequence===importSequence){upload.disabled=false;upload.value='';clearButton.disabled=!records.length;}}
});
clearButton.addEventListener('click',()=>{
  if(!records.length && !upload.disabled)return;
  if(!confirm('Reset this evidence view?'))return;
  ++importSequence;
  records=[];matched=[];
  upload.disabled=false;upload.value='';
  search.value='';mode.value='all';
  if(error)error.textContent='';
  render();
  status.textContent='Evidence view reset. Choose a new JSON export.';
  upload.focus();
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
