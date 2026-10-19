import assert from 'node:assert/strict';
import {evaluateMatrix,exportMatrixJSON,exportMatrixCSV} from './core.mjs';
const data=()=>({criteria:[{id:'C01',label:'Quality',weight:100,sourceRef:'spec:01'}],vendors:[{id:'0007',name:'Vendor',conflict:'none',price:'10.25'}],ratings:[{vendorId:'0007',criterionId:'C01',score:5,evidenceRef:'quote:01'}]});
let n=0;
for(let i=0;i<250;i++){
 const d=data();d.vendors[0].id=String(i).padStart(6,'0');d.ratings[0].vendorId=d.vendors[0].id;d.ratings[0].score=i%6;
 const result=evaluateMatrix(d);
 assert.equal(result.comparisons[0].scorePercent,(i%6)*20);n++;
 assert.equal(JSON.parse(exportMatrixJSON(result)).vendors[0].id,d.vendors[0].id);n++;
 assert.ok(exportMatrixCSV(result).includes('"'+d.vendors[0].id+'"'));n++;
}
console.log('FT-07 deterministic ID/score/export checks:',n,'PASS');
