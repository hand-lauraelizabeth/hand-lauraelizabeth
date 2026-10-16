import assert from 'node:assert/strict';
import {calculateLedger, exportTransactionsCSV, exportJSON, MAX_CATEGORIES, MAX_EXPENSES} from './core.mjs';

const award={awardId:'A-1',awardName:'Synthetic award',start:'2026-01-01',end:'2026-12-31'};
const categories=Array.from({length:MAX_CATEGORIES},(_,i)=>({
  categoryId:'C'+i,label:'Category '+i,budget:'999999999.99'
}));
const expenses=Array.from({length:MAX_EXPENSES},(_,i)=>({
  transactionId:'T'+i,sourceId:'  SRC-'+i+'  ',date:'2026-06-01',
  categoryId:'C'+(i%MAX_CATEGORIES),amount:'999999999.99',
  percent:'100',allocationBasis:'',evidenceRef:'synthetic-proof'
}));
const original=JSON.stringify({award,categories,expenses});
const result=calculateLedger(award,categories,expenses);
assert.equal(result.lines.length,MAX_CATEGORIES);
assert.equal(result.expenses.length,MAX_EXPENSES);
assert.equal(result.totalExpenseCents,MAX_EXPENSES*99999999999);
assert.equal(result.totalAssignedCents,result.totalExpenseCents);
assert.equal(result.totalUnassignedCents,0);
assert.equal(result.totalBudgetCents,MAX_CATEGORIES*99999999999);
assert.equal(result.lines[0].actualCents,10*99999999999);
assert.equal(result.lines[0].differenceCents,-9*99999999999);
assert.equal(result.review.length,MAX_CATEGORIES);
assert.equal(result.expenses[0].sourceId,'  SRC-0  ');
assert.equal(result.expenses.at(-1).sourceId,'  SRC-499  ');
assert.equal(JSON.stringify({award,categories,expenses}),original);
const csv=exportTransactionsCSV(result);
assert.equal(csv.split('\r\n').length,MAX_EXPENSES+2);
assert.ok(csv.includes('"  SRC-499  "'));
const json=JSON.parse(exportJSON(result));
assert.equal(json.schema,'grant-ledger-review-v1');
assert.equal(json.expenses.length,MAX_EXPENSES);
assert.throws(()=>calculateLedger(award,categories,[...expenses,expenses[0]]),/Too many expenses/);
assert.throws(()=>calculateLedger(award,[...categories,categories[0]],expenses),/Too many budget categories/);
console.log('18 synthetic maximum-boundary assertions passed');
