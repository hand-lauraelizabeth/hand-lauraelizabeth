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
  for(const r of state.requests){
    const card=node('div',`${r.id} — ${r.agency} (${r.jurisdiction}; ${r.stage}) — ${r.description}`);
    card.className='card';requestList.append(card);
    const opt=node('option',`${r.id} — ${r.agency}`);opt.value=r.id;selector.append(opt);
  }
  if([...selector.options].some(x=>x.value===selected)) selector.value=selected;
  for(const e of chronology(state)) eventList.append(node('li',`${e.date} — Event ${e.id} — Request ${e.requestId} — ${e.kind}: ${e.description}${e.sourceId?' [source '+e.sourceId+']':''}`));
  for(const item of reviewFlags(state)) flagList.append(node('li',`${item.requestId}: ${item.flags.join('; ')}`));
  if(!state.requests.length)requestList.append(node('p','No requests yet.'));
  if(!state.events.length)eventList.append(node('li','No dated events yet.'));
  if(!flagList.children.length)flagList.append(node('li','No missing-documentation flags. This does not establish completeness.'));
}
function add(formId,kind){const form=byId(formId);form.addEventListener('submit',event=>{
  event.preventDefault();try{
    const r=kind==='request'?{
      id:field(form,'id'),jurisdiction:field(form,'jurisdiction'),agency:field(form,'agency'),stage:field(form,'stage'),submittedOn:field(form,'submittedOn'),agencyTrackingId:field(form,'agencyTrackingId'),description:field(form,'description')
    }:{id:field(form,'id'),requestId:field(form,'requestId'),date:field(form,'date'),kind:field(form,'kind'),sourceId:field(form,'sourceId'),description:field(form,'description')};
    const next={...state,[kind==='request'?'requests':'events']:[...state[kind==='request'?'requests':'events'],r]};
    state=validateWorkspace(next);form.reset();render();say(`Added ${kind} ${r.id}.`);
  }catch(error){say(`Cannot add ${kind}: ${error.message}`);}
});}
add('request-form','request');add('event-form','event');
bindExports(()=>state,say);
bindReopen(()=>state, next=>{state=next;render();},say);
render();
