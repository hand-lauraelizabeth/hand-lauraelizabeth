import {TOOLS,STATUS_LABELS} from './catalog.mjs';
export function validateCatalog(rows=TOOLS){
 if(!Array.isArray(rows))throw Error('Catalog must be an array');
 const ids=new Set();
 for(const t of rows){
  if(!t||typeof t!=='object'||typeof t.id!=='string'||!/^[a-z][a-z0-9-]*$/.test(t.id)||ids.has(t.id))throw Error('Invalid or duplicate ID');
  ids.add(t.id);
  for(const key of ['title','category','description']){
   if(typeof t[key]!=='string'||!t[key].trim())throw Error('Missing '+key);
   // Catalog labels are controlled metadata, not arbitrary document text: prevent invisible
   // direction controls from visually reordering resource names or availability context.
   // Legitimate RTL/CJK letters and combining marks remain valid.
   if(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/u.test(t[key]))throw Error('Directional control in '+key);
   // Public labels are single-line metadata: reject hidden line breaks, C0/C1 controls,
   // Unicode line/paragraph separators and BOM before rendering or indexing.
   if(/[\u0000-\u001f\u007f-\u009f\u2028\u2029\ufeff]/u.test(t[key]))throw Error('Control character in '+key);
   // Non-printing format characters can conceal different visible labels and search terms.
   // Keep ZWNJ/ZWJ for languages that require them; reject only listed obfuscators.
   // Unicode 17.0 ch23: deprecated U+206A–U+206F; Unicode FAQ: invisible CGJ U+034F.
   // https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-23/
   // https://www.unicode.org/faq/char_combmark.html
   if(/[\u00ad\u034f\u180e\u200b\u2060\u206a-\u206f\u3164\uffa0]/u.test(t[key]))throw Error('Invisible format character in '+key);
  }
  if(!Object.hasOwn(STATUS_LABELS,t.status))throw Error('Invalid availability');
  if(t.status==='live'||t.status==='preview'){
   if(typeof t.url!=='string')throw Error('Available tool must have URL');
   const u=new URL(t.url);
   // URL parsing can silently strip whitespace and normalize path segments. Only
   // canonical, lower-case ASCII resource paths are suitable as public live links.
   // WHATWG URL Standard (2026-10-19): https://url.spec.whatwg.org/
   if(u.origin!=='https://www.lauraelizabethhand.com'||u.username||u.password||u.search||u.hash||
      u.href!==t.url||!/^\/resources\/(?:[a-z0-9-]+\/)+$/.test(u.pathname))throw Error('Unapproved tool URL');
  }else if(t.url)throw Error('Unreleased tool cannot have a link');
 }
 return true;
}
// Search operates on a temporary index; source titles, IDs and URLs are never changed.
// Unicode UAX #15 (2026-08-12): https://www.unicode.org/reports/tr15/
// Unicode UAX #29 (2026-09-01): https://www.unicode.org/reports/tr29/
// Latin accents are folded for search; meaningful marks in other scripts remain.
const segmenter=new Intl.Segmenter('und',{granularity:'grapheme'});
// Bound untrusted pasted search text before Unicode segmentation or catalog scans.
// Count Unicode code points, not UTF-16 units, so supplementary-script text is
// not penalized. The fast code-unit guard prevents oversized allocations.
export const MAX_QUERY_CODE_POINTS=256;
export function queryTooLong(query){
 const value=String(query);
 if(value.length>MAX_QUERY_CODE_POINTS*2)return true;
 let count=0;
 for(const _ of value)if(++count>MAX_QUERY_CODE_POINTS)return true;
 return false;
}
// Reject a narrow set of pasted invisible format and directional controls rather
// than silently normalizing them into misleading search terms. Keep ordinary
// whitespace, Arabic/Persian ZWNJ and emoji/Indic ZWJ valid.
// Unicode UTS #39 rev 34 (2026-08-27): https://www.unicode.org/reports/tr39/
// Also flag invisible CGJ, compatibility Hangul fillers and deprecated U+206A–U+206F.
// Keep meaningful combining marks and Korean Jamo U+115F/U+1160 untouched.
const unsafeQueryControls=/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\u00ad\u034f\u061c\u180e\u200b\u200e\u200f\u2028\u2029\u202a-\u202e\u2060\u2066-\u206f\u3164\ufeff\uffa0]/u;
export function queryIssue(query){
 if(queryTooLong(query))return 'too-long';
 if(unsafeQueryControls.test(String(query)))return 'invisible-control';
 return null;
}
function searchKey(value){
 return String(value).normalize('NFD')
  .replace(/(\p{Script=Latin})\p{M}+/gu,'$1')
  .toLocaleLowerCase('en').normalize('NFC');
}
function graphemes(value){
 return Array.from(segmenter.segment(value),part=>part.segment);
}
// Match at complete extended-grapheme boundaries, not inside a decomposed
// vowel/voicing cluster (e.g. か must not match が; α must not match ά).
function includesGraphemes(index,term){
 if(!term.length)return true;
 for(let i=0;i<=index.length-term.length;i++){
  let matches=true;
  for(let j=0;j<term.length;j++)if(index[i+j]!==term[j]){matches=false;break;}
  if(matches)return true;
 }
 return false;
}
export function filterTools(rows=TOOLS,{query='',category='all',status='all'}={}){
 if(queryIssue(query))return [];
 const terms=searchKey(query).trim().split(/\s+/u).filter(Boolean).map(graphemes);
 return rows.filter(t=>{
  if(category!=='all'&&t.category!==category)return false;
  if(status!=='all'&&t.status!==status)return false;
  const index=graphemes(searchKey([t.title,t.category,t.description].join(' ')));
  return terms.every(term=>includesGraphemes(index,term));
 });
}
validateCatalog();