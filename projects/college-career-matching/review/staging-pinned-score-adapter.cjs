'use strict';
// Review-only: load alongside the immutable Scorecard overlay; never overwrite its entries.
const candidates=Object.freeze({
 '105330':{name:'Northern Arizona University',cohort:'Fall 2025',source:'https://in.nau.edu/wp-content/uploads/sites/129/2026/04/CDS-2025-2026.pdf',sat:{p25:1010,p50:1175,p75:1280,percent:3},act:{p25:19,p50:23,p75:26,percent:27},admission_policy:'optional_considered_if_submitted'},
 '197294':{name:'SUNY Westchester Community College',cohort:'Fall 2025',source:'https://www.sunywcc.edu/wp-content/uploads/2026/04/2025-2026-Common-Data-Set.pdf',sat:{p25:940,p50:1170,p75:1250,percent:2},act:{p25:23,p50:27,p75:null,percent:0},admission_policy:'scores_not_used_in_admissions'}
});
function createStagingView(overlay){
 if(overlay.school_count!==6243 || !overlay.institutions || Object.keys(overlay.institutions).length!==1247) throw Error('Pinned overlay version mismatch');
 if(Object.keys(candidates).some(id=>Object.hasOwn(overlay.institutions,id))) throw Error('Candidate collides with pinned overlay');
 if(!Object.hasOwn(overlay.institutions,'208822')) throw Error('George Fox baseline missing');
 const describe=id=>Object.hasOwn(candidates,id)?{...candidates[id],unitid:id,display:'descriptive_only',allow_admissions_category:false}:null;
 return Object.freeze({describe,baselineEntry:id=>overlay.institutions[id]||null,canClassify:id=>id!=='208822'&&!Object.hasOwn(candidates,id),counts:{baseline:1247,descriptiveCandidates:2,admissionGates:1}});
}
module.exports={createStagingView};
