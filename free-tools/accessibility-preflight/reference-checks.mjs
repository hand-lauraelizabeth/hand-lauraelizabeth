// Static HTML reference checks. Review prompts, not accessibility verdicts.
const FORM_ASSOCIATED='button[form],fieldset[form],input[form],object[form],output[form],select[form],textarea[form]';
export function checkDocumentReferences(doc,add){
 const ids=new Map();
 for(const el of doc.querySelectorAll('[id]')) if(!ids.has(el.id)) ids.set(el.id,el);
 const names=new Set([...doc.querySelectorAll('a[name]')].map(el=>el.getAttribute('name')));
 for(const el of doc.querySelectorAll('a[href^="#"],area[href^="#"]')){
  const href=el.getAttribute('href');
  if(href==='#')continue;
  let target;
  try{target=decodeURIComponent(href.slice(1));}
  catch{add('fragment-encoding','review',el,'Fragment contains malformed percent-encoding; inspect browser navigation.','HTML fragment navigation');continue;}
  if(!target||target.toLowerCase()==='top')continue;
  if(!ids.has(target)&&!names.has(target))add('fragment-target','review',el,'Same-document fragment does not resolve in this static HTML: '+target.slice(0,100),'HTML fragment navigation');
 }
 for(const el of doc.querySelectorAll(FORM_ASSOCIATED)){
  const id=el.getAttribute('form');
  if(!id||ids.get(id)?.tagName!=='FORM')add('form-owner','review',el,'Explicit form association does not identify a form element in this document.','HTML form owner association');
 }
 for(const el of doc.querySelectorAll('input[list]')){
  const id=el.getAttribute('list');
  if(!id||ids.get(id)?.tagName!=='DATALIST')add('datalist-target','review',el,'Input list does not identify a datalist in this document.','HTML list attribute');
 }
}
