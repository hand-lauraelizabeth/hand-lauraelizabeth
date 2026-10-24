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
   // Keep ZWNJ/ZWJ for languages that require them; reject only the listed catalog obfuscators.
   if(/[\u00ad\u180e\u200b\u2060]/u.test(t[key]))throw Error('Invisible format character in '+key);
  }
  if(!Object.hasOwn(STATUS_LABELS,t.status))throw Error('Invalid availability');
  if(t.status==='live'||t.status==='preview'){
   if(typeof t.url!=='string')throw Error('Available tool must have URL');
   const u=new URL(t.url);
   if(u.origin!=='https://www.lauraelizabethhand.com'||!u.pathname.startsWith('/resources/')||u.username||u.password||u.search||u.hash)throw Error('Unapproved tool URL');
  }else if(t.url)throw Error('Unreleased tool cannot have a link');
 }
 return true;
}
export function filterTools(rows=TOOLS,{query='',category='all',status='all'}={}){
 const q=String(query).trim().toLocaleLowerCase('en');
 return rows.filter(t=>(category==='all'||t.category===category)&&(status==='all'||t.status===status)&&(!q||[t.title,t.category,t.description].some(s=>s.toLocaleLowerCase('en').includes(q))));
}
validateCatalog();