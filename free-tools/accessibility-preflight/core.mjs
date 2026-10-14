import {checkStructure} from './structure-checks.mjs';
import {checkContent} from './content-checks.mjs';
import {checkControls} from './control-checks.mjs';
import {locationFor} from './location.mjs';
export function inspectDocument(doc) {
 const findings=[];
 const add=(rule,severity,element,message,reference)=>{
  findings.push({id:'F-'+String(findings.length+1).padStart(3,'0'),rule,severity,location:locationFor(element),message,reference});
 };
 checkStructure(doc,add);
 checkContent(doc,add);
 checkControls(doc,add);
 return {format:'html-accessibility-preflight',version:1,findings};
}
