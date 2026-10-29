import {calculateLedger,exportTransactionsCSV,exportBudgetCSV,exportReviewCSV,exportJSON} from './core.mjs';
import {appendExpenseCorrection,exportEvidenceWithCorrections} from './correction-history.mjs';
import {assertSafeLedgerCSV} from './csv-preflight.mjs';
import {buildInterface} from './view.mjs';
import {renderLedger} from './render.mjs';
buildInterface();
let award={awardId:'SYNTHETIC-AWARD-01',awardName:'Sample community project',start:'2026-01-01',end:'2026-12-31'};
let categories=[],expenses=[],corrections=[];
let editingId=null;
const $=id=>document.getElementById(id);
const values=form=>Object.fromEntries(new FormData(form).entries());
const error=text=>{const e=$('error');e.textContent=text;e.hidden=!text;if(text)e.focus();};
function update(a,c,e,message){
 const result=calculateLedger(a,c,e);
 award=a;categories=c;expenses=e;error('');renderLedger(result);$('status').textContent=message;
}
$('awardForm').addEventListener('submit',ev=>{
 ev.preventDefault();try{update(values(ev.currentTarget),categories,expenses,'Award updated.');}catch(e){error(e.message);}
});
$('categoryForm').addEventListener('submit',ev=>{
 ev.preventDefault();try{const f=ev.currentTarget;update(award,[...categories,values(f)],expenses,'Category added.');f.reset();}catch(e){error(e.message);}
});
function endExpenseEdit(form){
 editingId=null;form.elements.transactionId.readOnly=false;
 $('expenseSubmit').textContent='Add expenditure';$('cancelExpenseEdit').hidden=true;
 form.reset();form.elements.percent.value='100';
}
function focusExpenseEdit(id){
 const index=expenses.findIndex(e=>e.transactionId===id);
 if(index>=0)$('expenseRows').querySelector('button[data-edit-index="'+index+'"]')?.focus();
}
$('expenseRows').addEventListener('click',event=>{
 const button=event.target.closest('button[data-edit-index]');
 if(!button||!$('expenseRows').contains(button))return;
 const index=Number(button.dataset.editIndex);
 if(!Number.isSafeInteger(index)||index<0||index>=expenses.length)return;
 const item=expenses[index],form=$('expenseForm');
 editingId=item.transactionId;
 for(const [key,value] of Object.entries(item)){
  const control=form.elements.namedItem(key);if(control)control.value=value;
 }
 form.elements.transactionId.readOnly=true;
 $('expenseSubmit').textContent='Save correction';$('cancelExpenseEdit').hidden=false;
 error('');$('status').textContent='Editing expenditure '+editingId+'. Transaction ID stays unchanged. Cancel to discard edits.';
 form.elements.sourceId.focus();
});
$('cancelExpenseEdit').addEventListener('click',()=>{
 const id=editingId;endExpenseEdit($('expenseForm'));error('');
 $('status').textContent='Correction cancelled; saved evidence unchanged.';
 if(id!==null)focusExpenseEdit(id);
});
$('expenseForm').addEventListener('submit',ev=>{
 ev.preventDefault();
 const form=ev.currentTarget;
 try{
  const item=values(form);
  if(editingId===null){
   update(award,categories,[...expenses,item],'Expenditure recorded.');
   endExpenseEdit(form);
  }else{
   const id=editingId,index=expenses.findIndex(e=>e.transactionId===id);
   if(index<0||item.transactionId!==id)throw new Error('Correction cannot change the transaction ID. Cancel and start again.');
   const proposedHistory=appendExpenseCorrection(corrections,expenses[index],item);
   const corrected=expenses.map((e,i)=>i===index?item:e);
   const changed=proposedHistory!==corrections;
   // Commit the history only after the complete corrected ledger validates successfully.
   update(award,categories,corrected,changed?'Expenditure '+id+' corrected; prior values retained in Evidence JSON.':'No expenditure values changed.');
   corrections=proposedHistory;
   $('correctionSummary').textContent=corrections.length+' expenditure correction'+(corrections.length===1?'':'s')+' recorded in this tab. Evidence JSON includes original and replacement values; award and category edits are not logged.';
   endExpenseEdit(form);focusExpenseEdit(id);
  }
 }catch(e){error(e.message);}
});
function download(filename,mime,text){
 const url=URL.createObjectURL(new Blob([text],{type:mime}));
 const a=document.createElement('a');a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1000);$('status').textContent=filename+' downloaded.';
}
const current=()=>calculateLedger(award,categories,expenses);
function safeCSV(kind, filename, exporter) {
 try {
  const result=current();
  assertSafeLedgerCSV(result,kind);
  error('');
  download(filename,'text/csv;charset=utf-8',exporter(result));
 } catch(e) {
  error(e.message);
  $('status').textContent='CSV unavailable. Evidence JSON retains the original entered values.';
 }
}
$('downloadTransactions').addEventListener('click',()=>safeCSV('transactions','grant-transactions.csv',exportTransactionsCSV));
$('downloadBudget').addEventListener('click',()=>safeCSV('budget','grant-budget.csv',exportBudgetCSV));
$('downloadReview').addEventListener('click',()=>safeCSV('review','grant-review-flags.csv',exportReviewCSV));
$('downloadCurrentJSON').addEventListener('click',()=>{
 try {
  // Deliberately omit the in-tab correction history; current records still contain user-entered data.
  const evidence = exportJSON(current());
  error('');
  download('grant-current-state.json','application/json;charset=utf-8',evidence);
 } catch (e) {
  error(e.message);
  $('status').textContent='Current-state JSON unavailable.';
 }
});
$('downloadJSON').addEventListener('click',()=>{
 try {
  // Validate and serialize before clearing any earlier CSV-specific error.
  const evidence = exportEvidenceWithCorrections(current(),corrections);
  error('');
  download('grant-evidence.json','application/json;charset=utf-8',evidence);
 } catch (e) {
  error(e.message);
  $('status').textContent='Evidence JSON unavailable.';
 }
});
renderLedger(current());
