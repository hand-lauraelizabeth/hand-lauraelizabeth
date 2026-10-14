import {inspectDocumentWithFocus} from './focus-extended.mjs';
import {checkDocumentReferences} from './reference-checks.mjs';
import {locationFor} from './location.mjs';
export function inspectDocumentWithReferences(doc){
 const report=inspectDocumentWithFocus(doc);
 checkDocumentReferences(doc,(rule,severity,element,message,reference)=>{
  report.findings.push({id:'F-'+String(report.findings.length+1).padStart(3,'0'),rule,severity,location:locationFor(element),message,reference});
 });
 return report;
}
