export function checkContent(doc, add) {
 for(const img of doc.querySelectorAll('img')){
  if(!img.hasAttribute('alt'))add('image-alt-missing','review',img,'Determine an appropriate text alternative or decorative treatment.','WCAG 1.1.1');
  else add('image-alt-quality','manual',img,'Check alt text quality and context.','WCAG 1.1.1');
 }
 for(const table of doc.querySelectorAll('table')){
  if(!table.querySelector('th'))add('table-headers','review',table,'Review whether data tables need header cells.','WCAG 1.3.1');
 }
}
