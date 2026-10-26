import {emptyWorkspace,validateWorkspace,chronology,reviewFlags} from './core.mjs';
import {bindReopen} from './reopen-ui.mjs';
import {bindExports} from './export-ui.mjs';
let state=emptyWorkspace();
const byId=id=>document.getElementById(id);
const say=message=>{byId('status').textContent=message;};
const field=(form,name)=>form.elements.namedItem(name).value;
const node=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;return el;};
function render(){
  const requestList=byId('requests'), eventList=byId('events'), flagList=byId('flags'), selector=byId('request-select');
  requestList.replaceChildren();eventList.replaceChildren();flagList.replaceChildren();
  const selected=selector.value;selector.replaceChildren(node('option','Select a request'));selector.firstChild.value='';
  state.requests.forEach((r,index)=>{
    const card=document.createElement('div');
    card.className='card';
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
        render();
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
    card.append(statusLabel,dateLabel,trackingLabel,save,error);requestList.append(card);
    const opt=node('option',`${r.id} — ${r.agency}`);opt.value=r.id;selector.append(opt);
  });
  if([...selector.options].some(x=>x.value===selected)) selector.value=selected;
  for(const e of chronology(state)) eventList.append(node('li',`${e.date} — Event ${e.id} — Request ${e.requestId} — ${e.kind}: ${e.description}${e.sourceId?' [source '+e.sourceId+']':''}`));
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
