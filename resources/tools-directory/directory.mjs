import {TOOLS,STATUS_LABELS} from './catalog.mjs';
export function validateCatalog(rows=TOOLS){
 if(!Array.isArray(rows))throw Error('Catalog must be an array');
 const ids=new Set();
 for(const t of rows){
  if(!t||typeof t!=='object'||typeof t.id!=='string'||!/^[a-z][a-z0-9-]*$/.test(t.id)||ids.has(t.id))throw Error('Invalid or duplicate ID');
  ids.add(t.id);
  for(const key of ['title','category','description'])if(typeof t[key]!=='string'||!t[key].trim())throw Error('Missing '+key);
  if(!Object.hasOwn(STATUS_LABELS,t.status))throw Error('Invalid availability');
  if(t.status==='live'||t.status==='preview'){
   if(typeof t.url!=='string')throw Error('Available tool must have URL');
   const u=new URL(t.url);
   if(u.origin!=='https://www.lauraelizabethhand.com'||!u.pathname.startsWith('/resources/')||u.username||u.password||u.search||u.hash)throw Error('Unapproved tool URL');
  }else if(t.url)throw Error('Unreleased tool cannot have a link');
 }
 return true;
}
// Normalize only the temporary search index; catalog titles and URLs remain unchanged.
// Canonical decomposition supports both precomposed and combining-mark input.
function searchKey(value){
 // Latin accent-insensitive matching must not erase meaningful vowel/voicing marks
 // in Devanagari, Japanese, Arabic or other scripts. Preserve NFD equivalence.
 return String(value).normalize('NFD').replace(/(\p{Script=Latin})\p{M}+/gu,'$1').toLocaleLowerCase('en');
}
export function filterTools(rows=TOOLS,{query='',category='all',status='all'}={}){
 const terms=searchKey(query).trim().split(/\s+/u).filter(Boolean);
 return rows.filter(t=>{
  if(category!=='all'&&t.category!==category)return false;
  if(status!=='all'&&t.status!==status)return false;
  const index=searchKey([t.title,t.category,t.description].join(' '));
  return terms.every(term=>index.includes(term));
 });
}
validateCatalog();