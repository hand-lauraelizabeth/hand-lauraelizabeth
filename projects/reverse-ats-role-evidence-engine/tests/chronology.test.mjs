import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';

// Exercise the functions shipped in the standalone application, without a
// second implementation of its date or requirement logic.
const file=process.argv[2]||fileURLToPath(new URL('../index.html',import.meta.url));
const html=readFileSync(file,'utf8');
const start=html.indexOf('function hardConditions(');
const end=html.indexOf('const SRCW=',start);
const reviewStart=html.indexOf('function reviewedSupport(');
const reviewEnd=html.indexOf('let DATA=',reviewStart);
assert(start>=0&&end>start&&reviewStart>=0&&reviewEnd>reviewStart,'application review functions are present');
class ReviewDate extends Date{
 constructor(...args){super(...(args.length?args:['2026-10-30T16:00:00Z']));}
}
const context=vm.createContext({Date:ReviewDate});
vm.runInContext(html.slice(start,end)+'\n'+html.slice(reviewStart,reviewEnd),context);
const node=(dates,id='E001')=>({evidence_id:id,statement:'Led a synthetic learning program.',verification_status:'verified',reviewed:{dates}});
const evidence={status:'strong',verification_status:'verified',confidentiality:'public'};
const cases=[
 ['same calendar year',[node('2026–2026')],'Required: 1 year of experience.',1],
 ['two calendar years can be a short period',[node('2025–2026')],'Required: 2 years of experience.',2],
 ['overlapping roles',[node('2017–2026'),node('2020–2026','E002')],'Required: 8+ years of experience.',10],
 ['gaps between roles',[node('2010–2011'),node('2025–2026','E002')],'Required: 4 years of experience.',4],
 ['present is still imprecise',[node('2026–present')],'Required: 1 year of experience.',1],
 ['month-level text is not an exact-duration calculation',[node('January 2026–March 2026')],'Required: 1 year of experience.',null],
 ['reversed dates',[node('2026–2020')],'Required: 3 years of experience.',null],
 ['missing dates',[node('')],'Required: 3 years of experience.',null],
 ['decimal requirement',[node('2020–2026')],'Required: 5.5 years of experience.',7],
 ['range requirement',[node('2020–2026')],'Required: 5–7 years leading learning programs.',7],
 ['duration without experience keyword',[node('2020–2026')],'Minimum 5 years managing programs.',7],
 ['written number',[node('2020–2026')],'At least five years of experience.',7],
];
let checks=0;
for(const [label,graph,requirement,covered] of cases){
 const conditions=context.hardConditions(requirement);
 assert.equal(conditions.some(c=>c.kind==='years'),true,label+': recognizes duration requirement');checks++;
 assert.equal(context.chronologyYears(graph).years,covered,label+': distinct calendar coverage');checks++;
 const status=context.hardConditionStatus(requirement,graph,evidence);
 assert.match(status,/duration unresolved/i,label+': does not resolve elapsed duration');checks++;
 assert.doesNotMatch(status,/chronology supports|does not yet support/i,label+': avoids qualification verdict');checks++;
 assert.equal(context.gap('hard',evidence,requirement,graph),'Hard-condition verification gap',label+': reviewed wording cannot bypass duration review');checks++;
}
assert.equal(context.chronologyYears([node('2017–2026'),node('2020–2026','E002')]).concurrent,true);checks++;
assert.equal(context.chronologyYears([node('2010–2011'),node('2025–2026','E002')]).concurrent,false);checks++;
assert.match(context.hardConditionStatus('Bachelor degree required',[],evidence),/degree evidence not visible/);checks++;
assert.match(context.hardConditionStatus('Excel proficiency required',[],evidence),/Excel visible/i);checks++;
assert.equal(context.hardConditionStatus('Lead curriculum development.',[],evidence),'');checks++;
console.log(`Role Evidence chronology: ${cases.length} scenarios, ${checks} assertions PASS`);
