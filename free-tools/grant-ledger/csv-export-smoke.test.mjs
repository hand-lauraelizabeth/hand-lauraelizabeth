import assert from 'node:assert/strict';
import { calculateLedger, exportTransactionsCSV } from './core.mjs';
const result = calculateLedger({awardId:'AW-1',awardName:'Synthetic',start:'2026-01-01',end:'2026-12-31'},[],[]);
assert.match(exportTransactionsCSV(result), /transactionId/);
assert.ok(exportTransactionsCSV(result).endsWith('\r\n'));
console.log('PASS: two CSV export smoke assertions');
