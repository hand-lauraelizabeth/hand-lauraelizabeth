import {inspectDocument} from './core.mjs';
import {renderFindings} from './render.mjs';
import {bindHTMLFile} from './file-input.mjs';
import {saveLocal} from './download.mjs';
import {exportFindingsCSV} from './report-export.mjs';
const byId=id=>document.getElementById(id);
const source=byId('source'),status=byId('status');
const findings=byId('findings'),summary=byId('summary');
let report=null;
const invalidate=()=>{
 if(report===null)return;
 report=null;
 findings.replaceChildren();
 summary.textContent='Previous findings cleared. Analyze the changed source before exporting.';
 status.textContent='Source changed. Analyze HTML again before exporting.';
};
// Exports must never describe HTML that has since been edited or replaced.
source.addEventListener('input',invalidate);
byId('html-file').addEventListener('change',invalidate);
bindHTMLFile(byId('html-file'),source,status);
byId('analyze').addEventListener('click',()=>{
 report=null;
 findings.replaceChildren();
 summary.textContent='';
 try{
  if(!source.value.trim()||source.value.length>2_000_000||source.value.includes('\0'))throw Error('Provide HTML under 2 million characters.');
  const doc=new DOMParser().parseFromString(source.value,'text/html');
  report=inspectDocument(doc);
  renderFindings(report,findings,summary);
  status.textContent='Preflight completed locally. Review all findings.';
 }catch(error){report=null;findings.replaceChildren();summary.textContent='';status.textContent='Cannot analyze: '+error.message;}
});
byId('download-json').addEventListener('click',()=>{
 if(!report)return status.textContent='Analyze HTML first.';
 saveLocal('html-preflight.json','application/json',JSON.stringify(report,null,2));
});
byId('download-csv').addEventListener('click',()=>{
 if(!report)return status.textContent='Analyze HTML first.';
 try{saveLocal('html-preflight.csv','text/csv;charset=utf-8',exportFindingsCSV(report.findings));}\n catch(error){status.textContent=error.message;status.focus();}
});
