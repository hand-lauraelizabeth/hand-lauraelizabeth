import {parseCents,formatCents,dateUTC,project,exportSafeCSV,exportJSON,csvExportRisk} from './engine.mjs';
import {exportPlan,readPlanFile} from './plan.mjs';
const $=id=>document.getElementById(id),events=[];let latest=null,revision=0,loadTicket=0;
function markEdited(){revision++;}
function say(message,error=false){$('error').textContent=error?message:'';$('status').textContent=error?'Projection unavailable.':message}
function invalidate(){latest=null;$('export').disabled=true;$('export-json').disabled=true;$('csv-warning').textContent='';$('results').replaceChildren();$('summary').textContent='';}
function eventList(){const ul=$('events');ul.replaceChildren();const select=$('shift-id');select.replaceChildren();const blank=document.createElement('option');blank.value='';blank.textContent='No shift';select.append(blank);
  if(!events.length){const li=document.createElement('li');li.textContent='No events added.';ul.append(li)}
  for(const e of events){const li=document.createElement('li');li.append(document.createTextNode(`${e.id} — ${e.label} (${formatCents(e.cents)} USD; ${e.date}; ${e.repeat}) `));const button=document.createElement('button');button.type='button';button.textContent=`Remove ${e.id}`;button.addEventListener('click',()=>{if(!window.confirm('Remove this event from this tab? Re-enter it if needed; exported files are not changed.'))return;events.splice(events.indexOf(e),1);markEdited();eventList();invalidate();say('Event removed. Recalculate to update results.');$('event-id').focus()});li.append(button);ul.append(li);const option=document.createElement('option');option.value=e.id;option.textContent=`${e.id}: ${e.label}`;select.append(option)}
}
$('event-form').addEventListener('submit',ev=>{ev.preventDefault();try{const e={id:$('event-id').value,label:$('event-label').value,date:$('event-date').value,repeat:$('event-repeat').value,cents:parseCents($('event-amount').value)};if(!e.id.trim()||!e.label.trim()||e.id.length>50||e.label.length>120||events.some(v=>v.id===e.id))throw Error('Provide a unique ID and a description.');dateUTC(e.date);events.push(e);markEdited();eventList();invalidate();say('Event added. Recalculate to update results.');$('event-form').reset()}catch(error){say(error.message,true)}});
for(const id of ['start','end','opening','shift-id','shift-days'])$(id).addEventListener('input',()=>{markEdited();invalidate();say('Inputs changed. Recalculate to update results.')});
$('calculate').addEventListener('click',()=>{invalidate();try{const config={start:$('start').value,end:$('end').value,openingCents:parseCents($('opening').value),events};const base=project(config),shiftId=$('shift-id').value||null,shiftDays=Number($('shift-days').value);if(!Number.isInteger(shiftDays))throw Error('Enter a whole number of days.');const scenario=project({...config,shiftId,shiftDays});const frag=document.createDocumentFragment();for(let i=0;i<base.days.length;i++){const tr=document.createElement('tr');for(const text of [base.days[i].date,formatCents(scenario.days[i].changeCents),formatCents(base.days[i].balanceCents),formatCents(scenario.days[i].balanceCents)]){const td=document.createElement('td');td.textContent=text;tr.append(td)}frag.append(tr)}$('results').append(frag);$('summary').textContent=`Baseline minimum end-of-day ${formatCents(base.minimumCents)} USD on ${base.minimumDate}; scenario minimum end-of-day ${formatCents(scenario.minimumCents)} USD on ${scenario.minimumDate}. Scenario end ${formatCents(scenario.endingCents)} USD.`;latest=scenario;const risk=csvExportRisk(scenario);$('export').disabled=Boolean(risk);$('export-json').disabled=false;$('csv-warning').textContent=risk?`CSV export unavailable: ${risk.field} contains formula-like text, invisible direction controls, or unsupported control characters. Use lossless JSON instead.`:'';say(`Calculated ${base.days.length} days. Results are estimates.`)}catch(error){say(error.message,true)}});
function download(content,type,filename){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
$('export').addEventListener('click',()=>{if(!latest)return;try{download(exportSafeCSV(latest),'text/csv;charset=utf-8','cash-flow-scenario.csv')}catch(error){say(error.message,true)}});
$('export-json').addEventListener('click',()=>{if(!latest)return;try{download(exportJSON(latest),'application/json;charset=utf-8','cash-flow-scenario.json')}catch(error){say(error.message,true)}});
eventList();

// Save only editable inputs, not calculated daily balances. A plan is private
// even though this browser-local tool never transmits it.
$('save-plan').addEventListener('click',()=>{
  try{
    const plan={schema:'cash-flow-plan/v1',start:$('start').value,end:$('end').value,
      openingCents:parseCents($('opening').value),events:events.map(e=>({...e})),
      shiftId:$('shift-id').value||null,shiftDays:Number($('shift-days').value)};
    download(exportPlan(plan),'application/json;charset=utf-8','cash-flow-plan.json');
    say('Editable plan saved locally. Keep the file private.');
  }catch(error){say(error.message,true)}
});
$('load-plan').addEventListener('change',async()=>{
  const input=$('load-plan'),file=input.files?.[0];
  input.value=''; // permit retrying the same file after an error or cancellation
  if(!file)return;
  const ticket=++loadTicket,startedAt=revision;
  try{
    const plan=await readPlanFile(file);
    if(ticket!==loadTicket||startedAt!==revision){say('Plan was not loaded because inputs changed. Choose the file again.',true);return;}
    if(!window.confirm('Replace all events and projection settings in this tab with the selected local plan?')){say('Plan import cancelled. Current inputs and exports were preserved.');return;}
    $('start').value=plan.start;$('end').value=plan.end;
    $('opening').value=formatCents(plan.openingCents);
    events.splice(0,events.length,...plan.events);
    eventList();
    $('shift-id').value=plan.shiftId||'';
    $('shift-days').value=String(plan.shiftDays);
    markEdited();invalidate();
    say('Editable plan loaded locally. Recalculate to update projections.');
    $('event-id').focus();
  }catch(error){
    if(ticket===loadTicket){say(error.message,true);input.focus();}
  }
});
