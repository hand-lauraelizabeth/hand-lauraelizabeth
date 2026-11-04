import {summary} from './core.mjs';
import {startLocalDownload} from './download-guard.mjs';
import {csvExportRisk,exportSafeEvidenceCSV} from './safe-export.mjs';
import {normalizeExact as normalizeEvidence} from './exact-core.mjs';
import {readExactJSON} from './json-import.mjs';
import {createImportFeedback} from './import-feedback.mjs';
import {previewReplacement, replacementConfirmation} from './replacement-preview.mjs';
import {reviewStatusSummary} from './review-filter.mjs';
import {findSourceIds} from './source-id-find.mjs';
import {filterByGroupLabel} from './group-find.mjs';
import {formatGroupSummary} from './group-summary.mjs';
import {setReviewGroup} from './edit-group.mjs';
import {STATUS_OPTIONS} from './reclassify.mjs';
import {changeReviewStatus, undoReviewStatus} from './undo-status.mjs';
const $ = id => document.getElementById(id);
let records = [];
let pendingStatusUndo = null;
let editingGroupId = null;
const form=$('entry-form'), error=$('error'), list=$('records');
const text=(tag,value)=>{const e=document.createElement(tag);e.textContent=String(value);return e;};
function clearStatusUndo(){pendingStatusUndo=null;$('undo-status').hidden=true;$('undo-status').disabled=true;}
function offerStatusUndo(change){pendingStatusUndo=change;$('undo-status').hidden=false;$('undo-status').disabled=false;}
function showError(message,field){error.textContent=message;error.hidden=false; if(field){const input=$(field);input.setAttribute('aria-invalid','true');input.setAttribute('aria-describedby','error');}error.focus();}
function clearError(){error.hidden=true;error.textContent='';for(const field of form.elements)if(field.removeAttribute){field.removeAttribute('aria-invalid');field.removeAttribute('aria-describedby');}}
function stopGroupEdit(){
  editingGroupId=null;
  $('group-edit-panel').hidden=true;
  $('group-edit-form').reset();
  $('group-edit-error').hidden=true;
  $('group-edit-error').textContent='';
  $('group-edit-value').removeAttribute('aria-invalid');
  $('group-edit-value').removeAttribute('aria-describedby');
}
function focusGroupEditButton(sourceId){
  const button=[...list.querySelectorAll('button[data-edit-group]')].find(item=>item.dataset.editGroup===sourceId);
  (button||$('count')).focus();
}
function beginGroupEdit(record){
  if(editingGroupId!==null && editingGroupId!==record.sourceId &&
      !window.confirm('Discard the unsaved group edit and open another record?')) return;
  editingGroupId=record.sourceId;
  $('group-edit-form').reset();
  $('group-edit-error').hidden=true;
  $('group-edit-error').textContent='';
  $('group-edit-value').removeAttribute('aria-invalid');
  $('group-edit-value').setAttribute('aria-describedby','group-edit-help');
  $('group-edit-source').textContent='Source ID: '+record.sourceId;
  $('group-edit-value').value=record.group;
  $('group-edit-panel').hidden=false;
  $('group-edit-value').focus();
}
function render(){
  list.replaceChildren();const report=summary(records);
  const selected=$('review-filter').value;const query=$('source-find').value;
  const groupQuery=$('group-find').value, ungroupedOnly=$('ungrouped-only').checked;
  const visible=filterByGroupLabel(findSourceIds(records,selected,query),groupQuery,ungroupedOnly);
  $('clear-source-find').disabled=query==='';
  $('clear-group-find').disabled=groupQuery==='' && !ungroupedOnly;
  $('count').textContent=selected==='all' && query==='' && groupQuery==='' && !ungroupedOnly ? report.total+' '+(report.total===1?'record':'records')+' (date order).' : 'Showing '+visible.length+' of '+report.total+' records (date order).';
  $('review-summary').textContent=reviewStatusSummary(records);
  $('groups').textContent=formatGroupSummary(report.reviewGroups);
  $('empty').hidden=visible.length>0;
  $('empty').textContent=records.length===0 ? 'No records yet. Add a record to build your timeline.' : 'No records match the selected review status, source ID, or group filter. Clear the searches or choose All statuses.';
  for(const r of visible){const item=text('li','');item.className='record';item.append(text('h3',r.sourceId+' — '+r.date));item.append(text('p',r.claim));const details=text('p','Type: '+r.kind+' · Status: '+r.status+(r.group?' · Group: '+r.group:''));item.append(details);
    const statusSelect=document.createElement('select');
    statusSelect.setAttribute('aria-label','Review status for record '+r.sourceId);
    statusSelect.dataset.sourceId=r.sourceId;
    for(const status of STATUS_OPTIONS){const option=text('option',status);option.value=status;statusSelect.append(option);}
    statusSelect.value=r.status;
    statusSelect.addEventListener('change',()=>{
      try{
        const hadFilter=$('review-filter').value!=='all';
        const change=changeReviewStatus(records,r.sourceId,statusSelect.value);
        records=change.records;
        if(change.undo)offerStatusUndo(change.undo);else clearStatusUndo();
        if(hadFilter)$('review-filter').value='all';
        render();
        const replacement=[...list.querySelectorAll('select[data-source-id]')].find(element=>element.dataset.sourceId===r.sourceId);
        (replacement||$('count')).focus();
        $('change-status-message').textContent='Review status updated. '+(hadFilter?'All statuses are now shown.':'');
      }catch(e){$('change-status-message').textContent='Review status could not be updated.';render();$('count').focus();}
    });
    item.append(statusSelect);
    const editGroup=text('button','Edit group for '+r.sourceId);
    editGroup.type='button';
    editGroup.dataset.editGroup=r.sourceId;
    editGroup.addEventListener('click',()=>beginGroupEdit(r));
    item.append(editGroup);
    const remove=text('button','Remove '+r.sourceId);remove.type='button';remove.setAttribute('aria-label','Remove record '+r.sourceId);remove.addEventListener('click',()=>{if(!window.confirm('Remove this record from this tab? This cannot be undone unless you have an export.'))return;records=records.filter(x=>x.sourceId!==r.sourceId);if(editingGroupId===r.sourceId)stopGroupEdit();clearStatusUndo();render();$('count').focus();});item.append(remove);list.append(item);}
  const risk=csvExportRisk(records);
  $('csv').disabled=records.length===0||Boolean(risk);
  $('json').disabled=records.length===0;
  $('download-readable').disabled=records.length===0;
  if($('download-filtered'))$('download-filtered').disabled=visible.length===0;
  $('clear').disabled=records.length===0;
  $('csv-warning').textContent=risk?'CSV unavailable: '+risk.field+' contains '+risk.reason+'. Download exact JSON instead.':'';
}
// Restore the full chronology in one action without changing any evidence.
const resetFiltersButton=text('button','Show all records (clear filters)');
resetFiltersButton.type='button';
resetFiltersButton.id='reset-all-filters';
const resetFiltersHelp=text('p','Clears source ID, group, ungrouped-only, and review-status filters without editing records.');
resetFiltersHelp.id='reset-filters-help';
resetFiltersButton.setAttribute('aria-describedby','reset-filters-help');
$('review-filter').after(resetFiltersButton,resetFiltersHelp);
resetFiltersButton.addEventListener('click',()=>{
  $('review-filter').value='all';
  $('source-find').value='';
  $('group-find').value='';
  $('group-find').disabled=false;
  $('ungrouped-only').checked=false;
  render();
  $('count').focus();
  $('change-status-message').textContent='All chronology filters cleared. Evidence records are unchanged.';
});
$('count').tabIndex=-1;
$('review-filter').addEventListener('change',render);
$('source-find').addEventListener('input',render);
$('clear-source-find').addEventListener('click',()=>{$('source-find').value='';render();$('source-find').focus();});
$('group-find').addEventListener('input',render);
$('ungrouped-only').addEventListener('change',()=>{
  if($('ungrouped-only').checked)$('group-find').value='';
  $('group-find').disabled=$('ungrouped-only').checked;
  render();
});
function clearGroupFilter(){
  $('group-find').value='';$('group-find').disabled=false;$('ungrouped-only').checked=false;
}
$('clear-group-find').addEventListener('click',()=>{clearGroupFilter();render();$('group-find').focus();});
$('group-edit-value').addEventListener('input',()=>{
  // The previous rejection describes the old value, not the edited draft.
  if($('group-edit-error').hidden)return;
  $('group-edit-error').hidden=true;
  $('group-edit-error').textContent='';
  $('group-edit-value').removeAttribute('aria-invalid');
  $('group-edit-value').setAttribute('aria-describedby','group-edit-help');
});
$('group-edit-form').addEventListener('submit',event=>{
  event.preventDefault();
  if(editingGroupId===null)return;
  const sourceId=editingGroupId;
  try{
    records=setReviewGroup(records,sourceId,$('group-edit-value').value);
    clearStatusUndo();
    stopGroupEdit();
    const groupFilterWasActive=$('group-find').value!=='' || $('ungrouped-only').checked;
    if(groupFilterWasActive)clearGroupFilter();
    render();
    focusGroupEditButton(sourceId);
    $('change-status-message').textContent='Related-record group saved for '+sourceId+'.'+(groupFilterWasActive?' Group filter cleared so the edited record remains visible.':'');
  }catch(e){
    $('group-edit-error').textContent='Group not saved: '+String(e.message||e);
    $('group-edit-error').hidden=false;
    $('group-edit-value').setAttribute('aria-invalid','true');
    $('group-edit-value').setAttribute('aria-describedby','group-edit-help group-edit-error');
    $('group-edit-error').focus();
  }
});
$('cancel-group-edit').addEventListener('click',()=>{
  const sourceId=editingGroupId;
  stopGroupEdit();
  focusGroupEditButton(sourceId);
  $('change-status-message').textContent='Group edit cancelled. No evidence changed.';
});
$('undo-status').addEventListener('click',()=>{
  const change=pendingStatusUndo;
  try{
    records=undoReviewStatus(records,change);
    clearStatusUndo();
    $('review-filter').value='all';
    render();
    const replacement=[...list.querySelectorAll('select[data-source-id]')].find(element=>element.dataset.sourceId===change.sourceId);
    (replacement||$('count')).focus();
    $('change-status-message').textContent='Last review status change undone. All statuses are now shown.';
  }catch(e){clearStatusUndo();$('change-status-message').textContent='Undo is no longer available because records changed.';$('count').focus();}
});
form.addEventListener('submit',event=>{
  event.preventDefault();clearError();
  const data=Object.fromEntries(new FormData(form).entries());
  for(const [id,label] of [['sourceId','Source ID'],['date','Record date'],['claim','Record description']]){
    if(!String(data[id]??'').trim()){showError(label+' is required.',id);return;}
  }
  try{records=normalizeEvidence([...records,data]);clearStatusUndo();form.reset();$('source-find').value='';clearGroupFilter();render();$('sourceId').focus();}
  catch(e){const message=String(e.message||e);const field=/source ID/i.test(message)?'sourceId':/date/i.test(message)?'date':/claim/i.test(message)?'claim':null;showError(message,field);}
});
function exportRecords(kind) {
  const failure=$('export-error'), status=$('export-status');
  failure.hidden=true;failure.textContent='';status.textContent='';
  try {
    const csv=kind==='csv';
    const content=csv?exportSafeEvidenceCSV(records):JSON.stringify({schema:'evidence-timeline-v1',records},null,2)+'\n';
    startLocalDownload({filename:csv?'evidence-timeline-spreadsheet.csv':'evidence-timeline-exact.json',
      content,type:csv?'text/csv;charset=utf-8':'application/json'});
    status.textContent=(csv?'CSV':'Exact JSON')+' download started. Check your browser downloads; saving is not guaranteed.';
  } catch {
    failure.textContent=(kind==='csv'?'CSV':'Exact JSON')+' download could not be started. Your records are unchanged. Try again or use the other export when available.';
    failure.hidden=false;failure.focus();
  }
}
// Human-readable, exact-value timeline for reviewing evidence without a spreadsheet.
const readableButton=text('button','Download readable timeline');
readableButton.type='button';
readableButton.id='download-readable';
readableButton.disabled=true;
readableButton.setAttribute('aria-describedby','readable-help');
const readableHelp=text('p','Downloads a local plain-text chronology with exact JSON-quoted source IDs and descriptions. All records are included, regardless of filters. This is a review aid, not a finding.');
readableHelp.id='readable-help';
$('json').after(readableButton);
$('csv-warning').before(readableHelp);
function readableTimeline(rows,partial=false){
  const ordered=[...rows].sort((a,b)=>a.date.localeCompare(b.date)||a.sourceId.localeCompare(b.sourceId));
  const lines=['Evidence & Timeline Builder — readable chronology','Local review only; no facts or relationships independently verified.',partial?'PARTIAL VIEW: only records matching current filters are included. Dates are calendar dates without times or time zones.':'All records included regardless of visible filters. Dates are calendar dates without times or time zones.','Source values are JSON-quoted to preserve punctuation, whitespace, and control-character distinctions.','Records: '+ordered.length,''];
  for(const [index,r] of ordered.entries()){
    lines.push((index+1)+'. '+r.date+' | Source ID: '+JSON.stringify(r.sourceId));
    lines.push('   Type: '+r.kind+' | User-assigned status: '+r.status);
    lines.push('   Related-record group: '+JSON.stringify(r.group||''));
    lines.push('   Description: '+JSON.stringify(r.claim),'');
  }
  lines.push('Review classifications and group labels are user-assigned; this document makes no legal, medical, or financial determination.');
  return lines.join('\n')+'\n';
}
// A partial extract is distinct from the complete evidence archive.
const viewButton=text('button','Download filtered view');
viewButton.type='button';viewButton.id='download-filtered';viewButton.disabled=true;
viewButton.setAttribute('aria-describedby','filtered-download-help');
const viewHelp=text('p','Downloads only records currently matching the source ID, group and review-status filters. This partial extract excludes hidden records; use Download readable timeline for a complete chronology.');
viewHelp.id='filtered-download-help';
readableButton.after(viewButton,viewHelp);
viewButton.addEventListener('click',()=>{
  $('export-error').hidden=true;$('export-error').textContent='';$('export-status').textContent='';
  try{
    const visible=filterByGroupLabel(findSourceIds(records,$('review-filter').value,$('source-find').value),$('group-find').value,$('ungrouped-only').checked);
    if(!visible.length)throw Error('No visible records');
    const preface='PARTIAL FILTERED VIEW — '+visible.length+' of '+records.length+' records. Hidden records are NOT included.\n';
    startLocalDownload({filename:'evidence-timeline-filtered-view.txt',content:preface+readableTimeline(visible,true),type:'text/plain;charset=utf-8'});
    $('export-status').textContent='Partial filtered-view download started. Check browser downloads; saving is not guaranteed.';
  }catch{
    $('export-error').textContent='Filtered-view download could not be started. Your records are unchanged. Use the complete readable timeline or exact JSON instead.';
    $('export-error').hidden=false;$('export-error').focus();
  }
});
readableButton.addEventListener('click',()=>{
  $('export-error').hidden=true;$('export-error').textContent='';$('export-status').textContent='';
  try{
    if(!records.length)throw Error('No records to export');
    startLocalDownload({filename:'evidence-timeline-readable.txt',content:readableTimeline(records),type:'text/plain;charset=utf-8'});
    $('export-status').textContent='Readable timeline download started. Check your browser downloads; saving is not guaranteed.';
  }catch{
    $('export-error').textContent='Readable timeline download could not be started. Your records are unchanged. Try again or use exact JSON.';
    $('export-error').hidden=false;$('export-error').focus();
  }
});
$('csv').addEventListener('click',()=>exportRecords('csv'));
$('json').addEventListener('click',()=>exportRecords('json'));
$('clear').addEventListener('click',()=>{if(window.confirm('Clear all records from this tab? Export first if you need them.')){records=[];stopGroupEdit();clearStatusUndo();$('review-filter').value='all';$('source-find').value='';clearGroupFilter();render();$('sourceId').focus();}});

const timeline=document.querySelector('[aria-labelledby="timeline-heading"]');
const section=document.createElement('section');
section.setAttribute('aria-labelledby','resume-heading');
const heading=document.createElement('h2');heading.id='resume-heading';heading.textContent='Resume from a JSON export';
const instructions=document.createElement('p');instructions.id='resume-json-help';instructions.textContent='Choose a JSON file exported by this tool. Files stay in this tab. Import replaces existing records only after confirmation.';
const label=document.createElement('label');label.htmlFor='resume-json';label.textContent='Evidence Timeline JSON file';
const input=document.createElement('input');input.type='file';input.id='resume-json';input.accept='.json,application/json';
section.append(heading,instructions,label,input);
const importFeedback=createImportFeedback(input,instructions,section);
timeline.before(section);
input.addEventListener('change',async()=>{
 const file=input.files?.[0];if(!file)return;
 importFeedback.begin();
 const initialRecords=records;
 input.disabled=true;
 try{
   const next=await readExactJSON(file);
   if(records!==initialRecords) throw Error('Records changed while reading the file. Choose the file again to review the current records.');
   const impact=previewReplacement(records,next);
   if(window.confirm(replacementConfirmation(impact))){
     records=next;
     stopGroupEdit();
     clearStatusUndo();
     // A filter from the replaced working set must not conceal imported evidence.
     $('review-filter').value='all';
     $('source-find').value='';
     clearGroupFilter();
     render();$('count').focus();
     importFeedback.announce(next.length+' records imported locally. All review statuses are now shown.');
   }else importFeedback.announce('Import cancelled; existing records retained.');
 }catch(e){importFeedback.fail(String(e.message||e));}
 finally{input.value='';input.disabled=false;}
});

/* Fictional, explicitly unverified evidence for learning the complete workflow. */
const exampleRecords = [
  {sourceId:'EXAMPLE-MINUTES-001',date:'2026-01-12',claim:'Fictional committee minutes record a proposed opening date of March 1.',status:'reported',kind:'source',group:'opening-date'},
  {sourceId:'EXAMPLE-EMAIL-002',date:'2026-01-19',claim:'A fictional email proposes moving the opening date to March 15. This does not establish the actual date.',status:'unresolved',kind:'source',group:'opening-date'},
  {sourceId:'EXAMPLE-NOTE-003',date:'2026-01-20',claim:'An imaginary reviewer notes that the two proposed dates need verification against a final decision.',status:'unresolved',kind:'observation',group:'opening-date'}
];
const exampleButton=text('button','Try fictional example');
exampleButton.type='button';
exampleButton.id='load-example';
exampleButton.setAttribute('aria-describedby','example-help');
const exampleHelp=text('p','Loads three fictional records with exact source IDs and a shared review group. This replaces your current records only after confirmation. Export your work first.');
exampleHelp.id='example-help';
form.after(exampleButton,exampleHelp);
exampleButton.addEventListener('click',()=>{
  if(records.length && !window.confirm('Replace all current records with three fictional examples? Export your work first if you need it.')) {
    $('change-status-message').textContent='Example cancelled. Your records are unchanged.';
    return;
  }
  records=normalizeEvidence(exampleRecords);
  stopGroupEdit();
  clearStatusUndo();
  $('review-filter').value='all';
  $('source-find').value='';
  clearGroupFilter();
  render();
  $('count').focus();
  $('change-status-message').textContent='Three fictional records loaded locally. Compare the related opening-date records, change their review status, then export your work.';
});

render();
