import {summary} from './core.mjs';
import {csvExportRisk,exportSafeEvidenceCSV} from './safe-export.mjs';
import {normalizeExact as normalizeEvidence} from './exact-core.mjs';
import {readExactJSON} from './json-import.mjs';
import {createImportFeedback} from './import-feedback.mjs';
import {previewReplacement, replacementConfirmation} from './replacement-preview.mjs';
import {reviewStatusSummary} from './review-filter.mjs';
import {findSourceIds} from './source-id-find.mjs';
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
  const visible=findSourceIds(records,selected,query);
  $('clear-source-find').disabled=query==='';
  $('count').textContent=selected==='all' && query==='' ? report.total+' '+(report.total===1?'record':'records')+' (date order).' : 'Showing '+visible.length+' of '+report.total+' records (date order).';
  $('review-summary').textContent=reviewStatusSummary(records);
  $('groups').textContent=report.reviewGroups.length?report.reviewGroups.map(g=>'Review group '+g.group+': '+g.sourceIds.join(', ')).join(' · '):'No related-record groups to review.';
  $('empty').hidden=visible.length>0;
  $('empty').textContent=records.length===0 ? 'No records yet. Add a record to build your timeline.' : 'No records match the selected review status or source ID. Clear the source search or choose All statuses.';
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
  $('clear').disabled=records.length===0;
  $('csv-warning').textContent=risk?'CSV unavailable: '+risk.field+' contains '+risk.reason+'. Download exact JSON instead.':'';
}
$('count').tabIndex=-1;
$('review-filter').addEventListener('change',render);
$('source-find').addEventListener('input',render);
$('clear-source-find').addEventListener('click',()=>{$('source-find').value='';render();$('source-find').focus();});
$('group-edit-form').addEventListener('submit',event=>{
  event.preventDefault();
  if(editingGroupId===null)return;
  const sourceId=editingGroupId;
  try{
    records=setReviewGroup(records,sourceId,$('group-edit-value').value);
    clearStatusUndo();
    stopGroupEdit();
    render();
    focusGroupEditButton(sourceId);
    $('change-status-message').textContent='Related-record group saved for '+sourceId+'.';
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
  try{records=normalizeEvidence([...records,data]);clearStatusUndo();form.reset();$('source-find').value='';render();$('sourceId').focus();}
  catch(e){const message=String(e.message||e);const field=/source ID/i.test(message)?'sourceId':/date/i.test(message)?'date':/claim/i.test(message)?'claim':null;showError(message,field);}
});
function download(filename,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
$('csv').addEventListener('click',()=>download('evidence-timeline-spreadsheet.csv',exportSafeEvidenceCSV(records),'text/csv;charset=utf-8'));
$('json').addEventListener('click',()=>download('evidence-timeline-exact.json',JSON.stringify({schema:'evidence-timeline-v1',records},null,2)+'\n','application/json'));
$('clear').addEventListener('click',()=>{if(window.confirm('Clear all records from this tab? Export first if you need them.')){records=[];stopGroupEdit();clearStatusUndo();$('review-filter').value='all';$('source-find').value='';render();$('sourceId').focus();}});

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
     render();$('count').focus();
     importFeedback.announce(next.length+' records imported locally. All review statuses are now shown.');
   }else importFeedback.announce('Import cancelled; existing records retained.');
 }catch(e){importFeedback.fail(String(e.message||e));}
 finally{input.value='';input.disabled=false;}
});

render();
