import assert from 'node:assert/strict';
import {evaluateMatrix,exportMatrixCSV} from './core.mjs';
const input=()=>({criteria:[{id:'C1',label:'Quality',weight:100,sourceRef:'spec:1'}],vendors:[{id:'0007',name:'Vendor',conflict:'none'}],ratings:[{vendorId:'0007',criterionId:'C1',score:5,evidenceRef:'quote:1'}]});
for(const score of [' ','0x2','1e0']){const x=input();x.ratings[0].score=score;assert.throws(()=>evaluateMatrix(x),/Score must be 0–5/);}
const x=input();x.vendors[0].name='＝SUM(A1)';assert.throws(()=>exportMatrixCSV(evaluateMatrix(x)),/CSV export blocked/);
console.log('FT-07 fail-closed score and CSV negative controls: 4/4 PASS');
