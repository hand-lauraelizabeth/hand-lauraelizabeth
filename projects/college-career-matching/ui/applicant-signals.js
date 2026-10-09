/* Applicant signals: planning inputs only. Never predict admission or infer a cutoff. */
(function(root){
  "use strict";
  const finite = x => typeof x === "number" && Number.isFinite(x);
  function validateGpa(value, scale, weighting){
    if(value === "" || value === null || value === undefined) return {ok:true,missing:true};
    const n=Number(value);
    const max=Number(scale);
    if(!["4","5","100"].includes(String(scale)) || !["weighted","unweighted"].includes(weighting))
      return {ok:false,reason:"Choose a valid GPA scale and weighting."};
    if(!Number.isFinite(n)||n<0||n>max) return {ok:false,reason:"GPA must be between zero and the selected scale maximum."};
    return {ok:true,value:n,scale:max,weighting,missing:false};
  }
  function validateTesting(mode,satTotal,actComposite,sections={}){
    if(!["omit","sat","act","test_optional","test_blind"].includes(mode))return {ok:false,reason:"Unknown testing choice."};
    if(["omit","test_optional","test_blind"].includes(mode))return {ok:true,mode,omitted:true};
    const raw=mode==="sat"?satTotal:actComposite;
    if(raw===""||raw===null||raw===undefined)return {ok:false,reason:"Enter a score or select no score."};
    const sat=mode==="sat",n=Number(raw);
    if(!Number.isInteger(n)||n<(sat?400:1)||n>(sat?1600:36)||(sat&&n%10!==0))return {ok:false,reason:"Invalid reported score."};
    const keys=sat?["satReadingWriting","satMath"]:["actEnglish","actMath","actReading","actScience"];
    const values={};
    for(const key of keys){
      const rawSection=sections?.[key];
      if(rawSection===""||rawSection==null)continue;
      const v=Number(rawSection);
      if(!Number.isInteger(v)||v<(sat?200:1)||v>(sat?800:36)||(sat&&v%10!==0))return {ok:false,reason:"Invalid "+key+" section score."};
      values[key]=v;
    }
    if(sat&&values.satReadingWriting!=null&&values.satMath!=null&&values.satReadingWriting+values.satMath!==n)return {ok:false,reason:"SAT total must equal section sum."};
    return {ok:true,mode,value:n,sections:values,omitted:false};
  }
  function validEnrollment(record,kind){
    const value=record?.enrollment?.[kind];
    return Number.isInteger(value)&&value>=0?value:null;
  }
  function sizeMatch(record,kind,min,max){
    if(kind==="any")return {include:true,reason:"No enrollment-size constraint."};
    const n=validEnrollment(record,kind);
    if(n===null)return {include:false,unknown:true,reason:"Enrollment count unknown for selected definition."};
    if(min!==null&&n<min||max!==null&&n>max)return {include:false,unknown:false,reason:"Outside selected enrollment range."};
    return {include:true,value:n,reason:"Enrollment count meets selected range."};
  }
  function testingPolicy(record){
    const policy=record?.testing_policy;
    return ["required","optional","blind","unknown"].includes(policy)?policy:"unknown";
  }
  function policyNote(record,mode){
    const policy=testingPolicy(record);
    if(policy==="blind")return "Test-blind: submitted scores are not considered; confirm the current official policy.";
    if(policy==="optional")return "Test-optional: scores may be omitted; confirm the current official policy.";
    if(policy==="required")return "Testing required according to the record; verify current policy and accepted test types.";
    return "Testing policy unknown; confirm directly with admissions.";
  }
  const api={validateGpa,validateTesting,validEnrollment,sizeMatch,testingPolicy,policyNote};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.MatcherSignals=api;
})(typeof window!=="undefined"?window:globalThis);
