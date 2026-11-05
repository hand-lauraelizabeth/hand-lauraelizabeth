import assert from 'node:assert/strict';
import {calculateLedger, exportTransactionsCSV, exportBudgetCSV} from './core.mjs';

const award={awardId:'＝Award',awardName:'Synthetic',start:'2026-01-01',end:'2026-12-31'};
const categories=[{categoryId:'C',label:'＋Operations',budget:'100.00',restrictionNote:'－review'}];
const ops=['＝','＋','－','＠','='];
const expenses=ops.map((op,i)=>({
  transactionId:'T'+i,sourceId:'  '+op+'S'+i+'  ',date:'2026-02-01',categoryId:'C',
  amount:'1.00',percent:'50',allocationBasis:'time',evidenceRef:'＠proof',
  note:i===0?'Quoted "text"\nsecond line':'synthetic'
}));
const result=calculateLedger(award,categories,expenses);
const csv=exportTransactionsCSV(result),budget=exportBudgetCSV(result);
let count=0;
for(let i=0;i<ops.length;i++){
  assert.equal(result.expenses[i].sourceId,'  '+ops[i]+'S'+i+'  ');count++;
  assert.ok(csv.includes('"\'  '+ops[i]+'S'+i+'  "'));count++;
}
assert.ok(csv.includes('"\'＠proof"'));count++;
assert.ok(budget.includes('"\'＝Award"'));count++;
assert.ok(budget.includes('"\'＋Operations"'));count++;
assert.ok(budget.includes('"\'－review"'));count++;
assert.ok(csv.includes('"Quoted ""text""\nsecond line"'));count++;
assert.ok(csv.endsWith('\r\n')&&budget.endsWith('\r\n'));count++;
assert.equal(result.totalAssignedCents,250);count++;
console.log(count+' full-width CSV and source-integrity assertions PASS');
