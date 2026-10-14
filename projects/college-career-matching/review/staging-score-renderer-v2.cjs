'use strict';
function renderStagingScore(container, model) {
 container.replaceChildren();
 if (!model) return null;
 const doc=container.ownerDocument;
 const section=doc.createElement('section');
 section.setAttribute('aria-label','Standardized test score evidence');
 for (const value of [model.heading,model.sat,model.act,model.note,model.categoryExplanation]) {
  if (!value) continue;
  const p=doc.createElement('p');
  p.textContent=value;
  section.appendChild(p);
 }
 container.appendChild(section);
 return model;
}
module.exports={renderStagingScore};
