import {parseCents,formatCents,dateUTC,project,exportCSV} from './engine.mjs';
import {serializeWorkspace,parseWorkspaceBytes,WORKSPACE_MAX_BYTES} from './workspace.mjs';
const $=id=>document.getElementById(id),events=[];let latest=null,workspaceReadGeneration=0;
function say(message,error=false){$('error').textContent=error?message:'';$('status').textContent=error?'Projection unavailable.':message}
function invalidate(){latest=null;$('export').disabled=true;$('results').replaceChildren();$('summary').textContent='';}
function eventList(){const ul=$('events');ul.replaceChildren();const select=$('shift-id');select.replaceChildren();const blank=document.createElement('option');blank.value='';blank.textContent='No shift';select.append(blank);
  if(!events.length){const li=document.createElement('li');li.textContent='No events added.';ul.append(li)}
  for(const e of events){const li=document.createElement('li');li.append(document.createTextNode(`${e.id} — ${e.label} (${formatCents(e.cents)} USD; ${e.date}; ${e.repeat}) `));const button=document.createElement('button');button.type='button';button.textContent=`Remove ${e.id}`;button.addEventListener('click',()=>{workspaceReadGeneration++;events.splice(events.indexOf(e),1);eventList();invalidate();say('Event removed. Recalculate to update results.')});li.append(button);ul.append(li);const option=document.createElement('option');option.value=e.id;option.textContent=`${e.id}: ${e.label}`;select.append(option)}
}
$('event-form').addEventListener('submit',ev=>{ev.preventDefault();workspaceReadGeneration++;try{const e={id:$('event-id').value.trim(),label:$('event-label').value.trim(),date:$('event-date').value,repeat:$('event-repeat').value,cents:parseCents($('event-amount').value)};if(!e.id||!e.label||e.id.length>50||e.label.length>120||events.some(v=>v.id===e.id))throw Error('Provide a unique ID and a description.');dateUTC(e.date);events.push(e);eventList();invalidate();say('Event added. Recalculate to update results.');$('event-form').reset()}catch(error){say(error.message,true)}});
for(const id of ['start','end','opening','shift-id','shift-days'])$(id).addEventListener('input',()=>{workspaceReadGeneration++;invalidate();say('Inputs changed. Recalculate to update results.')});
$('calculate').addEventListener('click',()=>{invalidate();try{const config={start:$('start').value,end:$('end').value,openingCents:parseCents($('opening').value),events};const base=project(config),shiftId=$('shift-id').value||null,shiftDays=Number($('shift-days').value);if(!Number.isInteger(shiftDays))throw Error('Enter a whole number of days.');const scenario=project({...config,shiftId,shiftDays});const frag=document.createDocumentFragment();for(let i=0;i<base.days.length;i++){const tr=document.createElement('tr');for(const text of [base.days[i].date,formatCents(scenario.days[i].changeCents),formatCents(base.days[i].balanceCents),formatCents(scenario.days[i].balanceCents)]){const td=document.createElement('td');td.textContent=text;tr.append(td)}frag.append(tr)}$('results').append(frag);$('summary').textContent=`Baseline minimum ${formatCents(base.minimumCents)} USD on ${base.minimumDate}; scenario minimum ${formatCents(scenario.minimumCents)} USD on ${scenario.minimumDate}. Scenario end ${formatCents(scenario.endingCents)} USD.`;latest=scenario;$('export').disabled=false;say(`Calculated ${base.days.length} days. Results are estimates.`)}catch(error){say(error.message,true)}});
function download(name,type,contents){const url=URL.createObjectURL(new Blob([contents],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
$('export').addEventListener('click',()=>{if(!latest)return;download('cash-flow-scenario.csv','text/csv;charset=utf-8',exportCSV(latest))});
$('save-workspace').addEventListener('click',()=>{try{const settings={start:$('start').value,end:$('end').value,opening:$('opening').value,shiftId:$('shift-id').value||null,shiftDays:Number($('shift-days').value)};const {json}=serializeWorkspace(settings,events);download('cash-flow-workspace.json','application/json;charset=utf-8',json);say('Workspace saved to a local JSON file.')}catch(error){say(error.message,true)}});
$('load-workspace').addEventListener('change',async()=>{
 const input=$('load-workspace'),file=input.files?.[0];if(!file)return;
 const generation=++workspaceReadGeneration;input.value='';
 try{
   if(!/\\.json$/i.test(file.name)||file.size===0||file.size>WORKSPACE_MAX_BYTES)throw Error('Choose a .json workspace file of 1–1,000,000 bytes.');
   const bytes=new Uint8Array(await file.arrayBuffer());
   if(generation!==workspaceReadGeneration)return;
   const restored=parseWorkspaceBytes(bytes);
   if(!window.confirm('Replace the current workspace with the selected local file? This cannot be undone.')){say('Workspace restore canceled.');return}
   if(generation!==workspaceReadGeneration)return;
   events.splice(0,events.length,...restored.events);
   $('start').value=restored.settings.start;$('end').value=restored.settings.end;$('opening').value=restored.settings.opening;
   eventList();$('shift-id').value=restored.settings.shiftId??'';$('shift-days').value=String(restored.settings.shiftDays);
   $('event-form').reset();invalidate();say(`Restored ${events.length} events. Recalculate to update results.`);
 }catch(error){if(generation===workspaceReadGeneration){$('error').textContent=error.message;$('status').textContent='Workspace not restored; current entries and results remain unchanged.'}}
});
eventList();
