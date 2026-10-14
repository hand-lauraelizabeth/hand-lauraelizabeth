/* Source-record provenance for replayable local reconciliation. No remote calls. */
(function(root,factory){
 const api=factory(typeof module!=='undefined'&&module.exports?require('./reconcile-core.js'):root.DataReconcile);
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(root)root.DataRescueProvenance=api;
})(typeof window!=='undefined'?window:null,function(engine){
 'use strict';
 function replay(source,manifest){
  if(!source||!Array.isArray(source.rows)||!Array.isArray(source.headers))
   throw new Error('A parsed source table is required.');
  if(!manifest||manifest.schema!=='data-rescue-operations/v1')
   throw new Error('Unknown operations manifest version.');
  const expected=manifest.source;
  if(!expected||expected.rowCount!==source.rows.length||expected.columnCount!==source.headers.length||
   expected.format!==(source.delimiter==='\t'?'TSV':'CSV'))
    throw new Error('Manifest source dimensions or format do not match this dataset.');
  const steps=manifest.steps,rev=manifest.appliedRevisions;
  if(!Array.isArray(steps)||steps.length>30||!Number.isInteger(rev)||rev<0||rev>steps.length)
   throw new Error('Invalid operation sequence.');
  let records=source.rows.map((row,i)=>({cells:row.slice(),sourceRow:i+2}));
  for(let i=0;i<rev;i++){
   const step=steps[i];
   if(!step||step.revision!==i+1||step.status!=='applied'||step.rowsBefore!==records.length)
    throw new Error('Operation sequence does not match the original source.');
   let changed=0;
   if(step.type==='trimWhitespace'){
    if(!Number.isInteger(step.columnIndex)||step.columnIndex<0||step.columnIndex>=source.headers.length)
     throw new Error('Invalid source column index.');
    records=records.map(record=>{
     const cells=record.cells.slice(),old=cells[step.columnIndex];
     cells[step.columnIndex]=old.trim();
     if(old!==cells[step.columnIndex])changed++;
     return {...record,cells};
    });
   }else if(step.type==='removeExactDuplicates'){
    const seen=new Set();
    records=records.filter(record=>{
     const key=JSON.stringify(record.cells);
     if(seen.has(key)){changed++;return false;}
     seen.add(key);return true;
    });
   }else throw new Error('Unsupported operation type.');
   if(changed!==step.changed||records.length!==step.rowsAfter)
    throw new Error('Operation counts do not match source data. Check the original input and operation history.');
  }
  return {...source,rows:records.map(r=>r.cells),sourceRowNumbers:records.map(r=>r.sourceRow)};
 }
 function compare(left,right,leftKey,rightKey){
  function positions(table){
   if(!Array.isArray(table.rows))throw new Error('Invalid input table.');
   const nums=table.sourceRowNumbers;
   if(nums===undefined)return table.rows.map((_,i)=>i+2);
   if(!Array.isArray(nums)||nums.length!==table.rows.length||
      nums.some(x=>!Number.isSafeInteger(x)||x<2)||new Set(nums).size!==nums.length)
      throw new Error('Invalid original source record identifiers.');
   return nums;
  }
  const a=positions(left),b=positions(right);
  const r=engine.reconcile(left,right,leftKey,rightKey);
  const l=x=>a[x-2],z=x=>b[x-2];
  return {
   matches:r.matches.map(x=>({...x,leftRow:l(x.leftRow),rightRow:z(x.rightRow)})),
   ambiguous:r.ambiguous.map(x=>({...x,leftRows:x.leftRows.map(l),rightRows:x.rightRows.map(z)})),
   leftOnly:r.leftOnly.map(x=>({...x,row:l(x.row)})),
   rightOnly:r.rightOnly.map(x=>({...x,row:z(x.row)})),
   missingLeft:r.missingLeft.map(l),
   missingRight:r.missingRight.map(z)
  };
 }
 return {replay,compare};
});
