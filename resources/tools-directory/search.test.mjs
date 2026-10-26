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

// Preserve meaning-bearing marks outside Latin; accent-insensitive Latin remains supported.
// Unicode UAX #15 (2026-08-12): https://www.unicode.org/reports/tr15/
const multilingual=[
 {id:'dev-vowel',title:'किताब',category:'Languages',description:'Hindi',status:'development'},
 {id:'dev-plain',title:'कतब',category:'Languages',description:'Hindi',status:'development'},
 {id:'jp-voiced',title:'が',category:'Languages',description:'Japanese',status:'development'},
 {id:'jp-unvoiced',title:'か',category:'Languages',description:'Japanese',status:'development'},
 {id:'ar-vowel',title:'عَلَم',category:'Languages',description:'Arabic',status:'development'},
 {id:'ar-plain',title:'علم',category:'Languages',description:'Arabic',status:'development'},
 {id:'greek-accent',title:'ά',category:'Languages',description:'Greek',status:'development'},
 {id:'greek-plain',title:'α',category:'Languages',description:'Greek',status:'development'},
 {id:'latin-accent',title:'Ångström',category:'Languages',description:'Latin',status:'development'}
];
const multilingualBefore=JSON.stringify(multilingual);
const multilingualIds=q=>filterTools(multilingual,{query:q}).map(t=>t.id).sort();
same(multilingualIds('किताब'),['dev-vowel'],'Devanagari vowel mark must not be discarded');
same(multilingualIds('कि'),['dev-vowel'],'complete Hindi vowel grapheme remains searchable');
same(multilingualIds('क'),[],'bare Hindi consonant must not match vowel grapheme');
same(multilingualIds('कतब'),['dev-plain'],'Devanagari unmarked word remains distinct');
same(multilingualIds('が'),['jp-voiced'],'Japanese dakuten must not be discarded');
same(multilingualIds('か'),['jp-unvoiced'],'unvoiced Japanese must not match voiced grapheme');
same(multilingualIds('か\u3099'),['jp-voiced'],'Japanese canonically decomposed voiced form');
same(multilingualIds('عَلَم'),['ar-vowel'],'Arabic vowel marks must not be discarded');
same(multilingualIds('ع'),['ar-plain'],'unvowelled Arabic grapheme must not match vowelled cluster');
same(multilingualIds('عَ'),['ar-vowel'],'vowelled Arabic grapheme remains independently searchable');
same(multilingualIds('علم'),['ar-plain'],'Arabic unmarked word remains distinct');
same(multilingualIds('ά'),['greek-accent'],'Greek accent remains meaningful');
same(multilingualIds('α\u0301'),['greek-accent'],'canonically decomposed Greek accent matches composed form');
same(multilingualIds('α'),['greek-plain'],'unaccented Greek must not match accented grapheme');
same(multilingualIds('angstrom'),['latin-accent'],'Latin accent-insensitive search retained');
same(multilingualIds('ÅNGSTRÖM'),['latin-accent'],'Latin case and accents supported');
same(JSON.stringify(multilingual),multilingualBefore,'multilingual metadata remains exact');


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
