export function checkStructure(doc, add) {
 const root=doc.documentElement;
 if(!root.getAttribute('lang')?.trim())add('page-language','review',root,'Declare and verify the page language.','WCAG 3.1.1');
 if(!doc.querySelector('title')?.textContent?.trim())add('page-title','review',doc.head,'Provide a meaningful page title.','WCAG 2.4.2');
 const headings=[...doc.querySelectorAll('h1,h2,h3,h4,h5,h6')];
 if(!headings.length)add('headings','review',doc.body,'No headings found; review the structure.','WCAG 1.3.1');
 let previous=0;
 for(const h of headings){
  const level=Number(h.tagName.slice(1));
  if(!h.textContent.trim())add('empty-heading','issue',h,'Heading is empty.','WCAG 1.3.1');
  if(previous&&level>previous+1)add('heading-jump','review',h,'Heading levels skip from H'+previous+' to H'+level+'.','WCAG 1.3.1');
  previous=level;
 }
 const seen=new Set();
 for(const el of doc.querySelectorAll('[id]')){
  if(seen.has(el.id))add('duplicate-id','issue',el,'Duplicate ID: '+el.id.slice(0,100),'WCAG 4.1.2 (review relationships)');
  seen.add(el.id);
 }
}
