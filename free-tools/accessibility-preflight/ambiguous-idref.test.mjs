import assert from 'node:assert/strict';
import {checkRelationships} from './relationship-checks.mjs';

// Synthetic document model: checks exact, case-sensitive ID references without
// external packages or private HTML. Browser integration is exercised separately.
const table = {};
function element(tag, attrs={}, text='') {
  return {
    tagName:tag, id:attrs.id ?? '', type:attrs.type ?? '',
    textContent:text,
    getAttribute:name=>Object.hasOwn(attrs,name)?attrs[name]:null,
    closest:selector=>selector==='table'?table:null
  };
}
function rules(elements) {
  const select=selector=>{
    if(selector==='[id]')return elements.filter(e=>e.getAttribute('id')!==null);
    if(/^\[[a-z-]+\]$/.test(selector)){
      const attr=selector.slice(1,-1);
      return elements.filter(e=>e.getAttribute(attr)!==null);
    }
    if(selector==='label[for]')return elements.filter(e=>e.tagName==='LABEL'&&e.getAttribute('for')!==null);
    if(selector==='th[headers],td[headers]')return elements.filter(e=>['TH','TD'].includes(e.tagName)&&e.getAttribute('headers')!==null);
    if(selector==='button[aria-label],a[href][aria-label]')return [];
    if(selector==='iframe')return [];
    throw Error('Unexpected selector '+selector);
  };
  const findings=[];
  checkRelationships({querySelectorAll:select},(rule,severity,el,message,reference)=>
    findings.push({rule,severity,el,message,reference}));
  return findings;
}
let count=0;
function expect(elements,expected) {
  assert.deepEqual(rules(elements).map(x=>x.rule),expected);
  count++;
}
const p=(id,text='')=>element('P',{id},text);
expect([p('hint','First'),p('hint','Second'),element('INPUT',{id:'q','aria-describedby':'hint'})],['ambiguous-id-reference']);
expect([p('name','First'),p('name','Second'),element('INPUT',{id:'q','aria-labelledby':'name'})],['ambiguous-id-reference']);
expect([p('hint','First'),p('hint','Second'),element('INPUT',{id:'q','aria-describedby':'hint hint'})],['ambiguous-id-reference','repeated-id-reference']);
expect([p('hint','First'),p('Hint','Second'),element('INPUT',{id:'q','aria-describedby':'hint'})],[]);
expect([p('unrelated'),p('unrelated'),element('INPUT',{id:'q','aria-describedby':'other'})],['unresolved-id-reference']);
expect([p('unrelated'),p('unrelated')],[]);
expect([element('INPUT',{id:'field'}),element('INPUT',{id:'field'}),element('LABEL',{for:'field'},'Name')],['ambiguous-label-target']);
expect([element('INPUT',{id:'field'}),element('LABEL',{for:'field'},'Name')],[]);
expect([element('TH',{id:'h'}),element('TH',{id:'h'}),element('TD',{headers:'h'})],['ambiguous-table-header']);
expect([element('TH',{id:'h'}),element('TD',{headers:'h'})],[]);
expect([p(' 001','A'),p('001','B'),element('INPUT',{id:'q','aria-describedby':'001'})],[]);
expect([p('001','A'),p('001','B'),element('INPUT',{id:'q','aria-describedby':'001'})],['ambiguous-id-reference']);
for(const attr of ['aria-labelledby','aria-describedby','aria-controls','aria-owns','aria-details','aria-errormessage','aria-activedescendant']){
  expect([p('ref','First'),p('ref','Second'),element('BUTTON',{id:'control',[attr]:'ref'})],['ambiguous-id-reference']);
}
// Non-ASCII spacing belongs to the ID token, unlike HTML ASCII whitespace.
expect([p('claim\u00a001'),element('INPUT',{id:'q','aria-describedby':'claim\u00a001'})],[]);
expect([p('claim\u00a001'),p('claim\u00a001'),element('INPUT',{id:'q','aria-describedby':'claim\u00a001'})],['ambiguous-id-reference']);
expect([p('claim\u202f01'),element('INPUT',{id:'q','aria-labelledby':'claim\u202f01'})],[]);
expect([p('claim\u202801'),element('INPUT',{id:'q','aria-controls':'claim\u202801'})],[]);
expect([p('claim\u000b01'),element('INPUT',{id:'q','aria-describedby':'claim\u000b01'})],[]);
expect([p('first'),p('second'),element('INPUT',{id:'q','aria-describedby':'first\tsecond'})],[]);
expect([p('first'),p('second'),element('INPUT',{id:'q','aria-describedby':'first\fsecond'})],[]);
expect([element('TH',{id:'head\u00a001'}),element('TD',{headers:'head\u00a001'})],[]);
expect([element('TH',{id:'head\u00a001'}),element('TH',{id:'head\u00a001'}),element('TD',{headers:'head\u00a001'})],['ambiguous-table-header']);
expect([p('claim\u00a001'),element('BUTTON',{id:'q','aria-activedescendant':'claim\u00a001'})],[]);
// WAI-ARIA 1.2: details and error-message targets are singular; flowto is a list.
expect([p('a'),p('b'),element('INPUT',{id:'q','aria-details':'a b'})],['single-id-reference']);
expect([p('a'),p('b'),element('INPUT',{id:'q','aria-errormessage':'a b','aria-invalid':'true'})],['single-id-reference']);
expect([p('a'),p('b'),element('INPUT',{id:'q','aria-describedby':'a b'})],[]);
expect([p('a'),p('b'),element('INPUT',{id:'q','aria-flowto':'a b'})],[]);
expect([p('a'),element('INPUT',{id:'q','aria-flowto':'a missing'})],['unresolved-id-reference']);
expect([p('a'),p('a'),element('INPUT',{id:'q','aria-flowto':'a'})],['ambiguous-id-reference']);
expect([p('a'),element('INPUT',{id:'q','aria-flowto':'a a'})],['repeated-id-reference']);
expect([p('a\\u00a0b'),element('INPUT',{id:'q','aria-details':'a\\u00a0b'})],[]);
expect([p('a\\u00a0b'),element('INPUT',{id:'q','aria-errormessage':'a\\u00a0b','aria-invalid':'true'})],[]);
expect([p('a\\u00a0b'),element('INPUT',{id:'q','aria-flowto':'a\\u00a0b'})],[]);
const sample=rules([p('safe','One'),p('safe','Two'),element('INPUT',{id:'q','aria-labelledby':'safe'})])[0];
assert.match(sample.message,/multiple elements/);count++;
assert.match(sample.reference,/4\.1\.2/);count++;
console.log('PASS: '+count+' FT-10 ambiguous referenced-ID, case sensitivity, label and table assertions');
