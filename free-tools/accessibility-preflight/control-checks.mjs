export function checkControls(doc, add) {
 const labels=[...doc.querySelectorAll('label[for]')];
 const hasName=el=>{
  if(el.getAttribute('aria-label')?.trim())return true;
  const ids=(el.getAttribute('aria-labelledby')||'').split(/\s+/);
  if(ids.some(id=>id&&doc.getElementById(id)?.textContent?.trim()))return true;
  if(el.closest('label')?.textContent?.trim())return true;
  return Boolean(el.id&&labels.some(label=>label.htmlFor===el.id&&label.textContent.trim()));
 };
 for(const el of doc.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]),select,textarea')){
  if(!hasName(el))add('form-name','review',el,'No associated label detected.','WCAG 3.3.2 / 4.1.2');
 }
 for(const el of doc.querySelectorAll('a[href],button')){
  const imgAlt=[...el.querySelectorAll('img[alt]')].some(img=>img.getAttribute('alt').trim());
  if(!el.textContent.trim()&&!imgAlt&&!hasName(el))add('control-name','review',el,'Link or button has no detected name.','WCAG 2.4.4 / 4.1.2');
 }
}
