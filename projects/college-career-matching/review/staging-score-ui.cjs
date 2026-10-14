'use strict';
// Mount only in staging. UI consumes the pinned overlay and review view; no production writes.
const {scoreDisplay}=require('./score-display-guard.cjs');
const {createStagingView}=require('./staging-pinned-score-adapter.cjs');
function stagingScoreModel(overlay,unitid){const view=createStagingView(overlay);return scoreDisplay({unitid:String(unitid),baseline:overlay,view});}
function renderStagingScore(container,overlay,unitid){
 const doc=container.ownerDocument;
 const model=stagingScoreModel(overlay,unitid);
 container.replaceChildren();
 if(!model)return null;
 const section=doc.createElement('section');section.setAttribute('aria-label','Standardized test score evidence');
 for(const line of [model.heading,model.sat,model.act,model.note,model.categoryExplanation].filter(Boolean)){
   const p=doc.createElement('p');p.textContent=line;section.appendChild(p);
 }
 if(model.source&&/^https:\/\//.test(model.source)){
   const a=doc.createElement('a');a.href=model.source;a.textContent='Official score source';a.rel='noopener noreferrer';section.appendChild(a);
 }
 container.appendChild(section);return model;
}
module.exports={stagingScoreModel,renderStagingScore};
