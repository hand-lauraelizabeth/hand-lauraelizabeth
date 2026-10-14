import {inspectDocument} from './core.mjs';
import {checkHiddenFocus} from './focus-checks.mjs';
import {locationFor} from './location.mjs';
export function inspectDocumentWithFocus(doc) {
 const report=inspectDocument(doc);
 checkHiddenFocus(doc,(rule,severity,element,message,reference)=>{
  report.findings.push({id:'F-'+String(report.findings.length+1).padStart(3,'0'),rule,severity,location:locationFor(element),message,reference});
 });
 return report;
}
