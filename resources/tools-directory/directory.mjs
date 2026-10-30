import {TOOLS,STATUS_LABELS} from './catalog.mjs';
// Recheck destinations at the rendering boundary, even if catalog validation
// was skipped by an embedding page or future integration.
// WHATWG URL Standard (2026-10-19): https://url.spec.whatwg.org/
// OWASP URL validation: https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html
export function approvedLiveURL(t){
 if(!t||t.status!=='live'||typeof t.url!=='string')return false;
 try{
  const u=new URL(t.url);
  return u.origin==='https://www.lauraelizabethhand.com'&&!u.username&&!u.password&&!u.search&&!u.hash&&
   u.href===t.url&&/^\/resources\/(?:[a-z0-9-]+\/)+$/.test(u.pathname);
 }catch{return false;}
}
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
   // Keep ZWNJ/ZWJ for languages that require them; reject only the listed catalog obfuscators.
   if(/[\u00ad\u180e\u200b\u2060]/u.test(t[key]))throw Error('Invisible format character in '+key);
  }
  if(!Object.hasOwn(STATUS_LABELS,t.status))throw Error('Invalid availability');
  // Preview and development entries are informational, never navigable.
  // Only an explicitly live resource can receive an approved destination.
  if(t.status==='live'){
   if(typeof t.url!=='string')throw Error('Available tool must have URL');
   if(!approvedLiveURL(t))throw Error('Unapproved tool URL');
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
const unsafeQueryControls=/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\u00ad\u061c\u180e\u200b\u200e\u200f\u2028\u2029\u202a-\u202e\u2060\u2066-\u2069\ufeff]/u;
// Identify the first rejected character without displaying or transmitting the query.
// Positions count Unicode code points (not UTF-16 units); supplementary characters
// before the problem count as one. This is diagnostic guidance, not normalization.
export function firstUnsafeQueryControl(query){
 let position=0;
 for(const character of String(query)){
  position++;
  if(unsafeQueryControls.test(character))return {
   position,
   codePoint:'U+'+character.codePointAt(0).toString(16).toUpperCase().padStart(4,'0')
  };
 }
 return null;
}
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