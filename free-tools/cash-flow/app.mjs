import {parseCents,formatCents,dateUTC,project,exportSafeCSV,exportJSON,csvExportRisk} from './engine.mjs';
import {exportPlan,readPlanFile} from './plan.mjs';
import {summarizeShortfalls,compareBelowZeroDates} from './shortfalls.mjs';
import {coverageText,coverageEvidence,displaySafeText} from './coverage.mjs';
const $=id=>document.getElementById(id),events=[];let latest=null,revision=0,loadTicket=0;
function markEdited(){revision++;}
function say(message,error=false){$('error').textContent=error?message:'';$('status').textContent=error?'Projection unavailable.':message}
function invalidate(){latest=null;$('export').disabled=true;$('export-json').disabled=true;$('csv-warning').textContent='';$('results').replaceChildren();$('summary').textContent='';$('shortfall-summary').textContent='';$('coverage-summary').textContent='';}
function eventList(){const ul=$('events');ul.replaceChildren();const select=$('shift-id');const previousShift=select.value;select.replaceChildren();const blank=document.createElement('option');blank.value='';blank.textContent='No shift';select.append(blank);
  if(!events.length){const li=document.createElement('li');li.textContent='No events added.';ul.append(li)}
  for(const e of events){const li=document.createElement('li');li.append(document.createTextNode(`${displaySafeText(e.id)} — ${displaySafeText(e.label,'description')} (${formatCents(e.cents)} USD; ${e.date}; ${e.repeat}) `));const button=document.createElement('button');button.type='button';button.textContent=`Remove ${displaySafeText(e.id)}`;button.addEventListener('click',()=>{if(!window.confirm('Remove this event from this tab? Re-enter it if needed; exported files are not changed.'))return;events.splice(events.indexOf(e),1);markEdited();const shiftCleared=eventList();invalidate();say(shiftCleared?'Event removed. Its timing shift was cleared. Recalculate to update results.':'Event removed. Recalculate to update results.');$('event-id').focus()});li.append(button);ul.append(li);const option=document.createElement('option');option.value=e.id;option.textContent=`${displaySafeText(e.id)}: ${displaySafeText(e.label,'description')}`;select.append(option)}
  if(events.some(e=>e.id===previousShift)){select.value=previousShift;return false;}
  if(previousShift){$('shift-days').value='0';return true;}
  return false;
}
const eventFields=['event-id','event-label','event-amount','event-date','event-repeat'];
function clearEventError(){
  $('event-error').textContent='';
  for(const id of eventFields){$(id).removeAttribute('aria-invalid');$(id).removeAttribute('aria-describedby');}
}
function reportEventError(message,fieldId){
  clearEventError();
  const field=$(fieldId);
  field.setAttribute('aria-invalid','true');
  field.setAttribute('aria-describedby','event-error');
  const alert=$('event-error');
  alert.textContent=message;
  alert.focus();
  say('Event not added. Correct the highlighted field next to the event form.');
}
for(const id of eventFields)$(id).addEventListener('input',clearEventError);
$('event-form').addEventListener('submit',ev=>{
  ev.preventDefault();
  let fieldId='event-amount';
  try{
    const cents=parseCents($('event-amount').value);
    fieldId='event-id';
    const id=$('event-id').value,label=$('event-label').value;
    if(!id.trim()||id.length>50||events.some(v=>v.id===id))throw Error('Provide a unique ID that has not already been used.');
    fieldId='event-label';
    if(!label.trim()||label.length>120)throw Error('Provide an event description.');
    fieldId='event-date';
    const date=$('event-date').value;
    dateUTC(date);
    const e={id,label,date,repeat:$('event-repeat').value,cents};
    events.push(e);
    clearEventError();
    markEdited();eventList();invalidate();
    say('Event added. Recalculate to update results.');
    $('event-form').reset();
  }catch(error){reportEventError(error.message,fieldId)}
});
function clearShiftError(){for(const id of ['shift-id','shift-days']){$(id).removeAttribute('aria-invalid');$(id).removeAttribute('aria-describedby');}}
for(const id of ['start','end','opening','shift-id','shift-days'])$(id).addEventListener('input',()=>{if(id==='shift-id'||id==='shift-days')clearShiftError();markEdited();invalidate();say('Inputs changed. Recalculate to update results.')});
$('calculate').addEventListener('click',()=>{invalidate();try{const config={start:$('start').value,end:$('end').value,openingCents:parseCents($('opening').value),events};const base=project(config),shiftId=$('shift-id').value||null,shiftDays=Number($('shift-days').value);if(!Number.isInteger(shiftDays))throw Error('Enter a whole number of days.');const scenario=project({...config,shiftId,shiftDays});const frag=document.createDocumentFragment();for(let i=0;i<base.days.length;i++){const tr=document.createElement('tr');for(const text of [base.days[i].date,formatCents(scenario.days[i].changeCents),formatCents(base.days[i].balanceCents),formatCents(scenario.days[i].balanceCents)]){const td=document.createElement('td');td.textContent=text;tr.append(td)}frag.append(tr)}$('results').append(frag);$('summary').textContent=`Baseline minimum end-of-day ${formatCents(base.minimumCents)} USD on ${base.minimumDate}; scenario minimum end-of-day ${formatCents(scenario.minimumCents)} USD on ${scenario.minimumDate}. Scenario end ${formatCents(scenario.endingCents)} USD.`;$('shortfall-summary').textContent=shortfallText('Baseline',base)+' '+shortfallText('Scenario',scenario)+' '+shortfallComparisonText(base,scenario)+' These estimates do not model intraday funds or overdraft rules.';$('coverage-summary').textContent=coverageText(events,base,scenario);latest={...scenario,sourceEventCoverage:coverageEvidence(events,base,scenario)};const risk=csvExportRisk(scenario);$('export').disabled=Boolean(risk);$('export-json').disabled=false;$('csv-warning').textContent=risk?`CSV export unavailable: ${risk.field} contains formula-like text, invisible direction controls, or unsupported control characters. Use lossless JSON instead.`:'';say(`Calculated ${base.days.length} days. Results are estimates.`)}catch(error){if(error.message==='Choose an event to shift, or set shift days to 0.'){const field=$('shift-id');field.setAttribute('aria-invalid','true');field.setAttribute('aria-describedby','error');field.focus();}say(error.message,true)}});
function shortfallText(label,projection){
  const s=summarizeShortfalls(projection);
  if(s.daysBelowZero===0)return label+': no projected below-zero end-of-day dates.';
  return label+': '+s.daysBelowZero+' projected below-zero end-of-day '+(s.daysBelowZero===1?'date':'dates')+' (first '+s.firstBelowZeroDate+'; lowest '+formatCents(s.lowestBalanceCents)+' USD; longest consecutive span '+s.longestRunDays+' '+(s.longestRunDays===1?'day':'days')+').';
}
function shortfallComparisonText(baseline,scenario){
  const changes=compareBelowZeroDates(baseline,scenario);
  const plural=n=>n===1?'date':'dates';
  const noLonger=changes.noLongerBelowZero+' '+plural(changes.noLongerBelowZero)+' no longer below zero'+
    (changes.firstNoLongerBelowZeroDate?' (first '+changes.firstNoLongerBelowZeroDate+')':'');
  const newly=changes.newlyBelowZero+' '+plural(changes.newlyBelowZero)+' newly below zero'+
    (changes.firstNewlyBelowZeroDate?' (first '+changes.firstNewlyBelowZeroDate+')':'');
  return 'Compared with baseline: '+noLonger+'; '+newly+'.';
}
// Initiating a browser download does not prove that the user saved the file.
function clearDownloadError(){$('download-error').textContent='';}
function reportDownloadError(){
  const alert=$('download-error');
  alert.textContent='Download could not start. Check browser download permissions and try again. Your inputs and results are unchanged.';
  alert.focus();
  $('status').textContent='Download did not start. Your inputs and results remain available.';
}
function download(content,type,filename){
  let url=null,link=null,started=false;
  try{
    url=URL.createObjectURL(new Blob([content],{type}));
    link=document.createElement('a');
    link.href=url;link.download=filename;
    document.body.append(link);
    link.click();
    started=true;
  }catch{
    throw Error('Download could not start.');
  }finally{
    if(link)link.remove();
    if(url){
      if(started)setTimeout(()=>URL.revokeObjectURL(url),1000);
      else URL.revokeObjectURL(url);
    }
  }
}
$('export').addEventListener('click',()=>{
  if(!latest)return;
  clearDownloadError();
  try{download(exportSafeCSV(latest),'text/csv;charset=utf-8','cash-flow-scenario.csv');say('Scenario CSV download started. Confirm the browser saved it.');}
  catch{reportDownloadError();}
});
$('export-json').addEventListener('click',()=>{
  if(!latest)return;
  clearDownloadError();
  try{download(exportJSON(latest),'application/json;charset=utf-8','cash-flow-scenario.json');say('Scenario JSON download started. Confirm the browser saved it.');}
  catch{reportDownloadError();}
});
eventList();

// Save only editable inputs, not calculated daily balances. A plan is private
// even though this browser-local tool never transmits it.
$('save-plan').addEventListener('click',()=>{
  try{
    const plan={schema:'cash-flow-plan/v1',start:$('start').value,end:$('end').value,
      openingCents:parseCents($('opening').value),events:events.map(e=>({...e})),
      shiftId:$('shift-id').value||null,shiftDays:Number($('shift-days').value)};
    const contents=exportPlan(plan);
    clearDownloadError();
    download(contents,'application/json;charset=utf-8','cash-flow-plan.json');
    say('Editable plan download started. Confirm it was saved and keep the file private.');
  }catch(error){
    if(error.message==='Download could not start.')reportDownloadError();
    else say(error.message,true);
  }
});
function clearPlanError(){ $('plan-error').textContent=''; $('load-plan').removeAttribute('aria-invalid'); }
function reportPlanError(message){
  const alert=$('plan-error');
  alert.textContent=message;
  $('load-plan').setAttribute('aria-invalid','true');
  alert.focus();
  say('Plan not loaded. Correct the file selection; your existing plan and calculated exports were preserved.');
}
$('load-plan').addEventListener('change',async()=>{
  const input=$('load-plan'),file=input.files?.[0];
  input.value=''; // permit retrying the same file after an error or cancellation
  if(!file)return;
  clearPlanError();
  const ticket=++loadTicket,startedAt=revision;
  try{
    const plan=await readPlanFile(file);
    // A superseded file read is obsolete, not a new user-facing error. Never
    // overwrite a newer import's status or confirmation with stale feedback.
    if(ticket!==loadTicket)return;
    if(startedAt!==revision){reportPlanError('Plan was not loaded because inputs changed. Choose the file again.');return;}
    if(!window.confirm('Replace all events and projection settings in this tab with the selected local plan?')){clearPlanError();say('Plan import cancelled. Current inputs and exports were preserved.');return;}
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
    if(ticket===loadTicket){reportPlanError(error.message);}
  }
});
