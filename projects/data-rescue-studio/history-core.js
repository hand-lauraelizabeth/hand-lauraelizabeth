/* Reversible, locally held data transformation history. Manifest contains metadata, not row values. */
(function(root,factory){
 const api=factory();
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(root)root.DataRescueHistory=api;
})(typeof window!=='undefined'?window:null,function(){
 'use strict';
 const MAX_STEPS=30;
 function createSession(source){
  if(!source||!Array.isArray(source.rows)||!Array.isArray(source.headers)||!Array.isArray(source.normalizedHeaders))
   throw new Error('Load a validated CSV or TSV first.');
  // Keep the source separate from all transformed row arrays; no file/server writes.
  const original={...source,rows:source.rows.map(row=>row.slice())};
  let steps=[],cursor=0,exports=[];
  function calculate(){
   let current={...original,rows:original.rows.map(row=>row.slice())};
   for(const step of steps.slice(0,cursor)){
    if(step.type==='trimWhitespace'){
     current={...current,rows:current.rows.map(row=>row.map((cell,i)=>i===step.columnIndex?cell.trim():cell))};
    } else if(step.type==='removeExactDuplicates'){
     const seen=new Set();
     current={...current,rows:current.rows.filter(row=>{
      const key=JSON.stringify(row);
      if(seen.has(key))return false;
      seen.add(key);
      return true;
     })};
    } else throw new Error('Unrecognized transformation history operation.');
   }
   return current;
  }
  function current(){return calculate();}
  function apply(spec){
   if(!spec||!['trimWhitespace','removeExactDuplicates'].includes(spec.type))
    throw new Error('Select a supported transformation.');
   if(spec.type==='trimWhitespace'&&(!Number.isInteger(spec.columnIndex)||spec.columnIndex<0||spec.columnIndex>=original.headers.length))
    throw new Error('Choose a valid column to trim.');
   const before=calculate();
   const after=spec.type==='trimWhitespace'
     ? {...before,rows:before.rows.map(row=>row.map((cell,i)=>i===spec.columnIndex?cell.trim():cell))}
     : (function(){const seen=new Set();return {...before,rows:before.rows.filter(row=>{const key=JSON.stringify(row);if(seen.has(key))return false;seen.add(key);return true;})};})();
   const changed=spec.type==='trimWhitespace'
     ? before.rows.reduce((n,row,i)=>n+(row[spec.columnIndex]!==after.rows[i][spec.columnIndex]?1:0),0)
     : before.rows.length-after.rows.length;
   if(!changed)return {applied:false,changed:0,rows:before.rows.length};
   if(cursor>=MAX_STEPS)throw new Error('This review supports at most '+MAX_STEPS+' active transformation steps. Export or reload the original file to begin again.');
   steps=steps.slice(0,cursor);
   steps.push({type:spec.type,...(spec.type==='trimWhitespace'?{columnIndex:spec.columnIndex}:{}),changed,rowsBefore:before.rows.length,rowsAfter:after.rows.length});
   cursor++;
   return {applied:true,changed,rows:after.rows.length};
  }
  function undo(){if(cursor===0)return false;cursor--;return true;}
  function redo(){if(cursor===steps.length)return false;cursor++;return true;}
  function state(){return {cursor,steps:steps.length,canUndo:cursor>0,canRedo:cursor<steps.length};}
  function recordExport(data){
   if(!data||typeof data!=='object'||!Number.isInteger(data.outputRows)||data.outputRows<0)
    throw new Error('Invalid export metadata.');
   exports.push({historyRevision:cursor,outputRows:data.outputRows,exportOnlyDedupe:data.exportOnlyDedupe===true,spreadsheetPrecaution:data.spreadsheetPrecaution===true});
  }
  function manifest(){
   return {
    schema:'data-rescue-operations/v1',
    note:'Operations metadata only. Original file and its content are required to replay; this is not a backup or proof of identity.',
    source:{rowCount:original.rows.length,columnCount:original.headers.length,format:original.delimiter==='\t'?'TSV':'CSV'},
    appliedRevisions:cursor,
    steps:steps.map((step,i)=>({revision:i+1,status:i<cursor?'applied':'undone',...step})),
    exports:exports.map(x=>({...x}))
   };
  }
  return {current,apply,undo,redo,state,recordExport,manifest};
 }
 return {createSession,MAX_STEPS};
});
