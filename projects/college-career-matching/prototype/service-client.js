/* Browser service boundary: UI consumes contracts, never recalculates model semantics. */
export class MatchingServiceClient {
  constructor({mode='fixture',baseUrl='',fixtureUrl='contract-fixtures.json',runtimeConfig=null}={}){this.mode=mode;this.baseUrl=baseUrl;this.fixtureUrl=fixtureUrl;this.runtimeConfig=runtimeConfig;this.fixtures=null}
  async load(){if(this.mode==='fixture')this.fixtures=await fetch(this.fixtureUrl).then(r=>{if(!r.ok)throw new Error('Unable to load contract fixtures');return r.json()});return this}
  async call(name,{method='GET',body=null,path='' }={}){
    if(this.mode==='fixture'){const v=this.fixtures?.[name];if(v===undefined)throw new Error(`Missing fixture response: ${name}`);return structuredClone(v)}
    const r=await fetch(`${this.baseUrl}${path}`,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):null});if(!r.ok)throw new Error(`${name} failed: ${r.status}`);return r.json()
  }
  metadata(){return this.call('metadata',{path:'/metadata'})}
  options(){return this.call('options',{path:'/options'})}
  match(request){return this.call('match',{method:'POST',path:'/match',body:request})}
  candidate(id){return this.call(`candidate:${id}`,{path:`/candidate/${encodeURIComponent(id)}`})}
  compare(candidateIds,context={}){return this.call('compare',{method:'POST',path:'/compare',body:{schema_version:'1.0',candidate_ids:candidateIds,...context}})}
}
export function validateRuntimeConfig(config){
 if(!config||config.schema_version!=='1.0')throw new Error('runtime: unsupported schema_version')
 if(!['fixture','production'].includes(config.mode))throw new Error('runtime: unsupported mode')
 if(config.mode==='fixture'){
  if(config.production_authorized!==false)throw new Error('runtime: fixture cannot be production authorized')
  if(!config.fixture_url)throw new Error('runtime: fixture_url required')
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
 if(metadata.production_authorized!==true||metadata.serving_state!=='production')throw new Error('runtime: service metadata is not production authorized')
 if(metadata.data_version!==x.data_version||metadata.model_version!==x.model_version)throw new Error('runtime: service version identity mismatch')
 if((metadata.snapshot?.output_sha256||'').toLowerCase()!==x.snapshot_sha256.toLowerCase())throw new Error('runtime: snapshot identity mismatch')
 return metadata
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
   const rec=result.recommendation
   if(!rec||rec.production_authorized!==productionAuthorized)throw new Error('match: recommendation production authorization mismatch')
   if(rec.status==='review_eligible_ranked'&&rec.review_eligibility!=='eligible_for_review')throw new Error('match: ranked result is not review-eligible')
   if(rec.status==='review_eligible_ranked'&&(!Number.isInteger(rec.rank)||rec.rank<1))throw new Error('match: invalid ranked result')
  }
 }
 if(kind==='compare'&&!Array.isArray(response.candidates))throw new Error('compare: candidates must be an array')
 return response
}
