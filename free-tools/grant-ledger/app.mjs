import {calculateLedger,exportTransactionsCSV,exportBudgetCSV,exportReviewCSV,exportJSON} from './core.mjs';
import {assertSafeLedgerCSV} from './csv-preflight.mjs';
import {buildInterface} from './view.mjs';
import {renderLedger} from './render.mjs';
buildInterface();
let award={awardId:'SYNTHETIC-AWARD-01',awardName:'Sample community project',start:'2026-01-01',end:'2026-12-31'};
let categories=[],expenses=[];
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
$('expenseForm').addEventListener('submit',ev=>{
 ev.preventDefault();try{const f=ev.currentTarget;update(award,categories,[...expenses,values(f)],'Expenditure recorded.');f.reset();f.elements.percent.value='100';}catch(e){error(e.message);}
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
$('downloadJSON').addEventListener('click',()=>download('grant-evidence.json','application/json;charset=utf-8',exportJSON(current())));
renderLedger(current());
