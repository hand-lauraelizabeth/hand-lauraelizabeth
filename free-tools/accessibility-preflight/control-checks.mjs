// Static name checks are review prompts, not computed accessibility names.
// Browser/assistive-technology behavior and CSS visibility still require manual testing.
export function checkControls(doc, add) {
 const labels=[...doc.querySelectorAll('label[for]')];
 const hasName=el=>{
  if(el.getAttribute('aria-label')?.trim())return true;
  const ids=(el.getAttribute('aria-labelledby')||'').split(/\s+/);
  if(ids.some(id=>id&&doc.getElementById(id)?.textContent?.trim()))return true;
  // The functional alt is the accessible label of an image submit control.
  if(el.tagName==='INPUT'&&el.type==='image'&&el.getAttribute('alt')?.trim())return true;
  if(el.tagName==='INPUT'&&el.type==='button'&&el.getAttribute('value')?.trim())return true;
  if(el.getAttribute('title')?.trim())return true;
  if(el.closest('label')?.textContent?.trim())return true;
  return Boolean(el.id&&labels.some(label=>label.htmlFor===el.id&&label.textContent.trim()));
 };
 for(const el of doc.querySelectorAll('input,select,textarea')){
  if(el.tagName==='INPUT'){
   // Submit/reset have native default labels. Image buttons need functional alt;
   // button inputs instead use their value or another accessible name.
   if(['hidden','submit','reset'].includes(el.type))continue;
   if(el.type==='image'){
    if(!el.getAttribute('alt')?.trim())add('image-button-alt','review',el,
     'Image submit button needs nonempty alt text describing its action. Review its accessible name, including any ARIA alternative.','WCAG 1.1.1 / 4.1.2; HTML image button');
    continue;
   }
   if(el.type==='button'){
    if(!hasName(el))add('input-button-name','review',el,
     'Button input has no detected accessible name. Provide a descriptive value or another supported name.','WCAG 4.1.2');
    continue;
   }
  }
  if(!hasName(el))add('form-name','review',el,'No associated label detected.','WCAG 3.3.2 / 4.1.2');
 }
 for(const el of doc.querySelectorAll('a[href],button')){
  const imgAlt=[...el.querySelectorAll('img[alt]')].some(img=>img.getAttribute('alt').trim());
  if(!el.textContent.trim()&&!imgAlt&&!hasName(el))add('control-name','review',el,'Link or button has no detected name.','WCAG 2.4.4 / 4.1.2');
 }
}
