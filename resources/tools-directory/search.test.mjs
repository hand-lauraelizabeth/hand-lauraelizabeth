import assert from 'node:assert/strict';
import {TOOLS} from './catalog.mjs';
import {filterTools,validateCatalog} from './directory.mjs';

// Synthetic-only names exercise composed/decomposed Unicode without modifying public metadata.
const synthetic=[
 {id:'resume',title:'Résumé Planner',category:'Career',description:'Plan research and evidence',status:'development'},
 {id:'cafe-composed',title:'Café Index',category:'Research',description:'Unicode notes',status:'development'},
 {id:'cafe-decomposed',title:'Cafe\u0301 Notes',category:'Research',description:'Evidence references',status:'development'},
 {id:'nonlatin',title:'東京ガイド',category:'Research',description:'日本語 records',status:'development'},
 {id:'plain',title:'Evidence Tracker',category:'Projects',description:'CSV imports',status:'development'}
];
const before=JSON.stringify(synthetic);
let checks=0;
function same(actual,expected,label){assert.deepEqual(actual,expected,label);checks++;}
function ids(query,filters={}){return filterTools(synthetic,{query,...filters}).map(t=>t.id).sort();}
same(ids('resume'),['resume'],'unaccented query finds résumé');
same(ids('re\u0301sume\u0301'),['resume'],'combining-mark query finds precomposed résumé');
same(ids('RÉSUMÉ'),['resume'],'accented uppercase query');
same(ids('cafe'),['cafe-composed','cafe-decomposed'],'both canonical forms searchable');
same(ids('CAFÉ'),['cafe-composed','cafe-decomposed'],'accented search');
same(ids('research evidence'),['cafe-decomposed','resume'],'tokens across title, category, description');
same(ids('EVIDENCE   RESEARCH'),['cafe-decomposed','resume'],'tokens in any order');
same(ids('  research \n evidence  '),['cafe-decomposed','resume'],'multiple whitespace');
same(ids('Research café'),['cafe-composed','cafe-decomposed'],'combined tokens');
same(ids('東京 ガイド'),['nonlatin'],'non-Latin tokens retained');
same(ids('日本語'),['nonlatin'],'Japanese content searchable');
same(ids('CSV'),['plain'],'description indexed');
same(ids('research evidence',{category:'Research'}),['cafe-decomposed'],'category filter AND terms');
same(ids('research evidence',{status:'live'}),[],'availability filter');
same(ids('no-match-987654'),[],'zero result');
same(ids('  '),synthetic.map(t=>t.id).sort(),'blank query returns all');
same(JSON.stringify(synthetic),before,'search never mutates source labels');

// Independent expected-ID table; not computed by the search implementation.
const cases=[
 ['resume',['resume']],
 ['cafe',['cafe-composed','cafe-decomposed']],
 ['research evidence',['cafe-decomposed','resume']],
 ['csv',['plain']],
 ['東京 ガイド',['nonlatin']]
];
let state=0x5f3759df;
function next(){state=(Math.imul(state,1664525)+1013904223)>>>0;return state;}
for(let i=0;i<500;i++){
 const [term,expected]=cases[next()%cases.length];
 const tokens=term.split(' ');
 if((next()&1)&&tokens.length>1)tokens.reverse();
 const spacing=(next()&1)?'  ':' \n ';
 const q=((next()&1)?'  ':'')+tokens.join(spacing).toUpperCase()+((next()&1)?'\t':'');
 same(ids(q),expected,'seeded case '+i+': '+JSON.stringify(q));
}
same(validateCatalog(TOOLS),true,'original public catalog remains valid');
console.log('FT-15 Unicode multi-term search: '+checks+'/'+checks+' PASS');
