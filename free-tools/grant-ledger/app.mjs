import {calculateLedger,exportTransactionsCSV,exportBudgetCSV,exportReviewCSV,exportJSON} from './core.mjs';
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
$('downloadTransactions').addEventListener('click',()=>download('grant-transactions.csv','text/csv;charset=utf-8',exportTransactionsCSV(current())));
$('downloadBudget').addEventListener('click',()=>download('grant-budget.csv','text/csv;charset=utf-8',exportBudgetCSV(current())));
$('downloadReview').addEventListener('click',()=>download('grant-review-flags.csv','text/csv;charset=utf-8',exportReviewCSV(current())));
$('downloadJSON').addEventListener('click',()=>download('grant-evidence.json','application/json;charset=utf-8',exportJSON(current())));
renderLedger(current());
