/* Explicit publication authorization and field-level provenance gate.
 * The public approval list is intentionally empty until independent review
 * and direct user approval. This does not itself verify a source.
 */
(function(root){
  "use strict";
  const BANDS=["0_30k","30_48k","48_75k","75_110k","110k_plus"];
  const CAREERS=["data","education","health","business"];
  const ENROLLMENT=["undergraduate","total"];
  const URL_OK=value=>{
    if(typeof value!=="string")return false;
    try{const u=new URL(value);return u.protocol==="https:"&&Boolean(u.hostname)&&!u.username&&!u.password;}catch{return false;}
  };
  const validYear=n=>Number.isInteger(n)&&n>=2000&&n<=2100;
  const validUnitid=x=>typeof x==="string"&&/^[0-9]{6}$/.test(x);
  function evidenceOK(value,evidence,isCost=false){
    if(!evidence||typeof evidence!=="object")return false;
    const status=evidence.status;
    if(value===null){
      if(!["UNKNOWN","NOT_APPLICABLE","SUPPRESSED"].includes(status))return false;
      if(status==="SUPPRESSED"&&(!URL_OK(evidence.source_url)||!validYear(evidence.reporting_year)))return false;
      return true;
    }
    if(status!=="VERIFIED"||!URL_OK(evidence.source_url)||!validYear(evidence.reporting_year))return false;
    return !isCost||(typeof evidence.cohort_map_reference==="string"&&evidence.cohort_map_reference.trim().length>0);
  }
  function validate(payload,manifest){
    if(!payload||payload.schema_version!==1||!Array.isArray(payload.records)||!payload.records.length)return {ok:false,reason:"Invalid data bundle."};
    if(!manifest||manifest.schema_version!==1||!Array.isArray(manifest.approved_unitids))return {ok:false,reason:"Publication approval manifest unavailable."};
    const approvals=new Map();
    for(const a of manifest.approved_unitids){
      if(!a||!validUnitid(a.unitid)||a.approved_by!=="user"||
         typeof a.approval_reference!=="string"||!a.approval_reference.trim()||
         typeof a.approved_on!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(a.approved_on)||
         approvals.has(a.unitid))return {ok:false,reason:"Malformed or duplicate publication approval."};
      approvals.set(a.unitid,a);
    }
    const seen=new Set();
    for(const r of payload.records){
      if(!r||!validUnitid(r.unitid)||seen.has(r.unitid)||!approvals.has(r.unitid)||
         r.publication_status!=="APPROVED"||r.publication_approved_by_user!==true)
        return {ok:false,reason:"Institution lacks explicit, unique user publication approval."};
      seen.add(r.unitid);
      const p=r.field_provenance;
      if(!p||typeof p!=="object")return {ok:false,reason:"Field-level provenance missing."};
      for(const k of ["setting","housing","access","aid"]){
        if(!Object.hasOwn(r,k)||!evidenceOK(r[k],p[k]))return {ok:false,reason:"Missing provenance: "+k};
      }
      // No public accessibility score until an independently approved scoring rubric exists.
      if(r.access!==null)return {ok:false,reason:"Campus-wide accessibility rating not authorized."};
      if(Array.isArray(r.aid)&&r.aid.length===0)return {ok:false,reason:"Empty aid list cannot establish no aid."};
      for(const [group,keys] of [["cost",BANDS],["careers",CAREERS],["enrollment",ENROLLMENT]]){
        if(!r[group]||typeof r[group]!=="object")return {ok:false,reason:"Missing "+group+" values."};
        for(const key of keys){
          const v=r[group][key];
          if(!Object.hasOwn(r[group],key)||!evidenceOK(v,p[group+"."+key],group==="cost"))
            return {ok:false,reason:"Missing provenance: "+group+"."+key};
          if(group==="enrollment"&&v!==null&&(!Number.isInteger(v)||v<0))
            return {ok:false,reason:"Invalid enrollment count."};
        }
      }
      if(r.testing_policy&&r.testing_policy!=="unknown"){
        const policy=root.MatcherInstitutionPolicy;
        if(!policy||!policy.review(r).reviewed)return {ok:false,reason:"Testing policy lacks reviewed source/year."};
      }
    }
    return {ok:true,reason:"All records appear on the explicit approval list with required field evidence."};
  }
  const api={validate,evidenceOK};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.MatcherPublicationGate=api;
})(typeof window!=="undefined"?window:globalThis);
