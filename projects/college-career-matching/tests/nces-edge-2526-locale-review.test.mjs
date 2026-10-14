import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
const dir=path.resolve(import.meta.dirname,'../data/review');
const names=['1a1','1a2','1a3','1b','2','3'].map(s=>'nces-edge-2526-locale-part-'+s+'.json');
const valid=new Set([11,12,13,21,22,23,31,32,33,41,42,43]);
const parts=names.map(n=>JSON.parse(fs.readFileSync(path.join(dir,n),'utf8')));
const rows=parts.flatMap(x=>Object.entries(x.locale_by_unitid));
function verify(pairs){const seen=new Set();for(const [id,v] of pairs){assert.match(id,/^[0-9]{6}$/);assert.ok(!seen.has(id),'duplicate UNITID');seen.add(id);assert.ok(valid.has(v),'invalid NCES locale');}return seen.size;}
test('72 exact UNITID official locale assignments',()=>assert.equal(verify(rows),72));
test('source vintage preserved',()=>parts.forEach(p=>assert.equal(p.source,'NCES EDGE 2025-26')));
test('three territorial nonapplicable schools withheld',()=>['243638','243647','376695'].forEach(id=>assert.ok(!rows.some(r=>r[0]===id))));
test('reject eight-digit extensions',()=>assert.throws(()=>verify([['12345678',11]])));
test('reject invalid codes',()=>assert.throws(()=>verify([['123456',2]])));
test('reject duplicate IDs',()=>assert.throws(()=>verify([['123456',11],['123456',21]])));
