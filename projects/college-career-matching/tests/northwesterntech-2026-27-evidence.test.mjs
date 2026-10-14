import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const load=n=>JSON.parse(readFileSync(new URL('../data/review/'+n+'.json',import.meta.url)));
const a=load('northwesterntech-2026-27-core'),b=load('northwesterntech-2026-27-continuing-education'),c=load('northwesterntech-2026-27-credential-gates');
function validate(x,y,z){assert.equal(x.unitid,'168573');assert.equal(x.program.contact_hours,720);assert.equal(x.program.school_award,'Certificate of Achievement');assert.equal(x.admissions.sat_act_policy,'unknown');assert.equal(x.verified_cip6,null);assert.equal(y.courses.length,9);assert.equal(y.course_count,9);assert.equal(y.non_vocational,true);assert.equal(y.school_award,'Certificate of Completion');assert.equal(z.epa608.automatic,false);assert.equal(z.michigan_mechanical_contractor.automatic,false)}
validate(a,b,c);
for(const [field,value] of [['contact_hours',700],['school_award','Diploma']]){const x=structuredClone(a);x.program[field]=value;assert.throws(()=>validate(x,b,c))}
for(const [field,value] of [['non_vocational',false],['course_count',10]]){const y=structuredClone(b);y[field]=value;assert.throws(()=>validate(a,y,c))}
for(const field of ['epa608','michigan_mechanical_contractor']){const z=structuredClone(c);z[field].automatic=true;assert.throws(()=>validate(a,b,z))}
console.log('PASS 11 positive assertions and 6 negative mutations');
