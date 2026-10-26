// Spreadsheet programs may interpret imported CSV cells as formulas. Refuse
// ambiguous cells rather than silently altering evidence; JSON remains exact.
// Reject all Unicode format controls (Cf), including invisible bidi and shaping
// characters, in spreadsheet CSV; the JSON export preserves exact evidence.
const UNSAFE_CONTROL = /[\u0000-\u001f\u007f-\u009f\p{Cf}]/u;
// Leading apostrophes can be interpreted as spreadsheet text escapes,
// changing source evidence after opening or saving.
const FORMULA_PREFIX = /^\s*['-=+@\uFF1D\uFF0B\uFF0D\uFF20]/u;

export function exportFindingsCSV(findings) {
 const columns=['id','rule','severity','location','message','reference'];
 const quote=(value,column,rowNumber)=>{
  const s=String(value??'');
  if(UNSAFE_CONTROL.test(s)||FORMULA_PREFIX.test(s)){
   throw Error('CSV export blocked: unsafe spreadsheet cell in '+column+' (finding '+rowNumber+'). Download JSON to preserve exact evidence.');
  }
  return '"'+s.replaceAll('"','""')+'"';
 };
 return [columns.join(','),...findings.map((row,index)=>
  columns.map(key=>quote(row[key],key,index+1)).join(',')
 )].join('\r\n')+'\r\n';
}
