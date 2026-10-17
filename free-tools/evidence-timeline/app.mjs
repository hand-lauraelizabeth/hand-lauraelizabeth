import {exportEvidenceCSV,summary} from './core.mjs';
import {normalizeExact as normalizeEvidence} from './exact-core.mjs';
import {readExactJSON} from './json-import.mjs';
import {createImportFeedback} from './import-feedback.mjs';
const $ = id => document.getElementById(id);
let records = [];
const form=$('entry-form'), error=$('error'), list=$('records');
const text=(tag,value)=>{const e=document.createElement(tag);e.textContent=String(value);return e;};
function showError(message,field){error.textContent=message;error.hidden=false; if(field){const input=$(field);input.setAttribute('aria-invalid','true');input.setAttribute('aria-describedby','error');}error.focus();}
function clearError(){error.hidden=true;error.textContent='';for(const field of form.elements)if(field.removeAttribute){field.removeAttribute('aria-invalid');field.removeAttribute('aria-describedby');}}
function render(){
  list.replaceChildren();const report=summary(records);$('count').textContent=report.total+' '+(report.total===1?'record':'records')+' (date order).';
  $('groups').textContent=report.reviewGroups.length?report.reviewGroups.map(g=>'Review group '+g.group+': '+g.sourceIds.join(', ')).join(' · '):'No related-record groups to review.';
  $('empty').hidden=records.length>0;
  for(const r of records){const item=text('li','');item.className='record';item.append(text('h3',r.sourceId+' — '+r.date));item.append(text('p',r.claim));const details=text('p','Type: '+r.kind+' · Status: '+r.status+(r.group?' · Group: '+r.group:''));item.append(details);const remove=text('button','Remove '+r.sourceId);remove.type='button';remove.setAttribute('aria-label','Remove record '+r.sourceId);remove.addEventListener('click',()=>{records=records.filter(x=>x.sourceId!==r.sourceId);render();$('count').focus();});item.append(remove);list.append(item);}
  for(const id of ['csv','json','clear'])$(id).disabled=records.length===0;
}
$('count').tabIndex=-1;
form.addEventListener('submit',event=>{
  event.preventDefault();clearError();
  const data=Object.fromEntries(new FormData(form).entries());
  for(const [id,label] of [['sourceId','Source ID'],['date','Record date'],['claim','Record description']]){
    if(!String(data[id]??'').trim()){showError(label+' is required.',id);return;}
  }
  try{records=normalizeEvidence([...records,data]);form.reset();render();$('sourceId').focus();}
  catch(e){const message=String(e.message||e);const field=/source ID/i.test(message)?'sourceId':/date/i.test(message)?'date':/claim/i.test(message)?'claim':null;showError(message,field);}
});
function download(filename,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
$('csv').addEventListener('click',()=>download('evidence-timeline-spreadsheet.csv',exportEvidenceCSV(records),'text/csv;charset=utf-8'));
$('json').addEventListener('click',()=>download('evidence-timeline-exact.json',JSON.stringify({schema:'evidence-timeline-v1',records},null,2)+'\n','application/json'));
$('clear').addEventListener('click',()=>{if(window.confirm('Clear all records from this tab? Export first if you need them.')){records=[];render();$('sourceId').focus();}});

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
 input.disabled=true;
 try{
   const next=await readExactJSON(file);
   if(window.confirm('Replace '+records.length+' current records with '+next.length+' imported records? Export first if needed.')){
     records=next;render();$('count').focus();importFeedback.announce(next.length+' records imported locally.');
   }else importFeedback.announce('Import cancelled; existing records retained.');
 }catch(e){importFeedback.fail(String(e.message||e));}
 finally{input.value='';input.disabled=false;}
});

render();
