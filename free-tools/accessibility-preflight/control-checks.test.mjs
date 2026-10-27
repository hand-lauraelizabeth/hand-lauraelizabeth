import assert from 'node:assert/strict';
import {checkControls} from './control-checks.mjs';

// Synthetic DOM contract exercises the exact production checker without a
// third-party DOM package. Browser-level behavior is checked separately.
function inspect(type, attributes={}, targets={}) {
 const element={
  tagName:'INPUT',type,id:attributes.id||'',
  getAttribute:key=>Object.hasOwn(attributes,key)?attributes[key]:null,
  closest:()=>null
 };
 const doc={
  querySelectorAll:selector=>selector==='input,select,textarea'?[element]:[],
  getElementById:id=>targets[id]?{textContent:targets[id]}:null
 };
 const findings=[];
 checkControls(doc,(rule,severity,el,message,reference)=>
  findings.push({rule,severity,message,reference,element:el}));
 return findings;
}
let checks=0;
const assertRules=(type,attrs,expected,targets)=>{
 const findings=inspect(type,attrs,targets);
 assert.deepEqual(findings.map(f=>f.rule),expected);
 checks++;
 return findings;
};
assertRules('image',{alt:'Search'},[]);
assertRules('image',{alt:'  Search  '},[]);
assertRules('image',{'aria-label':'Search'},['image-button-alt']);
assertRules('image',{'aria-labelledby':'action' },['image-button-alt'],{action:'Search'});
assertRules('image',{title:'Search'},['image-button-alt']);
assertRules('image',{name:'search'},['image-button-alt']);
assertRules('image',{},['image-button-alt']);
assertRules('image',{alt:''},['image-button-alt']);
assertRules('image',{alt:'   '},['image-button-alt']);
assertRules('button',{},['input-button-name']);
assertRules('button',{value:''},['input-button-name']);
assertRules('button',{value:'Save'},[]);
assertRules('button',{'aria-label':'Save'},[]);
assertRules('button',{'aria-labelledby':'action'},[],{action:'Save'});
assertRules('button',{title:'Save'},[]);
assertRules('reset',{},[]);
assertRules('submit',{},[]);
assertRules('hidden',{},[]);
assertRules('text',{placeholder:'Only a placeholder'},['form-name']);
assertRules('text',{title:'Search field'},[]);
assertRules('text',{'aria-labelledby':'missing'},['form-name']);
assertRules('text',{'aria-labelledby':'action'},[],{action:'Search'});
const warning=assertRules('image',{alt:''},['image-button-alt'])[0];
assert.match(warning.message,/nonempty alt text/);checks++;
assert.match(warning.reference,/1\.1\.1/);checks++;
console.log('PASS: '+checks+' FT-10 image/button naming and false-positive regression assertions');
