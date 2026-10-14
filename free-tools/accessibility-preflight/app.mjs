import {inspectDocument} from './core.mjs';
import {renderFindings} from './render.mjs';
import {bindHTMLFile} from './file-input.mjs';
import {saveLocal} from './download.mjs';
import {exportFindingsCSV} from './report-export.mjs';
const byId=id=>document.getElementById(id);
const source=byId('source'),status=byId('status');
let report=null;
bindHTMLFile(byId('html-file'),source,status);
byId('analyze').addEventListener('click',()=>{
 try{
  if(!source.value.trim()||source.value.length>2_000_000||source.value.includes('\0'))throw Error('Provide HTML under 2 million characters.');
  const doc=new DOMParser().parseFromString(source.value,'text/html');
  report=inspectDocument(doc);
  renderFindings(report,byId('findings'),byId('summary'));
  status.textContent='Preflight completed locally. Review all findings.';
 }catch(error){report=null;status.textContent='Cannot analyze: '+error.message;}
});
byId('download-json').addEventListener('click',()=>{
 if(!report)return status.textContent='Analyze HTML first.';
 saveLocal('html-preflight.json','application/json',JSON.stringify(report,null,2));
});
byId('download-csv').addEventListener('click',()=>{
 if(!report)return status.textContent='Analyze HTML first.';
 saveLocal('html-preflight.csv','text/csv;charset=utf-8',exportFindingsCSV(report.findings));
});
