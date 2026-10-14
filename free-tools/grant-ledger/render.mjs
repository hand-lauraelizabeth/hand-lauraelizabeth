import {formatMoney} from './core.mjs';
const $=id=>document.getElementById(id);
const row=(parent,values)=>{const tr=document.createElement('tr');values.forEach((v,i)=>{const td=document.createElement(i?'td':'th');td.textContent=v;if(!i)td.scope='row';tr.append(td);});parent.append(tr);};
export function renderLedger(result){
const s=$('expenseCategory'),selected=s.value;s.replaceChildren();
const blank=document.createElement('option');blank.value='';blank.textContent='Choose category';s.append(blank);
result.lines.forEach(c=>{const o=document.createElement('option');o.value=c.categoryId;o.textContent=c.label+' ('+c.categoryId+')';s.append(o);});
if(result.lines.some(c=>c.categoryId===selected))s.value=selected;
$('totals').textContent='Planned '+formatMoney(result.totalBudgetCents)+' | Assigned '+formatMoney(result.totalAssignedCents)+' | Unassigned '+formatMoney(result.totalUnassignedCents);
$('budgetRows').replaceChildren();result.lines.forEach(c=>row($('budgetRows'),[c.label,formatMoney(c.budgetCents),formatMoney(c.actualCents),formatMoney(c.differenceCents)]));
$('expenseRows').replaceChildren();result.expenses.forEach(e=>row($('expenseRows'),[e.transactionId,e.sourceId,e.date,formatMoney(e.assignedCents),formatMoney(e.unassignedCents)]));
$('reviewList').replaceChildren();const flags=result.review.length?result.review:[{flag:'No automatic review flags; this does not establish compliance.'}];
flags.forEach(f=>{const li=document.createElement('li');li.textContent=(f.transactionId?f.transactionId+': ':'')+f.flag;$('reviewList').append(li);});
}
