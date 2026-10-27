/* Browser-local reconciliation evidence. Exports decoded identifier findings, not source files or proof of authenticity. */
(function(root,factory){
 const api=factory();
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(root)root.DataRescueReconciliationEvidence=api;
})(typeof window!=='undefined'?window:null,function(){
 'use strict';
 const groups=['matches','ambiguous','leftOnly','rightOnly','missingLeft','missingRight'];
 function checkRow(row){
  if(!Number.isSafeInteger(row)||row<2)throw Error('Invalid logical source-record position.');
  return row;
 }
 function checkRows(rows){
  if(!Array.isArray(rows))throw Error('Invalid source-record positions.');
  return rows.map(checkRow);
 }
 function checkKey(key){
  if(typeof key!=='string')throw Error('Invalid exact identifier.');
  return key;
 }
 function summarizeCoverage(result){
  if(!result||groups.some(name=>!Array.isArray(result[name])))
   throw Error('A completed reconciliation is required.');
  const first={total:0,matched:0,ambiguous:0,firstOnly:0,missingIdentifier:0};
  const second={total:0,matched:0,ambiguous:0,secondOnly:0,missingIdentifier:0};
  const seenFirst=new Set(),seenSecond=new Set();
  function count(rows,seen,side,kind){
   for(const row of checkRows(rows)){
    if(seen.has(row))throw Error('A source record occurs in multiple reconciliation findings.');
    seen.add(row);
    side[kind]++;
    side.total++;
   }
  }
  for(const x of result.matches){
   count([x.leftRow],seenFirst,first,'matched');
   count([x.rightRow],seenSecond,second,'matched');
  }
  for(const x of result.ambiguous){
   count(x.leftRows,seenFirst,first,'ambiguous');
   count(x.rightRows,seenSecond,second,'ambiguous');
  }
  for(const x of result.leftOnly)count([x.row],seenFirst,first,'firstOnly');
  for(const x of result.rightOnly)count([x.row],seenSecond,second,'secondOnly');
  count(result.missingLeft,seenFirst,first,'missingIdentifier');
  count(result.missingRight,seenSecond,second,'missingIdentifier');
  return {first,second};
 }
 function build(result,context){
  if(!result||groups.some(name=>!Array.isArray(result[name])))
   throw Error('A completed reconciliation is required.');
  if(!context||!['firstName','secondName','firstKey','secondKey'].every(name=>typeof context[name]==='string'))
   throw Error('Source names and selected identifier columns are required.');
  if(!context.firstKey||!context.secondKey)throw Error('Identifier columns cannot be empty.');
  const findings=[];
  const add=(classification,identifier,firstRecords,secondRecords)=>{
   findings.push({classification,identifier,firstFileRecords:checkRows(firstRecords),secondFileRecords:checkRows(secondRecords)});
  };
  for(const x of result.matches)add('match',checkKey(x.key),[x.leftRow],[x.rightRow]);
  for(const x of result.ambiguous)add('ambiguous',checkKey(x.key),x.leftRows,x.rightRows);
  for(const x of result.leftOnly)add('first-only',checkKey(x.key),[x.row],[]);
  for(const x of result.rightOnly)add('second-only',checkKey(x.key),[],[x.row]);
  for(const row of result.missingLeft)add('missing-first-key',null,[row],[]);
  for(const row of result.missingRight)add('missing-second-key',null,[],[row]);
  return {
   schema:'data-rescue-reconciliation/v1',
   matching:'exact-case-sensitive',
   recordPositions:'logical-records-header-is-1',
   sources:{first:{fileName:context.firstName,keyColumn:context.firstKey},second:{fileName:context.secondName,keyColumn:context.secondKey}},
   counts:Object.fromEntries(groups.map(name=>[name,result[name].length])),
   recordCounts:summarizeCoverage(result),
   findings,
   limitations:'Local comparison of decoded identifiers only. File names and logical record positions are not cryptographic source authentication. No automatic merges or determinations.'
  };
 }
 function exportJson(result,context){return JSON.stringify(build(result,context));}
 return {build,exportJson,summarizeCoverage};
});
