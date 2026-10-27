import {emptyWorkspace,validateWorkspace,chronology,reviewFlags} from './core.mjs';
import {bindReopen} from './reopen-ui.mjs';
import {bindExports} from './export-ui.mjs';
let state=emptyWorkspace();
const byId=id=>document.getElementById(id);
const say=message=>{byId('status').textContent=message;};
const field=(form,name)=>form.elements.namedItem(name).value;
const node=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;return el;};
function renderEvent(e,list,draft){
  const item=document.createElement('li');
  item.dataset.eventId=e.id;
  item.append(node('p',`${e.date} — Event ${e.id} — Request ${e.requestId} — ${e.kind}: ${e.description}${e.sourceId?' [source '+e.sourceId+']':''}`));
  const details=document.createElement('details');
  const summary=node('summary',`Correct event ${e.id}`);
  details.append(summary);
  const editor=document.createElement('div');
  editor.className='event-editor';
  const control=(labelText,tag,value,max)=>{
    const label=node('label',labelText);
    const input=document.createElement(tag);
    if(tag==='input'){input.type='text';input.maxLength=max;}
    if(tag==='textarea'){input.maxLength=max;}
    input.value=value;label.append(input);editor.append(label);
    return input;
  };
  const dateInput=control('Event date (YYYY-MM-DD)', 'input',e.date,10);
  dateInput.inputMode='numeric';
  const kindLabel=node('label','Event type');
  const kindSelect=document.createElement('select');
  for(const kind of ['submitted','acknowledged','agency-message','clarification','response','appeal','note']){
    const option=node('option',kind);option.value=kind;kindSelect.append(option);
  }
  kindSelect.value=e.kind;kindLabel.append(kindSelect);editor.append(kindLabel);
  const sourceInput=control('Evidence/source ID (optional; exact text)', 'input',e.sourceId,200);
  const descriptionInput=control('What happened?', 'textarea',e.description,5000);
  const save=node('button','Save event correction');
  save.type='button';
  const cancel=node('button','Cancel event correction');
  cancel.type='button';
  const error=node('p','');
  error.className='form-error';error.setAttribute('role','alert');
  error.tabIndex=-1;error.hidden=true;
  save.addEventListener('click',()=>{
    if(dateInput.value===e.date && kindSelect.value===e.kind &&
       sourceInput.value===e.sourceId && descriptionInput.value===e.description){
      say(`No changes to event ${e.id}.`);return;
    }
    for(const input of [dateInput,kindSelect,sourceInput,descriptionInput])input.removeAttribute('aria-invalid');
    try{
      const next=validateWorkspace({...state,events:state.events.map(event=>
        event.id===e.id?{...event,date:dateInput.value,kind:kindSelect.value,
          sourceId:sourceInput.value,description:descriptionInput.value}:event)});
      state=next;render({discardEventDraftId:e.id});
      const updated=[...byId('events').children].find(li=>li.dataset.eventId===e.id);
      updated?.querySelector('summary')?.focus();
      say(`Corrected event ${e.id}. Its event ID and related request were preserved; review the updated chronology and documentation flags.`);
    }catch(failure){
      const message=String(failure.message);
      if(/event date/i.test(message))dateInput.setAttribute('aria-invalid','true');
      if(/source ID/i.test(message))sourceInput.setAttribute('aria-invalid','true');
      if(/event description/i.test(message))descriptionInput.setAttribute('aria-invalid','true');
      error.textContent=/event date/i.test(message)
        ? 'Event date is invalid. Use YYYY-MM-DD for a real calendar date.'
        : /source ID/i.test(message)
          ? 'Source ID is invalid. Use at most 200 characters and no null characters.'
          : /event description/i.test(message)
            ? 'Event description is required (up to 5,000 characters; no null characters).'
            : 'Event correction was not saved. Review the event fields.';
      error.hidden=false;
      say('Event correction not saved; original records and evidence were kept.');
      error.focus();
    }
  });
  cancel.addEventListener('click',()=>{
    render({discardEventDraftId:e.id});
    const restored=[...byId('events').children].find(li=>li.dataset.eventId===e.id);
    restored?.querySelector('summary')?.focus();
    say(`Cancelled changes to event ${e.id}; no records were changed.`);
  });
  // Unsaved edits are transient UI state, never part of JSON/CSV evidence.
  if(draft){
    details.open=true;
    dateInput.value=draft.date;
    kindSelect.value=draft.kind;
    sourceInput.value=draft.sourceId;
    descriptionInput.value=draft.description;
    for(const [input,invalid] of [[dateInput,draft.invalidDate],
      [sourceInput,draft.invalidSource],[descriptionInput,draft.invalidDescription]]){
      if(invalid)input.setAttribute('aria-invalid','true');
    }
    if(draft.error){error.textContent=draft.error;error.hidden=false;}
  }
  editor.append(save,cancel,error);details.append(editor);item.append(details);list.append(item);
}
function captureEventDrafts(){
  const drafts=new Map();
  for(const item of byId('events').children){
    const details=item.querySelector('details');
    if(!details?.open)continue;
    const editor=details.querySelector('.event-editor');
    if(!editor)continue;
    const inputs=editor.querySelectorAll('input');
    const kind=editor.querySelector('select');
    const description=editor.querySelector('textarea');
    const error=editor.querySelector('[role="alert"]');
    if(inputs.length!==2 || !kind || !description || !error)continue;
    drafts.set(item.dataset.eventId,{
      date:inputs[0].value,kind:kind.value,sourceId:inputs[1].value,
      description:description.value,
      invalidDate:inputs[0].getAttribute('aria-invalid')==='true',
      invalidSource:inputs[1].getAttribute('aria-invalid')==='true',
      invalidDescription:description.getAttribute('aria-invalid')==='true',
      error:error.hidden?'':error.textContent
    });
  }
  return drafts;
}
function captureRequestDrafts(){
  // Preserve user-entered request fields across unrelated list rerenders.
  // Drafts are DOM-only and are never part of downloaded evidence.
  const drafts=new Map();
  for(const card of byId('requests').querySelectorAll('.card[data-request-id]')){
    const stage=card.querySelector('.request-stage');
    const inputs=card.querySelectorAll('input');
    const error=card.querySelector('[role="alert"]');
    if(!stage || inputs.length!==2 || !error)continue;
    drafts.set(card.dataset.requestId,{
      stage:stage.value,submittedOn:inputs[0].value,agencyTrackingId:inputs[1].value,
      invalidDate:inputs[0].getAttribute('aria-invalid')==='true',
      error:error.hidden?'':error.textContent
    });
  }
  return drafts;
}
function render({discardEventDraftId=null,discardRequestDraftId=null}={}){
  const requestDrafts=captureRequestDrafts();
  if(discardRequestDraftId!==null)requestDrafts.delete(discardRequestDraftId);
  const drafts=captureEventDrafts();
  if(discardEventDraftId!==null)drafts.delete(discardEventDraftId);
  const requestList=byId('requests'), eventList=byId('events'), flagList=byId('flags'), selector=byId('request-select');
  requestList.replaceChildren();eventList.replaceChildren();flagList.replaceChildren();
  const selected=selector.value;selector.replaceChildren(node('option','Select a request'));selector.firstChild.value='';
  state.requests.forEach((r,index)=>{
    const card=document.createElement('div');
    card.className='card';card.dataset.requestId=r.id;
    card.append(node('p',`${r.id} — ${r.agency} (${r.jurisdiction}; ${r.stage}) — ${r.description}`));
    const statusLabel=node('label',`Tracking status for request ${r.id}`);
    const statusSelect=document.createElement('select');
    statusSelect.className='request-stage';
    for(const stage of ['draft','submitted','acknowledged','processing','responded','closed','unknown']){
      const option=node('option',stage);option.value=stage;statusSelect.append(option);
    }
    statusSelect.value=r.stage;
    statusLabel.append(statusSelect);
    const dateLabel=node('label','Submission date (YYYY-MM-DD; blank if unknown)');
    const dateInput=document.createElement('input');
    dateInput.type='text';dateInput.inputMode='numeric';dateInput.maxLength=10;
    dateInput.placeholder='YYYY-MM-DD';dateInput.value=r.submittedOn;
    dateLabel.append(dateInput);
    const trackingLabel=node('label','Agency tracking ID (optional; preserved exactly)');
    const trackingInput=document.createElement('input');
    trackingInput.type='text';trackingInput.maxLength=200;trackingInput.value=r.agencyTrackingId;
    trackingLabel.append(trackingInput);
    const error=node('p','');
    error.className='form-error';error.setAttribute('role','alert');
    error.tabIndex=-1;error.hidden=true;
    const save=node('button','Save request changes');
    save.type='button';
    save.setAttribute('aria-label',`Save request changes for request ${r.id}`);
    save.addEventListener('click',()=>{
      const changed=statusSelect.value!==r.stage || dateInput.value!==r.submittedOn ||
        trackingInput.value!==r.agencyTrackingId;
      if(!changed){say(`No status change or detail change for request ${r.id}.`);return;}
      dateInput.removeAttribute('aria-invalid');
      try{
        const next=validateWorkspace({...state,requests:state.requests.map(item=>
          item.id===r.id?{...item,stage:statusSelect.value,submittedOn:dateInput.value,
            agencyTrackingId:trackingInput.value}:item)});
        state=next;
        render({discardRequestDraftId:r.id});
        requestList.children[index]?.querySelector('button')?.focus();
        say(`Updated tracking status or request details for request ${r.id}. Review the documentation flags; these are your records, not agency determinations.`);
      }catch(failure){
        error.textContent=/submitted date/i.test(failure.message)
          ? 'Submission date is invalid. Use YYYY-MM-DD for a real calendar date, or leave it blank.'
          : 'Request changes were not saved. Check the tracking ID (200 characters maximum) and selected status.';
        if(/submitted date/i.test(failure.message))dateInput.setAttribute('aria-invalid','true');
        error.hidden=false;
        say('Request changes not saved; the original records and evidence were kept.');
        error.focus();
      }
    });
    const requestDraft=requestDrafts.get(r.id);
    if(requestDraft){
      statusSelect.value=requestDraft.stage;
      dateInput.value=requestDraft.submittedOn;
      trackingInput.value=requestDraft.agencyTrackingId;
      if(requestDraft.invalidDate)dateInput.setAttribute('aria-invalid','true');
      if(requestDraft.error){error.textContent=requestDraft.error;error.hidden=false;}
    }
    card.append(statusLabel,dateLabel,trackingLabel,save,error);requestList.append(card);
    const opt=node('option',`${r.id} — ${r.agency}`);opt.value=r.id;selector.append(opt);
  });
  if([...selector.options].some(x=>x.value===selected)) selector.value=selected;
  for(const e of chronology(state)) renderEvent(e,eventList,drafts.get(e.id));
  for(const item of reviewFlags(state)) flagList.append(node('li',`${item.requestId}: ${item.flags.join('; ')}`));
  if(!state.requests.length)requestList.append(node('p','No requests yet.'));
  if(!state.events.length)eventList.append(node('li','No dated events yet.'));
  if(!flagList.children.length)flagList.append(node('li','No missing-documentation flags. This does not establish completeness.'));
}
function add(formId,kind){
  const form=byId(formId), errorMessage=byId(kind+'-error');
  form.addEventListener('submit',event=>{
    event.preventDefault();
    try{
      const r=kind==='request'?{
        id:field(form,'id'),jurisdiction:field(form,'jurisdiction'),agency:field(form,'agency'),stage:field(form,'stage'),submittedOn:field(form,'submittedOn'),agencyTrackingId:field(form,'agencyTrackingId'),description:field(form,'description')
      }:{
        id:field(form,'id'),requestId:field(form,'requestId'),date:field(form,'date'),kind:field(form,'kind'),sourceId:field(form,'sourceId'),description:field(form,'description')
      };
      const collection=kind==='request'?'requests':'events';
      const next={...state,[collection]:[...state[collection],r]};
      state=validateWorkspace(next);
      errorMessage.hidden=true;
      errorMessage.textContent='';
      form.reset();
      render();
      say(`Added ${kind} ${r.id}.`);
    }catch(error){
      // Keep the entered values and exact existing workspace. Never echo user input in an error.
      errorMessage.textContent=`Cannot add ${kind}: ${error.message}. Correct the fields and try again; nothing was added.`;
      errorMessage.hidden=false;
      say(`${kind==='request'?'Request':'Event'} not added. Review the form error.`);
      errorMessage.focus();
    }
  });
}
add('request-form','request');add('event-form','event');
bindExports(()=>state,say);
bindReopen(()=>state, next=>{state=next;render();},say);
render();
