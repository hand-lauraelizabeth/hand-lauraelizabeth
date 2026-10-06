/* Browser service boundary: UI consumes contracts, never recalculates model semantics. */
export class MatchingServiceClient {
  constructor({mode='fixture',baseUrl='',fixtureUrl='contract-fixtures.json',runtimeConfig=null}={}){this.mode=mode;this.baseUrl=baseUrl;this.fixtureUrl=fixtureUrl;this.runtimeConfig=runtimeConfig;this.fixtures=null}
  async load(){if(this.mode==='fixture')this.fixtures=await fetch(this.fixtureUrl).then(r=>{if(!r.ok)throw new Error('Unable to load contract fixtures');return r.json()});return this}
  async call(name,{method='GET',body=null,path='',signal=null}={}){
    if(this.mode==='fixture'){const v=this.fixtures?.[name];if(v===undefined)throw new Error(`Missing fixture response: ${name}`);return structuredClone(v)}
    const r=await fetch(`${this.baseUrl}${path}`,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):null,signal});if(!r.ok)throw new Error(`${name} failed: ${r.status}`);return r.json()
  }
  metadata(){return this.call('metadata',{path:'/metadata'})}
  options(){return this.call('options',{path:'/options'})}
  match(request,{signal=null}={}){return this.call('match',{method:'POST',path:'/match',body:request,signal})}
  candidate(id){return this.call(`candidate:${id}`,{path:`/candidate/${encodeURIComponent(id)}`})}
  compare(candidateIds,context={}, {signal=null}={}){
    const body={schema_version:'1.0',candidate_ids:candidateIds,...context}
    if(this.mode==='fixture'){
      const template=this.fixtures?.compare
      if(!template)throw new Error('Missing fixture response: compare')
      const candidates=candidateIds.map(id=>this.fixtures?.[`candidate:${id}`])
      if(candidates.some(x=>!x))throw new Error('Missing fixture candidate detail for comparison')
      return Promise.resolve({...structuredClone(template),candidate_ids:[...candidateIds],candidates:structuredClone(candidates)})
    }
    return this.call('compare',{method:'POST',path:'/compare',body,signal})
  }
}
export function validateRuntimeConfig(config){
 if(!config||config.schema_version!=='1.0')throw new Error('runtime: unsupported schema_version')
 if(!['fixture','staging','production'].includes(config.mode))throw new Error('runtime: unsupported mode')
 if(config.mode==='fixture'){
  if(config.production_authorized!==false)throw new Error('runtime: fixture cannot be production authorized')
  if(!config.fixture_url)throw new Error('runtime: fixture_url required')
 }else if(config.mode==='staging'){
  if(config.production_authorized!==false)throw new Error('runtime: staging cannot be production authorized')
  if(!/^(https:\/\/|http:\/\/(127\.0\.0\.1|localhost|\[::1\])(?::\d+)?(?:\/|$))/.test(config.service_base_url||''))throw new Error('runtime: staging service must use HTTPS or loopback HTTP')
  const x=config.expected_identity||{}
  if(!x.data_version||!x.model_version||!/^([0-9a-f]{64})$/i.test(x.snapshot_sha256||''))throw new Error('runtime: expected staging identity missing')
 }else{
  if(config.production_authorized!==true)throw new Error('runtime: production authorization required')
  if(!/^https:\/\//.test(config.service_base_url||''))throw new Error('runtime: production service must use HTTPS')
  const x=config.expected_identity||{}
  if(!x.data_version||!x.model_version||!/^([0-9a-f]{64})$/i.test(x.snapshot_sha256||''))throw new Error('runtime: expected production identity missing')
 }
 return config
}
export function assertRuntimeMetadata(config,metadata){
 validateRuntimeConfig(config)
 if(config.mode==='fixture'){
  if(metadata.production_authorized!==false||metadata.serving_state==='production')throw new Error('runtime: fixture metadata cannot be production')
  return metadata
 }
 const x=config.expected_identity
 if(config.mode==='staging'){
  if(metadata.production_authorized!==false||metadata.serving_state==='production')throw new Error('runtime: staging metadata cannot be production')
  if(metadata.data_version!==x.data_version||metadata.model_version!==x.model_version)throw new Error('runtime: staging version identity mismatch')
  if((metadata.snapshot?.output_sha256||'').toLowerCase()!==x.snapshot_sha256.toLowerCase())throw new Error('runtime: staging snapshot identity mismatch')
  return metadata
 }
 if(metadata.production_authorized!==true||metadata.serving_state!=='production')throw new Error('runtime: service metadata is not production authorized')
 if(metadata.data_version!==x.data_version||metadata.model_version!==x.model_version)throw new Error('runtime: service version identity mismatch')
 if((metadata.snapshot?.output_sha256||'').toLowerCase()!==x.snapshot_sha256.toLowerCase())throw new Error('runtime: snapshot identity mismatch')
 return metadata
}
function assertPathways(value,label){
 if(!Array.isArray(value))throw new Error(label+': pathways must be an array')
 for(const x of value)if(!x||typeof x!=='object'||!x.soc_code||!('occupation_title' in x))throw new Error(label+': invalid pathway shape')
}
function assertCandidateShape(response,label='candidate'){
 for(const key of ['candidate_id','institution','program','affordability','aid_context','program_outcomes','transfer','career','labor_market','freshness','unknowns'])if(!(key in response))throw new Error(label+': missing '+key)
 if(!Array.isArray(response.unknowns)||!response.freshness||!Array.isArray(response.freshness.source_freshness))throw new Error(label+': invalid evidence/freshness shape')
 if(!response.career||!Number.isInteger(Number(response.career.pathway_count)))throw new Error(label+': missing career pathway count')
 assertPathways(response.career.pathways,label+' career');assertPathways(response.career.representative_pathways,label+' representative career')
 return response
}
export function assertContract(response,kind,{productionAuthorized=false}={}){
 if(!response||response.schema_version!=='1.0')throw new Error(`${kind}: unsupported schema_version`)
 if(kind==='metadata'&&(!response.data_version||!response.model_version||!response.snapshot))throw new Error('metadata: missing governed version/readiness fields')
 if(kind==='options'&&(!response.options||!response.constraint_capabilities))throw new Error('options: missing governed capabilities')
 if(kind==='match'){
  if(!Array.isArray(response.results))throw new Error('match: results must be an array')
  if(!response.ordering||response.ordering.production_authorized!==productionAuthorized)throw new Error('match: ordering production authorization mismatch')
  if(!['deterministic_unranked','review_eligible_ranking'].includes(response.ordering.mode))throw new Error('match: unsupported ordering mode')
  if(response.ordering.mode==='review_eligible_ranking'&&!/^rankctx_[0-9a-f]{24}$/.test(response.ordering.ranking_context_id||''))throw new Error('match: invalid ranking context')
  for(const result of response.results){
   const explanation=result.explanation
   if(!explanation||!Array.isArray(explanation.why_it_matches)||!Array.isArray(explanation.tradeoffs)||!Array.isArray(explanation.context)||!Array.isArray(explanation.unknowns))throw new Error('match: invalid explanation shape')
   for(const group of ['why_it_matches','tradeoffs','context','unknowns'])for(const item of explanation[group])if(!item||!item.code||!item.text||!Array.isArray(item.evidence_ids))throw new Error('match: invalid explanation record')
   const cp=result.career_pathways
   if(!cp||!Number.isInteger(Number(cp.pathway_count)))throw new Error('match: missing career pathway count')
   assertPathways(cp.pathways,'match career');assertPathways(cp.representative_pathways,'match representative career')
   const rec=result.recommendation
   if(!rec||rec.production_authorized!==productionAuthorized)throw new Error('match: recommendation production authorization mismatch')
   if(rec.status==='review_eligible_ranked'&&rec.review_eligibility!=='eligible_for_review')throw new Error('match: ranked result is not review-eligible')
   if(rec.status==='review_eligible_ranked'&&(!Number.isInteger(rec.rank)||rec.rank<1))throw new Error('match: invalid ranked result')
  }
 }
 if(kind==='candidate')assertCandidateShape(response,'candidate')
 if(kind==='compare'){
  if(!Array.isArray(response.candidates)||!Array.isArray(response.candidate_ids)||response.candidates.length!==response.candidate_ids.length)throw new Error('compare: candidate arrays are invalid')
  if(response.candidates.length<2||response.candidates.length>5)throw new Error('compare: expected 2 to 5 candidates')
  response.candidates.forEach((x,i)=>{assertCandidateShape(x,`compare candidate ${i+1}`);if(x.candidate_id!==response.candidate_ids[i])throw new Error('compare: candidate identity/order mismatch')})
  const rules=response.semantic_rules||{}
  for(const key of ['no_automatic_winner','missing_is_not_zero','current_market_is_not_long_term_outlook','institution_outcomes_are_not_program_outcomes','aid_reporting_is_not_individual_award','accreditation_absence_is_unknown_not_unaccredited'])if(rules[key]!==true)throw new Error(`compare: required semantic rule false or missing: ${key}`)
  if(!Array.isArray(response.comparison_dimensions))throw new Error('compare: comparison_dimensions must be an array')
 }
 return response
}
