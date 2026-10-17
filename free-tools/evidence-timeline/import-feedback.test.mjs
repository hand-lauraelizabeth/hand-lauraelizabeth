import assert from 'node:assert/strict';
import {createImportFeedback} from './import-feedback.mjs';

class Element {
  constructor(tag='div') {this.tagName=tag;this.attributes=new Map();this.children=[];this.textContent='';this.hidden=false;this.focused=false;}
  setAttribute(key,value){this.attributes.set(key,String(value));}
  getAttribute(key){return this.attributes.get(key)??null;}
  removeAttribute(key){this.attributes.delete(key);}
  append(...children){this.children.push(...children);}
  focus(){this.focused=true;}
}
globalThis.document={createElement:tag=>new Element(tag)};
const input=new Element('input'), help=new Element('p'), section=new Element('section');
help.id='resume-json-help';
const ui=createImportFeedback(input,help,section);
let checks=0;
const check=(actual,expected)=>{assert.deepEqual(actual,expected);checks++;};
check(section.children.length,2);
check(ui.status.getAttribute('role'),'status');
check(ui.error.getAttribute('role'),'alert');
check(ui.error.hidden,true);
check(input.getAttribute('aria-describedby'),'resume-json-help');
ui.begin();
check(ui.status.textContent,'Reading local JSON file…');
ui.fail('Invalid UTF-8');
check(ui.error.hidden,false);
check(ui.error.textContent,'Import failed: Invalid UTF-8');
check(ui.error.focused,true);
check(input.getAttribute('aria-invalid'),'true');
check(input.getAttribute('aria-describedby'),'resume-json-help resume-json-error');
check(ui.status.textContent,'');
ui.begin();
check(ui.error.hidden,true);
check(ui.error.textContent,'');
check(input.getAttribute('aria-invalid'),null);
check(input.getAttribute('aria-describedby'),'resume-json-help');
ui.announce('Import cancelled; existing records retained.');
check(ui.status.textContent,'Import cancelled; existing records retained.');
ui.fail('Invalid JSON syntax');
ui.announce('2 records imported locally.');
check(ui.error.hidden,true);
check(input.getAttribute('aria-invalid'),null);
check(ui.status.textContent,'2 records imported locally.');
console.log('PASS: '+checks+' import feedback and recovery assertions');
