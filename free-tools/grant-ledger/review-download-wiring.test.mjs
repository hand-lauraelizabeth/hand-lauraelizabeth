/** Synthetic regression: review download control, local event handler and exact source-linked output. */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {calculateLedger,exportReviewCSV,exportJSON} from './core.mjs';
const app=readFileSync(new URL('./app.mjs',import.meta.url),'utf8');
const view=readFileSync(new URL('./view.mjs',import.meta.url),'utf8');
const html=readFileSync(new URL('./index.html',import.meta.url),'utf8');
assert.match(app,/import \{[^}]*exportReviewCSV[^}]*\} from '\.\/core\.mjs'/);
assert.match(view,/button\(actions,'Review flags CSV','downloadReview'\)/);
assert.match(app,/\$\('downloadReview'\)\.addEventListener\('click',\(\)=>download\('grant-review-flags\.csv','text\/csv;charset=utf-8',exportReviewCSV\(current\(\)\)\)\)/);
assert.match(app,/URL\.createObjectURL\(new Blob\(/);
assert.match(app,/URL\.revokeObjectURL\(url\)/);
assert.doesNotMatch(app,/\bfetch\s*\(|\bXMLHttpRequest\b|\bsendBeacon\b/);
assert.match(html,/connect-src 'none'/);
const result=calculateLedger(
 {awardId:'AW-001',awardName:'Synthetic',start:'2026-01-01',end:'2026-12-31'},
 [{categoryId:'CAT-01',label:'Materials',budget:'1.00',restrictionNote:''}],
 [{transactionId:'TX-0001',sourceId:'=REF-001',date:'2027-01-01',categoryId:'CAT-01',amount:'2.01',percent:'50',allocationBasis:'',evidenceRef:'',note:''}]
);
assert.equal(result.review.length,4);
assert.ok(result.review.every(flag=>flag.categoryId==='CAT-01'));
assert.ok(result.review.some(flag=>flag.sourceId==='=REF-001'));
assert.ok(result.review.some(flag=>flag.transactionId==='' && flag.sourceId===''));
const csv=exportReviewCSV(result);
assert.ok(csv.startsWith('transactionId,sourceId,categoryId,flag\r\n'));
assert.ok(csv.includes("'=REF-001"));
assert.ok(csv.includes('TX-0001'));
assert.ok(csv.endsWith('\r\n'));
assert.equal(JSON.parse(exportJSON(result)).review[0].sourceId,'=REF-001');
console.log('PASS: 16 FT-06 review download wiring, local-only boundary and exact source checks');
