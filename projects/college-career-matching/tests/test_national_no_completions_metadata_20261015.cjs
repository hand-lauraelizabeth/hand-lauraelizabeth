const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const r=p=>JSON.parse(fs.readFileSync(path.join(__dirname,'..',p),'utf8'));
const d=r('review/national-six-digit-no-completions-20261015.json');
test('129 distinct six-digit records',()=>{assert.equal(d.institutions.length,129);assert.equal(new Set(d.institutions.map(x=>x.unitid)).size,129)});
test('metadata classifications',()=>{assert.equal(d.institutions.filter(x=>x.control_code===3).length,106);assert.equal(d.institutions.filter(x=>x.predominant_degree_code===1).length,121)});
test('unresolved means unresolved',()=>{assert.ok(d.institutions.every(x=>x.cause_of_absence==='NOT_DETERMINED'&&x.current_program_offering==='NOT_DETERMINED'))});
