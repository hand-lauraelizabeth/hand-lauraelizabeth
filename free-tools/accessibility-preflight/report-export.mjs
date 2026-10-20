export function exportFindingsCSV(findings) {
 const columns=['id','rule','severity','location','message','reference'];
 const quote=value=>{
  let s=String(value??'');
  if (/^[\s\uFEFF]*[=+@\-\t\r]/u.test(s)) s="'"+s;
  return '"'+s.replaceAll('"','""')+'"';
 };
 return [columns.join(','),...findings.map(row=>columns.map(key=>quote(row[key])).join(','))].join('\r\n')+'\r\n';
}
