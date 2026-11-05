/** Synthetic provenance regression for reviewer-facing CSV; no personal records. */
import assert from 'node:assert/strict';
import {calculateLedger,exportReviewCSV,exportJSON} from './core.mjs';

function parseCsv(input) {
  const rows=[]; let row=[],cell='',quoted=false,closed=false;
  for(let i=0;i<input.length;i++){
    const c=input[i];
    if(quoted){
      if(c==='"' && input[i+1]==='"'){cell+='"';i++;}
      else if(c==='"'){quoted=false;closed=true;}
      else cell+=c;
    }else if(c==='"' && cell==='' && !closed){quoted=true;}
    else if(c===','){row.push(cell);cell='';closed=false;}
    else if(c==='\r' && input[i+1]==='\n'){row.push(cell);rows.push(row);row=[];cell='';closed=false;i++;}
    else if(c==='\n'){throw new Error('Unquoted newline');}
    else if(closed){throw new Error('Characters after closing quote');}
    else cell+=c;
  }
  if(quoted || cell || row.length)throw new Error('Missing CRLF or unmatched quote');
  return rows;
}
const award={awardId:'AW-01',awardName:'Synthetic',start:'2026-01-01',end:'2026-12-31'};
const categories=[{categoryId:'=BUDGET',label:'Synthetic',budget:'1.00',restrictionNote:''}];
const expenses=[{
 transactionId:'TX-0001',sourceId:'=SOURCE"\r\nID',date:'2027-01-01',categoryId:'=BUDGET',
 amount:'2.01',percent:'50',allocationBasis:'',evidenceRef:'',note:''
}];
const result=calculateLedger(award,categories,expenses);
assert.equal(result.review.length,4);
for(const f of result.review){
 assert.equal(f.categoryId,'=BUDGET');
 assert.equal(f.transactionId==='TX-0001' ? f.sourceId : '',f.sourceId);
}
const csv=exportReviewCSV(result),rows=parseCsv(csv);
assert.deepEqual(rows[0],['transactionId','sourceId','categoryId','flag']);
assert.equal(rows.length,5);
for(const row of rows.slice(1)){
 assert.equal(row.length,4);
 assert.equal(row[2],"'=BUDGET");
 if(row[0]){assert.equal(row[0],'TX-0001');assert.equal(row[1],"'=SOURCE\"\r\nID");}
 else{assert.equal(row[1],'');assert.match(row[3],/Budget comparison/);}
}
const json=JSON.parse(exportJSON(result));
assert.equal(json.review[0].sourceId,'=SOURCE"\r\nID');
assert.equal(json.review[0].categoryId,'=BUDGET');
assert.equal(result.expenses[0].sourceId,'=SOURCE"\r\nID');
assert.equal(exportReviewCSV(calculateLedger(award,categories,[])).split('\r\n').length,2);
console.log('PASS: FT-06 review CSV exact provenance, independent parse, formula guard and JSON regression');
