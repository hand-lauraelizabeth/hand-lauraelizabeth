/* Browser service boundary: UI consumes contracts, never recalculates model semantics. */
export class MatchingServiceClient {
  constructor({mode='fixture',baseUrl='',fixtureUrl='contract-fixtures.json'}={}){this.mode=mode;this.baseUrl=baseUrl;this.fixtureUrl=fixtureUrl;this.fixtures=null}
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
export function assertContract(response,kind){
 if(!response||response.schema_version!=='1.0')throw new Error(`${kind}: unsupported schema_version`)
 if(kind==='metadata'&&(!response.data_version||!response.model_version||!response.snapshot))throw new Error('metadata: missing governed version/readiness fields')
 if(kind==='options'&&(!response.options||!response.constraint_capabilities))throw new Error('options: missing governed capabilities')
 if(kind==='match'){
  if(!Array.isArray(response.results))throw new Error('match: results must be an array')
  if(!response.ordering||response.ordering.production_authorized!==false)throw new Error('match: missing safe ordering metadata')
  if(!['deterministic_unranked','review_eligible_ranking'].includes(response.ordering.mode))throw new Error('match: unsupported ordering mode')
  if(response.ordering.mode==='review_eligible_ranking'&&!/^rankctx_[0-9a-f]{24}$/.test(response.ordering.ranking_context_id||''))throw new Error('match: invalid ranking context')
  for(const result of response.results){
   const rec=result.recommendation
   if(!rec||rec.production_authorized!==false)throw new Error('match: missing safe recommendation metadata')
   if(rec.status==='review_eligible_ranked'&&rec.review_eligibility!=='eligible_for_review')throw new Error('match: ranked result is not review-eligible')
   if(rec.status==='review_eligible_ranked'&&(!Number.isInteger(rec.rank)||rec.rank<1))throw new Error('match: invalid ranked result')
  }
 }
 if(kind==='compare'&&!Array.isArray(response.candidates))throw new Error('compare: candidates must be an array')
 return response
}
