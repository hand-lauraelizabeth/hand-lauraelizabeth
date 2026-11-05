import assert from 'node:assert/strict';
import {calculateLedger, parseMoney, parsePercent, exportTransactionsCSV, exportBudgetCSV, exportJSON} from './core.mjs';
const award={awardId:' A ',awardName:'Example',start:'2024-01-01',end:'2024-12-31'};
const categories=[{categoryId:'C',label:'Operations',budget:'100.00'}];
const expense={transactionId:'T',sourceId:' S ',date:'2024-02-29',categoryId:'C',amount:'1.00',percent:'50',allocationBasis:'Time split',evidenceRef:'Doc'};
let count=0;
const eq=(actual,expected)=>{assert.equal(actual,expected);count++};
const reject=(fn)=>{assert.throws(fn);count++};
for(const [text,cents] of [['0',0],['0.01',1],['1.01',101],['999999999.99',99999999999]])eq(parseMoney(text),cents);
for(const text of ['-1','1e3','01','1.001','1000000000','Infinity'])reject(()=>parseMoney(text));
for(const [text,bps] of [['0',0],['33.33',3333],['100',10000],['100.00',10000]])eq(parsePercent(text),bps);
for(const text of ['-1','100.01','101','1.001','01'])reject(()=>parsePercent(text));
const result=calculateLedger(award,categories,[expense]);
eq(result.totalAssignedCents,50);
eq(result.totalUnassignedCents,50);
eq(result.expenses[0].sourceId,' S ');
eq(JSON.parse(exportJSON(result)).award.awardId,' A ');
assert.ok(exportTransactionsCSV(result).includes('" S "'));count++;
assert.ok(exportBudgetCSV(result).includes('" A "'));count++;
reject(()=>calculateLedger(award,categories,[{...expense,date:'2024-02-30'}]));
reject(()=>calculateLedger(award,categories,[expense,expense]));
reject(()=>calculateLedger(award,categories,[{...expense,categoryId:'missing'}]));
for(const [patch,flag] of [[{evidenceRef:''},'Supporting evidence'],[{allocationBasis:''},'Partial allocation'],[{date:'2025-01-01'},'outside award']]){
  assert.ok(calculateLedger(award,categories,[{...expense,...patch}]).review.some(item=>item.flag.includes(flag)));count++;
}
console.log(count+' grant ledger boundary assertions PASS');
