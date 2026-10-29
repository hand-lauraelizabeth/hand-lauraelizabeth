/* Browser-local, value-free reconciliation index. No source names or identifier keys. */
(function(root,factory){
  const api=factory();
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  if(root)root.DataRescueComparisonIndex=api;
})(typeof window!=='undefined'?window:null,function(){
  'use strict';
  const MAX_SOURCE_RECORD=50001;
  function sourceSet(values,label){
    if(!Array.isArray(values)||values.length>50000)throw Error('Invalid '+label+' source-record list.');
    const seen=new Set();
    for(const value of values){
      if(!Number.isSafeInteger(value)||value<2||value>MAX_SOURCE_RECORD||seen.has(value))
        throw Error('Invalid or repeated '+label+' source-record identifier.');
      seen.add(value);
    }
    return seen;
  }
  function create(result,firstSourceRecords,secondSourceRecords){
    if(!result||typeof result!=='object')throw Error('A completed reconciliation is required.');
    const expectedFirst=sourceSet(firstSourceRecords,'first-file');
    const expectedSecond=sourceSet(secondSourceRecords,'second-file');
    const categories=['matches','ambiguous','leftOnly','rightOnly','missingLeft','missingRight'];
    if(categories.some(name=>!Array.isArray(result[name])))
      throw Error('Reconciliation categories are incomplete.');
    const seenFirst=new Set(),seenSecond=new Set();
    const mark=(value,expected,seen,label)=>{
      if(!Number.isSafeInteger(value)||!expected.has(value)||seen.has(value))
        throw Error('Invalid, unknown or repeated '+label+' source-record position.');
      seen.add(value);
      return value;
    };
    const first=value=>mark(value,expectedFirst,seenFirst,'first-file');
    const second=value=>mark(value,expectedSecond,seenSecond,'second-file');
    const findings={
      matches:result.matches.map(item=>({firstSourceRecord:first(item.leftRow),secondSourceRecord:second(item.rightRow)})),
      ambiguous:result.ambiguous.map(item=>{
        if(!Array.isArray(item.leftRows)||!Array.isArray(item.rightRows)||
           item.leftRows.length+item.rightRows.length<2)
          throw Error('Invalid ambiguous source-record group.');
        return {firstSourceRecords:item.leftRows.map(first),secondSourceRecords:item.rightRows.map(second)};
      }),
      firstOnly:result.leftOnly.map(item=>first(item.row)),
      secondOnly:result.rightOnly.map(item=>second(item.row)),
      missingFirstKey:result.missingLeft.map(first),
      missingSecondKey:result.missingRight.map(second)
    };
    if(seenFirst.size!==expectedFirst.size||seenSecond.size!==expectedSecond.size)
      throw Error('Incomplete source-record coverage; no index was exported.');
    return JSON.stringify({
      format:'data-rescue-reconciliation-issue-index',schemaVersion:1,
      recordUnit:'logical CSV/TSV source record; header is record 1',
      privacy:'No source filenames, column labels, identifier keys or cell values. Source positions and linkage patterns may still be sensitive.',
      counts:{firstRecords:seenFirst.size,secondRecords:seenSecond.size,
        matches:findings.matches.length,ambiguousGroups:findings.ambiguous.length,
        firstOnly:findings.firstOnly.length,secondOnly:findings.secondOnly.length,
        missingFirstKey:findings.missingFirstKey.length,missingSecondKey:findings.missingSecondKey.length},
      findings
    });
  }
  return {create};
});