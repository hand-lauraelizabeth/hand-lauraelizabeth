import assert from 'node:assert/strict';
import {TOOLS} from './catalog.mjs';
import {filterTools,validateCatalog,queryTooLong,queryIssue,firstUnsafeQueryControl,MAX_QUERY_CODE_POINTS} from './directory.mjs';

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
same(multilingualIds('क'),['dev-plain'],'bare Hindi consonant must not match vowelled grapheme');
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
// Search-input budget is measured in Unicode code points, not UTF-16 units.
// Rejection is non-destructive, including for very large pasted text.
same(MAX_QUERY_CODE_POINTS,256,'documented Unicode query budget');
same(queryTooLong('x'.repeat(256)),false,'256 Latin code points accepted');
same(queryTooLong('x'.repeat(257)),true,'257 Latin code points rejected');
same(queryTooLong('🧪'.repeat(256)),false,'256 supplementary code points accepted');
same(queryTooLong('🧪'.repeat(257)),true,'257 supplementary code points rejected');
same(queryTooLong('क'.repeat(256)),false,'256 Devanagari code points accepted');
same(queryTooLong('क'.repeat(257)),true,'257 Devanagari code points rejected');
same(queryTooLong('x'.repeat(100000)),true,'large pasted text rejected before normalization');
same(filterTools(synthetic,{query:'x'.repeat(100000)}),[],'oversized query yields no partial matches');
const noScan=new Proxy([], {get(target,key,receiver){
 if(key==='filter')throw Error('oversized query must not enumerate catalog');
 return Reflect.get(target,key,receiver);
}});
same(filterTools(noScan,{query:'x'.repeat(257)}),[],'invalid query short-circuits catalog scan');
same(ids('resume'),['resume'],'normal search recovers after oversized query');
console.log('FT-15 Unicode multi-term search: '+checks+'/'+checks+' PASS');

// Unsafe invisible/directional pasted characters must fail closed without
// stripping valid non-Latin shaping characters or normal whitespace.
const unsafe=[0x0000,0x0007,0x007f,0x009f,0x00ad,0x061c,0x180e,0x200b,0x200e,0x200f,0x2028,0x2029,0x202a,0x202b,0x202c,0x202d,0x202e,0x2060,0x2066,0x2067,0x2068,0x2069,0xfeff];
for(const cp of unsafe){
 const q='resume'+String.fromCodePoint(cp);
 same(queryIssue(q),'invisible-control','reject pasted control U+'+cp.toString(16));
 same(ids(q),[],'control cannot yield a partial result U+'+cp.toString(16));
}
// Diagnostic locations are Unicode code-point positions, never UTF-16 offsets.
same(firstUnsafeQueryControl('resume'),null,'ordinary search has no unsafe character');
same(firstUnsafeQueryControl('a\u202eb'),{position:2,codePoint:'U+202E'},'first bidi override located');
same(firstUnsafeQueryControl('🧪\u200btest'),{position:2,codePoint:'U+200B'},'supplementary code point counts once');
same(firstUnsafeQueryControl('a\u200b\u202e'),{position:2,codePoint:'U+200B'},'first of multiple controls reported');
same(firstUnsafeQueryControl('a\u0000'),{position:2,codePoint:'U+0000'},'NUL padded to four hex digits');
same(firstUnsafeQueryControl('می\u200cروم'),null,'legitimate Persian joiner is not flagged');
same(firstUnsafeQueryControl('👩\u200d💻'),null,'legitimate emoji joiner is not flagged');
same(firstUnsafeQueryControl('a'.repeat(256)+'\u202e'),{position:257,codePoint:'U+202E'},'diagnostic position independent of length validation');
same(queryIssue('resume'),null,'ordinary search accepted');
same(queryIssue('x'.repeat(257)),'too-long','length checked first');
same(queryIssue('x'.repeat(257)+'\u202e'),'too-long','oversize checked before hidden controls');
same(queryIssue('  research\\n evidence\\t'),null,'ordinary whitespace accepted');
same(queryIssue('می\u200cروم'),null,'Persian joining control preserved');
same(queryIssue('👩\u200d💻'),null,'emoji joining control preserved');
const legitimate=[{id:'persian',title:'می\u200cروم',category:'Language',description:'Persian',status:'development'},
 {id:'emoji',title:'👩\u200d💻',category:'Language',description:'Emoji',status:'development'}];
same(filterTools(legitimate,{query:'می\u200cروم'}).map(t=>t.id),['persian'],'Persian ZWNJ searchable');
same(filterTools(legitimate,{query:'👩\u200d💻'}).map(t=>t.id),['emoji'],'emoji ZWJ searchable');
const noHiddenScan=new Proxy([],{get(target,key,receiver){if(key==='filter')throw Error('invalid query scanned catalog');return Reflect.get(target,key,receiver)}});
same(filterTools(noHiddenScan,{query:'text\u202e lens'}),[],'invisible controls rejected before scanning');
same(ids('resume'),['resume'],'normal search recovers after invalid control');
// Incomplete UTF-16 sequences must never be normalized into replacement-character
// searches. Valid supplementary characters and language-shaping joiners remain usable.
// WHATWG Infra Strings: https://infra.spec.whatwg.org/#strings
same(queryIssue('a\uD800'),'malformed-unicode','lone high surrogate rejected');
same(queryIssue('\uDFFFb'),'malformed-unicode','lone low surrogate rejected');
same(queryIssue('🧪\uD800'),'malformed-unicode','lone surrogate after valid pair rejected');
same(queryIssue('a\uD800b'),'malformed-unicode','embedded high surrogate rejected');
same(queryIssue('a\uDFFFb'),'malformed-unicode','embedded low surrogate rejected');
same(queryIssue('🧪'),null,'valid surrogate pair accepted');
same(queryIssue('👩\u200d💻'),null,'valid joined emoji remains accepted');
same(queryIssue('x'.repeat(257)+'\uD800'),'too-long','length gate remains first');
same(ids('resume\uD800'),[],'malformed query cannot match a valid prefix');
same(filterTools(noHiddenScan,{query:'resume\uD800'}),[],'malformed query cannot scan catalog');
same(ids('resume'),['resume'],'valid search recovers after malformed input');
console.log('FT-15 invisible-query controls: '+checks+'/'+checks+' PASS');
