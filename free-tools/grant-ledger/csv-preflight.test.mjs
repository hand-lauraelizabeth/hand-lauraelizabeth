import assert from 'node:assert/strict';
import {assertSafeLedgerCSV} from './csv-preflight.mjs';
let passed = 0;
const ok=(actual,expected)=>{assert.deepEqual(actual,expected);passed++};
const blocks=(data,kind,field)=>{assert.throws(()=>assertSafeLedgerCSV(data,kind), e=>e.message.includes(field)&&e.message.includes('Evidence JSON'));passed++};
const base=()=>({award:{awardId:' 0007 '},expenses:[{transactionId:'00009',sourceId:' SRC-09 ',date:'2026-02-03',categoryId:'A',totalCents:120,allocationBps:10000,assignedCents:120,unassignedCents:0,allocationBasis:'',evidenceRef:'Doc, "A"',note:'Narrative - note'}],lines:[{categoryId:'A',label:'Budget, core',budgetCents:100,actualCents:120,differenceCents:-20,restrictionNote:''}],review:[{transactionId:'00009',sourceId:' SRC-09 ',categoryId:'A',flag:'Needs review'}]});
for(const kind of ['transactions','budget','review'])ok(assertSafeLedgerCSV(base(),kind),true);
for(const value of ['=1+1','+SUM(1,2)','-4','@HYPERLINK("x")','＝1','＋2','－3','＠x',' \\t=1','\\u200b=1','\\u202e=1','normal\\u007ftext','text\\u0000','text\\u2060hidden','\\n=1','\\r=1','\\u00ad=1','\\u034f=1']){
  const data=base();data.expenses[0].sourceId=value;blocks(data,'transactions','sourceId');
}
for(const value of ['=SUM(1,2)','\\u200evalue','\\u007f']){const data=base();data.award.awardId=value;blocks(data,'budget','awardId');}
for(const value of ['@cmd','text\\u202dtext']){const data=base();data.review[0].flag=value;blocks(data,'review','flag');}
for(const value of ['ordinary - hyphen','Évidence – text','quoted "field"','2026-01-01','00009',' 00009 ','Narrative - note','a,b;c']){
  const data=base();data.expenses[0].note=value;ok(assertSafeLedgerCSV(data,'transactions'),true);
}
const data=base();ok(data.expenses[0].sourceId,' SRC-09 ');ok(data.award.awardId,' 0007 ');ok(data.lines[0].differenceCents,-20);
assert.throws(()=>assertSafeLedgerCSV(base(),'unknown'));passed++;
assert.throws(()=>assertSafeLedgerCSV({...base(),review:null},'review'));passed++;
assert.throws(()=>assertSafeLedgerCSV({...base(),lines:[null]},'budget'));passed++;
console.log(`PASS: ${passed} synthetic FT-06 CSV preflight assertions`);
