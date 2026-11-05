/** Deterministic synthetic allocation properties; independent BigInt arithmetic oracle. */
import assert from 'node:assert/strict';
import { calculateLedger, exportJSON, parseMoney, parsePercent, MAX_MONEY_CENTS } from './core.mjs';
const award = {awardId:'AW-1',awardName:'Synthetic',start:'2026-01-01',end:'2026-12-31'};
const categories = [{categoryId:'C-1',label:'Synthetic category',budget:'999999999.99',restrictionNote:''}];
let seed = 20261017;
const random = () => { seed = (Math.imul(seed,1664525) + 1013904223) >>> 0; return seed; };
const expenses = [];
let expectedAssigned = 0n;
let expectedExpense = 0n;
for(let i=0;i<200;i++) {
  const cents = random() % 100000000;
  const basis = random() % 10001;
  const dollars = `${Math.floor(cents/100)}.${String(cents%100).padStart(2,'0')}`;
  const percent = `${Math.floor(basis/100)}.${String(basis%100).padStart(2,'0')}`;
  assert.equal(parseMoney(dollars),cents);
  assert.equal(parsePercent(percent),basis);
  expenses.push({transactionId:`TX-${i}`,sourceId:` SOURCE ${i} `,date:'2026-06-15',categoryId:'C-1',amount:dollars,percent,allocationBasis:'Time log',evidenceRef:'DOC-1',note:''});
  expectedExpense += BigInt(cents);
  expectedAssigned += (BigInt(cents)*BigInt(basis)+5000n)/10000n;
}
const result = calculateLedger(award,categories,expenses);
assert.equal(BigInt(result.totalAssignedCents),expectedAssigned);
assert.equal(BigInt(result.totalExpenseCents),expectedExpense);
assert.equal(BigInt(result.totalUnassignedCents),expectedExpense-expectedAssigned);
assert.equal(result.lines[0].actualCents,result.totalAssignedCents);
assert.equal(JSON.parse(exportJSON(result)).expenses[199].sourceId,' SOURCE 199 ');
assert.equal(parseMoney('999999999.99'),MAX_MONEY_CENTS);
assert.throws(()=>parseMoney('1000000000.00'));
assert.throws(()=>parsePercent('100.01'));
console.log('PASS: 408 deterministic BigInt oracle, exact ID and amount boundary assertions');
