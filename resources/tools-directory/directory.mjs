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
   if(u.protocol!=='https:'||u.hostname!=='www.lauraelizabethhand.com'||u.username||u.password||u.hash)throw Error('Unapproved tool URL');
  }else if(t.url)throw Error('Unreleased tool cannot have a link');
 }
 return true;
}
export function filterTools(rows=TOOLS,{query='',category='all',status='all'}={}){
 const q=String(query).trim().toLocaleLowerCase('en');
 return rows.filter(t=>(category==='all'||t.category===category)&&(status==='all'||t.status===status)&&(!q||[t.title,t.category,t.description].some(s=>s.toLocaleLowerCase('en').includes(q))));
}
validateCatalog();