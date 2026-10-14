/* Data Rescue: browser-local transformation controls, using a replayable in-memory history. */
(function(root){
 'use strict';
 const $=id=>document.getElementById(id);
 const el=(tag,text)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=String(text);return x;};
 let session=null,sourceName='',original=null;
 function state(){return session?session.state():{canUndo:false,canRedo:false};}
 function refresh(){
  const s=state(), select=$('trimColumn');
  select.disabled=!session;
  $('trimApply').disabled=!session||select.value==='';
  $('removeDuplicates').disabled=!session;
  $('historyUndo').disabled=!s.canUndo;
  $('historyRedo').disabled=!s.canRedo;
  $('historyExport').disabled=!session;
  const out=$('historyLog');out.replaceChildren();
  if(!session){$('historyStatus').textContent='No transformations yet.';return;}
  const manifest=session.manifest();
  if(!manifest.steps.length){$('historyStatus').textContent='Original working copy; no transformations applied.';return;}
  const table=el('table'),head=el('thead'),headRow=el('tr');
  table.append(el('caption','Transformation history'));
  ['Step','Action','Column','Affected rows','State'].forEach(t=>headRow.append(el('th',t)));
  head.append(headRow);table.append(head);
  const body=el('tbody');
  for(const step of manifest.steps){
   const tr=el('tr');
   const column=step.type==='trimWhitespace'?String(step.columnIndex+1):'—';
   [step.revision,step.type==='trimWhitespace'?'Trim whitespace':'Remove exact duplicates',column,step.changed,step.status].forEach(v=>tr.append(el('td',v)));
   body.append(tr);
  }
  table.append(body);out.append(table);
  $('historyStatus').textContent=manifest.appliedRevisions+' of '+manifest.steps.length+' steps applied.';
 }
 function onLoad(parsed,name){
  session=root.DataRescueHistory.createSession(parsed);
  original=parsed;
  sourceName=name;
  const select=$('trimColumn');select.replaceChildren();
  const placeholder=el('option','Choose a column');placeholder.value='';select.append(placeholder);
  parsed.normalizedHeaders.forEach((text,index)=>{const opt=el('option',text);opt.value=String(index);select.append(opt);});
  select.value='';refresh();
 }
 function onClear(){
  session=null;sourceName='';original=null;
  $('trimColumn').replaceChildren();
  refresh();
 }
 function changed(message){
  const working=root.DataRescueProvenance?root.DataRescueProvenance.replay(original,session.manifest()):session.current();
  root.DataRescueRenderFromHistory(working,sourceName);
  refresh();
  $('historyStatus').textContent=message+' '+session.state().cursor+' active steps.';
 }
 function apply(spec){
  if(!session)return;
  try{
   const result=session.apply(spec);
   changed(result.applied?(spec.type==='trimWhitespace'?'Trimmed '+result.changed+' cells.':'Removed '+result.changed+' duplicate rows.'):'No changes needed.');
  }catch(error){$('historyStatus').textContent=error.message;}
 }
 function recordExport(details){if(session){session.recordExport(details);refresh();}}
 function download(){
  if(!session)return;
  const json=JSON.stringify(session.manifest(),null,2);
  const url=URL.createObjectURL(new Blob([json],{type:'application/json;charset=utf-8'}));
  const link=el('a');link.href=url;link.download='data-rescue-operations.json';
  document.body.append(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
  $('historyStatus').textContent='Operations manifest downloaded. It includes no original row values.';
 }
 $('trimColumn').addEventListener('change',refresh);
 $('trimApply').addEventListener('click',()=>{if($('trimColumn').value!=='')apply({type:'trimWhitespace',columnIndex:Number($('trimColumn').value)});});
 $('removeDuplicates').addEventListener('click',()=>apply({type:'removeExactDuplicates'}));
 $('historyUndo').addEventListener('click',()=>{if(session&&session.undo())changed('Undid last step.');});
 $('historyRedo').addEventListener('click',()=>{if(session&&session.redo())changed('Redid step.');});
 $('historyExport').addEventListener('click',download);
 root.DataRescueHistoryUI={onLoad,onClear,recordExport};
})(window);
