/* Institution testing-policy evidence. No admission probability or cutoff is inferred. */
(function(root){
  "use strict";
  const MODES=new Set(["omit","sat","act","test_optional","test_blind"]);
  const POLICIES=new Set(["required","optional","blind","unknown"]);
  function review(record){
    const policy=POLICIES.has(record?.testing_policy)?record.testing_policy:"unknown";
    const source=typeof record?.testing_policy_source==="string"?record.testing_policy_source.trim():"";
    const year=record?.testing_policy_year;
    const verified=record?.testing_policy_verified===true;
    const vintage=Number.isInteger(year)&&year>=2000&&year<=2100;
    const hasSource=/^https:\/\/[^\s/]+\.[^\s/]+/.test(source);
    const reviewed=verified&&vintage&&hasSource&&policy!=="unknown";
    return {policy,source:hasSource?source:null,year:vintage?year:null,reviewed};
  }
  function match(record,mode){
    if(!MODES.has(mode))return {include:false,unknown:true,reason:"Invalid testing preference."};
    if(mode!=="test_optional"&&mode!=="test_blind")return {include:true,unknown:false,reason:"No institutional policy filter selected."};
    const evidence=review(record);
    if(!evidence.reviewed)return {include:false,unknown:true,reason:"Institution testing policy is not independently reviewed with a source and reporting year."};
    const include=mode==="test_blind"?evidence.policy==="blind":evidence.policy==="optional"||evidence.policy==="blind";
    return {include,unknown:false,reason:include?"Reviewed policy meets preference.":"Reviewed policy does not meet preference."};
  }
  function explanation(record,mode){
    const e=review(record);
    if(!e.reviewed)return "Institution testing policy unverified; no assumption about required scores.";
    const label={required:"Testing required",optional:"Test-optional",blind:"Test-blind"}[e.policy];
    const scores=(mode==="sat"||mode==="act")&&e.policy==="blind"?" Submitted scores are not considered.":"";
    return label+" (reporting year "+e.year+"). Source: "+e.source+"."+scores+" No admission probability is estimated.";
  }
  const api={review,match,explanation};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.MatcherInstitutionPolicy=api;
})(typeof window!=="undefined"?window:globalThis);
