import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';

const file=process.argv[2]||fileURLToPath(new URL('../index.html',import.meta.url));
const html=readFileSync(file,'utf8');
function section(a,b){
 const start=html.indexOf(a),end=html.indexOf(b,start);
 assert(start>=0&&end>start,'required application section exists: '+a);
 return html.slice(start,end);
}
const ctx=vm.createContext({});
vm.runInContext(section('const TYPE_RULES=','function terms(')+
 section('function hardConditions(','const SRCW=')+
 section('function reviewedSupport(','function action('),ctx);
let count=0;
function check(job,want){
 const actual=Array.from(ctx.jobClauses(job),row=>({text:row.text,type:ctx.classify(row.text,row.context)}));
 assert.deepEqual(actual.map(r=>r.type),want,job);
 count++;
 return actual;
}
const pair=check('Bachelor’s degree required; master’s preferred.',['hard','preferred']);
assert.match(pair[0].text,/bachelor/i);assert.match(pair[1].text,/master/i);count+=2;
check('Bachelor’s required, master’s preferred.',['hard','preferred']);
check('Master’s degree required.',['hard']);
check('Master’s preferred or equivalent experience.',['preferred']);
check('A master’s degree.',['context']);
const nested=check('Required Qualifications:\n- Bachelor’s degree\n- 8+ years of experience\nPreferred Qualifications:\n- Master’s degree\n- Experience with SQL',['hard','hard','preferred','preferred']);
assert.equal(nested.length,4);count++;
check('Preferred Qualifications:\n- Master’s degree\nResponsibilities:\n- Lead curriculum design',['preferred','scope']); // reset heading context
const ev={status:'not visible',confidentiality:'public',verification_status:'unreviewed'};
assert.equal(ctx.gap('preferred',ev,'Master’s preferred or equivalent experience.',[]),'Evidence visibility or context gap');count++;
assert.equal(ctx.hardConditionStatus('Bachelor’s degree required.',[],ev),'degree evidence not visible');count++;
assert.match(ctx.gap('hard',ev,'8 years of experience required.',[]),/Hard-condition verification gap/);count++;
console.log('Role Evidence requirement context: '+count+' checks PASS');
