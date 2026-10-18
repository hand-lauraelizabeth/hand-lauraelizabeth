import {buildHousingLedger,exportHousingJSON} from './housing-core.mjs';
const sources=[]; const events=[];
const $=id=>document.getElementById(id);
const error=$('error'),status=$('status');
const message=(msg)=>{error.hidden=false;error.textContent=msg;error.focus();};
const clearError=()=>{error.hidden=true;error.textContent='';};
const addText=(parent,tag,value)=>{const el=document.createElement(tag);el.textContent=value;parent.append(el);return el;};
function showList(id,items,empty,render){const root=$(id);root.replaceChildren();if(!items.length){addText(root,'li',empty);return;}for(const item of items){const li=document.createElement('li');render(li,item);root.append(li);}}
function render(){const ledger=buildHousingLedger({sources,events});
  showList('sources-list',ledger.sources,'No sources yet.',(li,s)=>addText(li,'span',`${s.sourceId} — ${s.kind}${s.date?' — '+s.date:''}${s.label?' — '+s.label:''}`));
  showList('events-list',ledger.events,'No events yet.',(li,e)=>addText(li,'span',`${e.date} — ${e.eventId} — ${e.category} — ${e.description||'(no description)'} — ${e.amountCents===null?'amount unknown':e.amountCents+' cents'} — sources: ${e.sourceIds.length?e.sourceIds.join(' | '):'none'}`));
  showList('findings-list',ledger.findings,'No review flags.',(li,f)=>addText(li,'span',`${f.eventId}: ${f.kind==='unlinked-evidence'?'No linked source evidence':'Deposit amount not provided'}`));
  status.textContent=`${ledger.sources.length} sources, ${ledger.events.length} events, ${ledger.findings.length} review flags. Data remains in this browser tab.`;
  return ledger;
}
function attempt(fn){try{clearError();fn();render();}catch(e){message(`Could not complete action: ${e instanceof Error?e.message:'Invalid input'}. Existing records were kept.`);}}
$('source-form').addEventListener('submit',e=>{e.preventDefault();const f=e.currentTarget;attempt(()=>{const entry={sourceId:$('source-id').value,kind:$('source-kind').value,label:$('source-label').value,date:$('source-date').value||null};buildHousingLedger({sources:[...sources,entry],events});sources.push(entry);f.reset();});});
$('event-form').addEventListener('submit',e=>{e.preventDefault();const f=e.currentTarget;attempt(()=>{const raw=$('amount').value; if(raw && !/^[0-9]{1,12}$/.test(raw))throw Error('Amount must be whole cents');const amountCents=raw===''?null:Number(raw);const links=$('source-links').value===''?[]:$('source-links').value.split(/\r?\n/u);const entry={eventId:$('event-id').value,date:$('event-date').value,category:$('category').value,description:$('description').value,sourceIds:links,amountCents};buildHousingLedger({sources,events:[...events,entry]});events.push(entry);f.reset();});});
$('download').addEventListener('click',()=>{attempt(()=>{const blob=new Blob([exportHousingJSON(buildHousingLedger({sources,events}))],{type:'application/json;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='housing-evidence-ledger.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);});});
$('clear').addEventListener('click',()=>{if(!sources.length&&!events.length)return;if(!window.confirm('Clear all sources and events from this tab? Export JSON first if you need a copy.'))return; sources.length=0;events.length=0;clearError();render();});
render();
