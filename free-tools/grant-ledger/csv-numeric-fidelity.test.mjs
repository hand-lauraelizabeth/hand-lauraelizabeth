import assert from 'node:assert/strict';
import {assertSafeLedgerCSV} from './csv-preflight.mjs';
import {exportBudgetCSV,exportJSON} from './core.mjs';
const data={
 award:{awardId:' 0007 ',awardName:'Sample',start:'2026-01-01',end:'2026-12-31'},
 lines:[{categoryId:'A',label:'Program',budgetCents:100,actualCents:120,differenceCents:-20,restrictionNote:''}],
 expenses:[],review:[],totalBudgetCents:100,totalAssignedCents:120,totalExpenseCents:120,totalUnassignedCents:0
};
assert.equal(assertSafeLedgerCSV(data,'budget'),true);
const csv=exportBudgetCSV(data);
assert.ok(csv.includes('"-20"'),'A generated negative number must remain numeric, not apostrophe-prefixed');
assert.ok(!csv.includes('"\'-20"'),'Negative cents must not be silently changed into text');
assert.ok(csv.includes('" 0007 "'),'Exact source award ID must remain intact');
assert.equal(JSON.parse(exportJSON(data)).lines[0].differenceCents,-20);
assert.equal(JSON.parse(exportJSON(data)).award.awardId,' 0007 ');
console.log('PASS: 5 synthetic FT-06 numeric CSV and JSON fidelity assertions');
