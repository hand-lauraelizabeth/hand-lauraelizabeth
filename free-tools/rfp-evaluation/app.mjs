import {exportMatrixJSON,exportMatrixCSV,exportEvidenceCSV} from './core.mjs';
import {evaluateWithProvenance,exportEvidenceCoverageCSV} from './evidence-coverage.mjs';
import {readWorkspaceFile} from './reopen.mjs';
import {describeCoverage,summarizeCriterionCoverage,summarizeVendorCoverage} from './coverage-summary.mjs';
import {createReplacementGate} from './replacement-gate.mjs';
import {createResetGate} from './reset-gate.mjs';
import {startLocalDownload} from './download-guard.mjs';
const $=id=>document.getElementById(id);
let current=null;
let importSequence=0;
const replacementGate=createReplacementGate();
const resetGate=createResetGate();
let resetToken=null;
let previewToken=null;
// A pending import must not overwrite edits made while its file is being read.
function dismissPreview(){replacementGate.cancel();previewToken=null;$('import-preview').hidden=true;}
function dismissResetPreview(){resetGate.cancel();resetToken=null;const section=$('reset-preview');if(section)section.hidden=true;}
function cancelPendingImport(){importSequence++;dismissPreview();const input=$('reopen-json');if(input){input.value='';input.removeAttribute('aria-invalid');input.setAttribute('aria-describedby','reopen-help');}}
const counts={criterion:0,vendor:0,rating:0};
const containers={criterion:'criteria-list',vendor:'vendors-list',rating:'ratings-list'};
const rowLimits=Object.freeze({criterion:30,vendor:30,rating:900});
function addRow(kind){
 if($(containers[kind]).children.length>=rowLimits[kind]){
  showError(`The maximum is ${rowLimits[kind]} ${kind} entries. Remove an entry before adding another.`);
  $('status').textContent='Entry not added. Existing entries were preserved.';
  return null;
 }
 dismissResetPreview();
 const item=$(kind+'-template').content.firstElementChild.cloneNode(true);
 const num=++counts[kind];item.querySelector('legend').textContent=`${kind[0].toUpperCase()+kind.slice(1)} ${num}`;
 for(const field of item.querySelectorAll('[data-field]')){
  const id=`${kind}-${num}-${field.dataset.field}`;const label=field.closest('label');field.id=id;label.htmlFor=id;
 }
 item.querySelector('[data-remove]').addEventListener('click',()=>{
  // Native confirmation is keyboard operable and does not repeat sensitive IDs.
  // Cancel must leave the evaluated results, pending import, and inputs intact.
  if(!window.confirm(`Remove this ${kind} entry? Its locally entered fields will be discarded. Select Cancel to keep the entry.`)){
   $('status').textContent=`${kind} removal canceled. Existing entries were preserved.`;
   return;
  }
  cancelPendingImport();dismissResetPreview();item.remove();invalidate();
  $('status').textContent=`${kind} entry removed. Evaluate again before exporting.`;
  // Removing the focused button must not strand keyboard focus in detached DOM.
  $('add-'+kind).focus();
 });
 $(containers[kind]).append(item);invalidate();return item;
}
function invalidate(){current=null;$('results-section').hidden=true;$('status').textContent='';$('error').hidden=true;}
function rows(kind){return [...$(containers[kind]).querySelectorAll('.entry')].map(entry=>{
 const out={};for(const input of entry.querySelectorAll('[data-field]'))out[input.dataset.field]=input.type==='checkbox'?input.checked:input.value;
 return out;
});}
function showError(error){$('error').textContent=error instanceof Error?error.message:String(error);$('error').hidden=false;$('error').focus();$('status').textContent='Evaluation or export was not completed.';}
function clearImportError(){const input=$('reopen-json');input.removeAttribute('aria-invalid');input.setAttribute('aria-describedby','reopen-help');}
function showImportError(error){showError(error);const input=$('reopen-json');input.setAttribute('aria-invalid','true');input.setAttribute('aria-describedby','reopen-help error');$('status').textContent='Import failed. Existing entries were preserved.';}
function evaluate(event){event.preventDefault();cancelPendingImport();invalidate();try{
 const data={criteria:rows('criterion'),vendors:rows('vendor'),ratings:rows('rating')};
 current=evaluateWithProvenance(data);const body=$('result-body');body.replaceChildren();
 for(const item of current.comparisons){const tr=document.createElement('tr');const values=[item.vendorId,item.name,item.scorePercent===null?'Incomplete':item.scorePercent.toFixed(1)+'%',item.priceCents===null?'Not supplied':'$'+(item.priceCents/100).toFixed(2),item.reviewFlags.length?item.reviewFlags.join('; '):'No flags'];for(const value of values){const td=document.createElement('td');td.textContent=value;tr.append(td);}body.append(tr);}
 const criterionBody=$('criterion-coverage-body');criterionBody.replaceChildren();
 for(const item of summarizeCriterionCoverage(current)){
  const tr=document.createElement('tr');
  for(const [index,value] of [item.criterionId,item.scoredPairs,item.completeReferencePairs,item.missingScores,item.scoredMissingAnyReference].entries()){
   const cell=document.createElement(index===0?'th':'td');
   if(index===0)cell.scope='row';
   cell.textContent=String(value);tr.append(cell);
  }
  criterionBody.append(tr);
 }
 const vendorBody=$('vendor-coverage-body');vendorBody.replaceChildren();
 for(const item of summarizeVendorCoverage(current)){
  const tr=document.createElement('tr');
  for(const [index,value] of [item.vendorId,item.scoredPairs,item.completeReferencePairs,item.missingScores,item.scoredMissingAnyReference].entries()){
   const cell=document.createElement(index===0?'th':'td');
   if(index===0)cell.scope='row';
   cell.textContent=String(value);tr.append(cell);
  }
  vendorBody.append(tr);
 }
 $('result-summary').textContent=`${current.comparisons.length} proposal(s) evaluated. ${describeCoverage(current)}`;$('results-section').hidden=false;$('status').textContent='Evaluation complete. '+describeCoverage(current)+' Review flags before exporting.';
 }catch(e){showError(e);}}
function download(kind){if(!current){showError('Evaluate proposals before exporting.');return;}try{
 const data=kind==='json'?exportMatrixJSON(current):kind==='matrix'?exportMatrixCSV(current):kind==='coverage'?exportEvidenceCoverageCSV(current):exportEvidenceCSV(current);
 const mime=kind==='json'?'application/json':'text/csv';const filename=kind==='json'?'rfp-evidence.json':kind==='matrix'?'rfp-comparison.csv':kind==='coverage'?'rfp-coverage.csv':'rfp-ratings.csv';
 startLocalDownload({data,filename,mime});
 $('error').hidden=true;$('status').textContent=`${filename} download started locally. Confirm the file was saved and verify its contents before sharing.`;
 }catch(e){showError(e);}}
for(const kind of Object.keys(containers)){$('add-'+kind).addEventListener('click',()=>{cancelPendingImport();addRow(kind);});addRow(kind);}
$('matrix-form').addEventListener('submit',evaluate);
$('matrix-form').addEventListener('input',()=>{dismissResetPreview();cancelPendingImport();invalidate();});
// A destructive clear requires an explicit second action. Keep the existing form
// intact until confirmation; the preview itself is non-modal and keyboard reachable.
$('reset-form').addEventListener('click',()=>{
 cancelPendingImport();
 const snapshot=resetGate.stage(Object.fromEntries(Object.keys(containers).map(kind=>[kind,$(containers[kind]).querySelectorAll('.entry').length])));
 resetToken=snapshot.token;
 $('reset-preview-summary').textContent=`This will discard ${snapshot.total} current entry/entries. Save a JSON copy first if you need these records.`;
 $('reset-preview').hidden=false;
 $('confirm-reset').focus();
});
function cancelReset(){dismissResetPreview();$('status').textContent='Clear canceled. Existing entries were preserved.';$('reset-form').focus();}
$('cancel-reset').addEventListener('click',cancelReset);
$('confirm-reset').addEventListener('click',()=>{
 try{resetGate.take(resetToken);}catch(e){dismissResetPreview();showError(e);return;}
 dismissResetPreview();cancelPendingImport();
 for(const id of Object.values(containers))$(id).replaceChildren();
 for(const kind of Object.keys(containers))addRow(kind);
 invalidate();$('status').textContent='All entries cleared.';$('add-criterion').focus();
});
$('download-json').addEventListener('click',()=>download('json'));
$('download-matrix').addEventListener('click',()=>download('matrix'));
$('download-evidence').addEventListener('click',()=>download('evidence'));
$('download-coverage').addEventListener('click',()=>download('coverage'));
function populate(kind,items){
 for(const item of items){const entry=addRow(kind);for(const input of entry.querySelectorAll('[data-field]')){
  const value=item[input.dataset.field];if(input.type==='checkbox')input.checked=value===true;
  else input.value=value===null||value===undefined?'':String(value);
 }}
}
$('cancel-reopen').addEventListener('click',()=>{cancelPendingImport();$('status').textContent='Import canceled. Current entries were preserved.';$('reopen-json').focus();});
// Escape offers a keyboard-only way to keep current entries without changing focus order.
document.addEventListener('keydown',event=>{
 if(event.key==='Escape'&&!$('reset-preview').hidden){
  event.preventDefault();cancelReset();return;
 }
 if(event.key==='Escape'&&!$('import-preview').hidden){
  event.preventDefault();cancelPendingImport();
  $('status').textContent='Import canceled. Current entries were preserved.';
  $('reopen-json').focus();
 }
});
$('confirm-reopen').addEventListener('click',()=>{
 let workspace;try{workspace=replacementGate.take(previewToken);}catch(e){dismissPreview();showImportError(e);return;}
 cancelPendingImport();
 for(const id of Object.values(containers))$(id).replaceChildren();
 for(const kind of Object.keys(containers))populate(kind,workspace[kind==='criterion'?'criteria':kind==='vendor'?'vendors':'ratings']);
 invalidate();clearImportError();$('status').textContent='JSON workspace reopened locally. Review inputs and evaluate again.';
 $('criteria-title').focus();
});
$('reopen-json').addEventListener('change',async event=>{
 const file=event.target.files?.[0];const sequence=++importSequence;
 dismissPreview();if(!file)return;clearImportError();$('error').hidden=true;
 try{
  const workspace=await readWorkspaceFile(file);
  if(sequence!==importSequence)return; // stale asynchronous file selection
  const staged=replacementGate.stage(workspace);previewToken=staged.token;
  $('import-preview-summary').textContent=`The selected file contains ${staged.counts.criteria} criterion/criteria, ${staged.counts.vendors} vendor(s), and ${staged.counts.ratings} rating(s).`;
  $('import-preview').hidden=false;$('status').textContent='Validated local workspace ready for review. Choose Replace or Keep.';
  $('confirm-reopen').focus();
 }catch(e){if(sequence===importSequence){dismissPreview();showImportError(e);}}finally{if(sequence===importSequence)event.target.value='';}
});
