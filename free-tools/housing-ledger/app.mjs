import {buildHousingLedger,exportHousingJSON,reviseHousingEvent} from './housing-core.mjs';
import {readHousingJSONFile} from './housing-import.mjs';
const sources=[]; const events=[];
let mutationVersion=0; let importRequest=0; let editingEventId=null;
let editingOriginalDescription=null; let editingDisplayedDescription=null;
const $=id=>document.getElementById(id);
const error=$('error'),status=$('status');
const message=(msg)=>{error.hidden=false;error.textContent=msg;error.focus();};
const clearError=()=>{error.hidden=true;error.textContent='';};
const addText=(parent,tag,value)=>{const el=document.createElement(tag);el.textContent=value;parent.append(el);return el;};
function showList(id,items,empty,render){const root=$(id);root.replaceChildren();if(!items.length){addText(root,'li',empty);return;}for(const item of items){const li=document.createElement('li');render(li,item);root.append(li);}}
function render(){const ledger=buildHousingLedger({sources,events});
  showList('sources-list',ledger.sources,'No sources yet.',(li,s)=>addText(li,'span',`${s.sourceId} — ${s.kind}${s.date?' — '+s.date:''}${s.label?' — '+s.label:''}`));
  showList('events-list',ledger.events,'No events yet.',(li,e)=>{
    addText(li,'span',`${e.date} — ${e.eventId} — ${e.category} — ${e.description||'(no description)'} — ${e.amountCents===null?'amount unknown':e.amountCents+' cents'} — sources: ${e.sourceIds.length?e.sourceIds.join(' | '):'none'}`);
    const button=addText(li,'button',`Edit event ${e.eventId}`);
    button.type='button'; button.dataset.eventId=e.eventId;
    button.addEventListener('click',()=>openEventEditor(e.eventId));
  });
  showList('findings-list',ledger.findings,'No review flags.',(li,f)=>addText(li,'span',`${f.eventId}: ${f.kind==='unlinked-evidence'?'No linked source evidence':'Deposit amount not provided'}`));
  status.textContent=`${ledger.sources.length} sources, ${ledger.events.length} events, ${ledger.findings.length} review flags. Data remains in this browser tab.`;
  return ledger;
}
function attempt(fn){try{clearError();fn();render();}catch(e){message(`Could not complete action: ${e instanceof Error?e.message:'Invalid input'}. Existing records were kept.`);}}
$('source-form').addEventListener('submit',e=>{e.preventDefault();const f=e.currentTarget;attempt(()=>{const entry={sourceId:$('source-id').value,kind:$('source-kind').value,label:$('source-label').value,date:$('source-date').value||null};buildHousingLedger({sources:[...sources,entry],events});sources.push(entry);mutationVersion++;f.reset();});});
$('event-form').addEventListener('submit',e=>{e.preventDefault();const f=e.currentTarget;attempt(()=>{const raw=$('amount').value; if(raw && !/^[0-9]{1,12}$/.test(raw))throw Error('Amount must be whole cents');const amountCents=raw===''?null:Number(raw);const links=$('source-links').value===''?[]:$('source-links').value.split(/\r?\n/u);const entry={eventId:$('event-id').value,date:$('event-date').value,category:$('category').value,description:$('description').value,sourceIds:links,amountCents};buildHousingLedger({sources,events:[...events,entry]});events.push(entry);mutationVersion++;f.reset();});});
function eventButton(eventId){
  return [...$('events-list').querySelectorAll('button[data-event-id]')].find(b=>b.dataset.eventId===eventId);
}
function closeEventEditor(focusButton=false){
  const id=editingEventId;
  editingEventId=null;
  editingOriginalDescription=null; editingDisplayedDescription=null;
  $('event-edit-form').reset();
  $('event-editor').hidden=true;
  if(focusButton && id!==null) eventButton(id)?.focus();
}
function openEventEditor(eventId){
  const event=buildHousingLedger({sources,events}).events.find(e=>e.eventId===eventId);
  if(!event) return;
  editingEventId=eventId;
  $('edit-event-id').textContent=eventId;
  $('edit-event-date').value=event.date;
  $('edit-description').value=event.description;
  editingOriginalDescription=event.description;
  editingDisplayedDescription=$('edit-description').value;
  $('edit-amount').value=event.amountCents===null?'':String(event.amountCents);
  $('edit-source-links').value=event.sourceIds.join('\n');
  $('event-editor').hidden=false;
  clearError();
  $('edit-event-date').focus();
}
$('event-edit-cancel').addEventListener('click',()=>closeEventEditor(true));
$('event-edit-form').addEventListener('submit',e=>{
  e.preventDefault();
  if(editingEventId===null)return;
  const id=editingEventId,raw=$('edit-amount').value;
  try {
    if(raw!=='' && !/^[0-9]{1,12}$/u.test(raw)) throw Error('Amount must be whole cents');
    const changes={
      date:$('edit-event-date').value,
      description:$('edit-description').value===editingDisplayedDescription?editingOriginalDescription:$('edit-description').value,
      amountCents:raw===''?null:Number(raw),
      sourceIds:$('edit-source-links').value===''?[]:$('edit-source-links').value.split(/\r?\n/u)
    };
    const ledger=reviseHousingEvent({sources,events},id,changes);
    events.splice(0,events.length,...ledger.events);
    mutationVersion++;
    clearError();
    render();
    closeEventEditor(true);
    status.textContent+=` Event ${id} updated; review flags recalculated.`;
  } catch(err) {
    message(`Could not update event ${id}: ${err instanceof Error?err.message:'Invalid input'}. Existing records were kept.`);
  }
});

$('import').addEventListener('click',async()=>{
  const file=$('import-file').files?.[0];
  const request=++importRequest, version=mutationVersion;
  clearError();
  status.textContent='Checking selected JSON locally. Existing records are unchanged.';
  try {
    const ledger=await readHousingJSONFile(file);
    if (request!==importRequest || version!==mutationVersion) {
      throw Error('Records changed while the file was being read; select the file again');
    }
    if (!window.confirm('Replace ALL records in this tab with the selected JSON? Export a copy first if needed.')) {
      render();
      status.textContent+=' Import canceled; existing records were kept.';
      return;
    }
    sources.splice(0,sources.length,...ledger.sources);
    events.splice(0,events.length,...ledger.events);
    closeEventEditor();
    mutationVersion++;
    render();
    status.textContent+=' JSON reopened successfully. Existing records were replaced.';
  } catch (e) {
    render();
    message(`Could not reopen JSON: ${e instanceof Error?e.message:'Invalid input'}. Existing records were kept.`);
  } finally {
    $('import-file').value='';
  }
});
$('download').addEventListener('click',()=>{attempt(()=>{const blob=new Blob([exportHousingJSON(buildHousingLedger({sources,events}))],{type:'application/json;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='housing-evidence-ledger.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);});});
$('clear').addEventListener('click',()=>{if(!sources.length&&!events.length)return;if(!window.confirm('Clear all sources and events from this tab? Export JSON first if you need a copy.'))return; sources.length=0;events.length=0;mutationVersion++;closeEventEditor();clearError();render();});
render();
