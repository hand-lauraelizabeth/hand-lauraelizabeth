import {inspectDocumentWithFocus} from './focus-extended.mjs';
import {renderFindings} from './render.mjs';
import {bindHTMLFile} from './file-input.mjs';
import {saveLocal} from './download.mjs';
import {exportFindingsCSV} from './report-export.mjs';
const el=id=>document.getElementById(id);
let report=null;
bindHTMLFile(el('html-file'),el('source'),el('status'));
el('analyze').addEventListener('click',()=>{
 try {
  const value=el('source').value;
  if(!value.trim()||value.length>2000000||value.includes('\0')) throw Error('Provide HTML under 2 million characters.');
  report=inspectDocumentWithFocus(new DOMParser().parseFromString(value,'text/html'));
  renderFindings(report,el('findings'),el('summary'));
  el('status').textContent='Preflight completed locally. Review all findings.';
 } catch(error) { report=null; el('status').textContent='Cannot analyze: '+error.message; }
});
el('download-json').addEventListener('click',()=>{
 if(!report) return el('status').textContent='Analyze HTML first.';
 saveLocal('html-preflight.json','application/json',JSON.stringify(report,null,2));
});
el('download-csv').addEventListener('click',()=>{
 if(!report) return el('status').textContent='Analyze HTML first.';
 saveLocal('html-preflight.csv','text/csv;charset=utf-8',exportFindingsCSV(report.findings));
});
