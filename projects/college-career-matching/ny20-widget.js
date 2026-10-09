(function(){
'use strict';
function initialize(){
const host=document.getElementById('leh-ccx');
const pane=document.getElementById('ccx-real-institutions');
const results=document.getElementById('ny20-results');
if(!host||!pane||!results)return;
const root=host.querySelector('.ccx-grid');
const demoNotes=['ccx-mode-note','ccx-service-state','ccx-retry','ccx-request-state'].map(id=>document.getElementById(id)).filter(Boolean);
const bReal=document.getElementById('ny20-tab-real'),bDemo=document.getElementById('ny20-tab-demo');
const lookup=id=>document.getElementById(id);
const controls=['ny20-search','ny20-system','ny20-state','ny20-sector','ny20-setting','ny20-size','ny20-income','ny20-budget','ny20-hs','ny20-transfer','ny20-sat','ny20-act','ny20-housing','ny20-sort'];
const unknown='Not reported / not yet verified';
const groups=[['0_30k','$0–$30,000'],['30_48k','$30,001–$48,000'],['48_75k','$48,001–$75,000'],['75_110k','$75,001–$110,000'],['110k_plus','Over $110,000']];
const SOURCE_URL='https://raw.githubusercontent.com/hand-lauraelizabeth/hand-lauraelizabeth/main/projects/college-career-matching/data/national/manifest.v1.json';
const NATIONAL_BASE=SOURCE_URL.slice(0,SOURCE_URL.lastIndexOf('/')+1);
const PAGE_SIZE=24;
let records=[],dataVersion='not loaded',loadState='',pageNumber=1;
function val(e){if(e==null)return null;if(typeof e==='object'&&!Array.isArray(e)&&Object.prototype.hasOwnProperty.call(e,'value'))return val(e.value);return (typeof e==='number'&&Number.isFinite(e))?e:null;}
function url(v){return typeof v==='string'&&/^https:\/\/[^\s<>"']+$/i.test(v)?v:null;}
function settingGroup(code){if(code==null)return null;return ({1:'City',2:'Suburban',3:'Town',4:'Rural'})[Math.floor(code/10)]||null;}
function clean(r){
 if(!r||typeof r!=='object'||!/^[0-9]{6}(?:[0-9]{2})?$/.test(String(r.unitid||''))||typeof r.name!=='string'||!r.name.trim())return null;
 const a=r.admissions||{},h=r.housing||{},loc=r.location||{},links=r.links||{};
 return {unitid:String(r.unitid),name:r.name.trim(),city:String(r.city||''),state:String(r.state||''),system:String(r.system||'Other'),type:String(r.type||''),
 size:val(r.size),tuition:val(r.tuition_in),net:val(r.net_price),income:r.income_net_prices&&typeof r.income_net_prices==='object'?r.income_net_prices:{},
 hs:a.hs_admitted_mean&&a.hs_admitted_mean.scale==='hs_percent_100'?a.hs_admitted_mean:null,
 transfer:a.transfer_mean&&a.transfer_mean.scale==='college_gpa_4'?a.transfer_mean:null,
 historical_admissions:val(a.historical_admit_rate),sat_avg:val(a.sat_avg),act_mid:val(a.act_mid),
 subject_mix:Array.isArray(r.subject_mix)?r.subject_mix:null, subject_labels:r.subject_labels&&typeof r.subject_labels==='object'?r.subject_labels:{},
 sector:String(r.sector||''),reported_locale:val(loc.locale_code_reported),reported_setting:settingGroup(val(loc.locale_code_reported)),
 housing:String(h.type||'NOT_VERIFIED'),housing_price:val(h.starting_price),housing_period:String(h.price_period||''),housing_year:String(h.rate_year||''),
 office:String((r.accessibility||{}).office||''),locale:loc.locale_independently_verified===true?String(loc.locale_label_provisional||''):null,
 relocation:String(loc.relocation_note||''),programs:Array.isArray(r.programs)?r.programs:null,
 links:Object.fromEntries(Object.entries(links).filter(([k,v])=>url(v)).map(([k,v])=>[k,url(v)])),score_authorized:false};
}
function normalize(data){
 if(!data||data.projection_kind!=='institution_reference'||data.data_publication_scope!=='DESCRIPTIVE_INSTITUTION_REFERENCE_ONLY'||data.scoring_authorized!==false||data.admission_predictions_authorized!==false||data.program_ranking_authorized!==false||!Array.isArray(data.institutions))throw Error('Dataset is not authorized for descriptive institution display');
 const ids=new Set(),arr=[];for(const raw of data.institutions){const o=clean(raw);if(!o||ids.has(o.unitid))continue;ids.add(o.unitid);arr.push(o)}
 if(!arr.length)throw Error('No valid institution records');return {records:arr,version:String(data.data_version||'unversioned')};
}
const el=(tag,cl='',txt)=>{const x=document.createElement(tag);if(cl)x.className=cl;if(txt!==undefined&&txt!==null)x.textContent=String(txt);return x};
const fmt=n=>n===null?unknown:'$'+Math.round(n).toLocaleString('en-US');
const number=n=>n===null?unknown:Math.round(n).toLocaleString('en-US');
function link(group,label,target){const u=url(target);if(!u)return;const a=el('a','',label);a.href=u;a.target='_blank';a.rel='noopener noreferrer';group.append(a)}
function addField(dl,k,value){const dt=el('dt','',k),dd=el('dd','',value==null?unknown:value);dl.append(dt,dd)}
function scoreDesc(rec,key,input,unit){const a=rec[key];if(!a||typeof a.value!=='number')return unknown;
 const baseline=(key==='hs'?`${a.value.toFixed(1)} / 100`:a.value.toFixed(2)+' / 4.0');
 if(input===null)return `${baseline} admitted-cohort mean (${a.cohort||'cohort unspecified'}); not a cutoff`;
 const diff=input-a.value;
 return `${baseline} admitted-cohort mean; your input is ${Math.abs(diff).toFixed(unit==='hs'?1:2)} ${unit==='hs'?'points':'GPA points'} ${diff>=0?'above':'below'} that historical mean—not admission odds`;
}
function card(rec,inputs){
 const c=el('article','ny20-card'); c.append(el('h3','',rec.name),el('p','ny20-meta',`${rec.city||'Location not confirmed'}, ${rec.state||'state unreported'} · ${rec.system} · UNITID ${rec.unitid}`));
 const dl=el('dl');addField(dl,'Undergraduates',number(rec.size));
 let net=inputs.income==='overall'?rec.net:val(rec.income[inputs.income]);
 addField(dl,inputs.income==='overall'?'Average net price':'Income-band net price',fmt(net));
 if(inputs.budget!==null)addField(dl,'Budget comparison',net===null?'Unknown price — retained':net>inputs.budget?'Reported average above selected reference (not filtered)':'Reported average within selected reference (not a quote)');
 addField(dl,'In-state tuition',fmt(rec.tuition));
 if(rec.sat_avg!==null)addField(dl,'Reported SAT average',number(rec.sat_avg)+' / 1600 (historical aggregate, not a cutoff)');
 if(rec.act_mid!==null)addField(dl,'Reported ACT composite midpoint',number(rec.act_mid)+' / 36 (historical aggregate, not a cutoff)');
 if(inputs.sat!==null)addField(dl,'SAT input vs reported average',rec.sat_avg===null?'No comparable SAT aggregate reported — kept in results':`${inputs.sat} vs ${rec.sat_avg} reported mean; descriptive difference only, not admission likelihood`);
 if(inputs.act!==null)addField(dl,'ACT input vs reported midpoint',rec.act_mid===null?'No comparable ACT aggregate reported — kept in results':`${inputs.act} vs ${rec.act_mid} reported composite midpoint; descriptive difference only, not admission likelihood`);
 if(rec.reported_setting)addField(dl,'Campus setting',rec.reported_setting+' · Scorecard locale '+rec.reported_locale+'; 2025 IPEDS confirmation pending');
 if(rec.subject_mix?.length){const top=rec.subject_mix.slice(0,3).map(([code,share])=>(rec.subject_labels[code]||'CIP '+code)+' ('+(share*100).toFixed(0)+'%)').join(' · '); addField(dl,'Reported academic-field distribution',top+' · historical field mix, not a current majors list');}
 addField(dl,'Freshman academic profile',scoreDesc(rec,'hs',inputs.hs,'hs'));
 addField(dl,'Transfer academic profile',scoreDesc(rec,'transfer',inputs.transfer,'transfer'));
 const housingLabels={CAMPUS_OPERATED_RESIDENCES:'Institution-operated residence information',PARTNER_CAMPUS_SUNY_PLATTSBURGH_HALLS:'Partner-campus housing arrangement',NO_INSTITUTION_OWNED_HOUSING:'No institution-owned housing reported',AVAILABLE_OFF_CAMPUS_COLLEGE_AFFILIATED:'College-affiliated off-campus housing reference',NOT_VERIFIED:'Housing arrangement not verified'};
 addField(dl,'Housing',housingLabels[rec.housing]||'Housing arrangements require confirmation');
 if(rec.housing_price!==null)addField(dl,'Published room rate',`${fmt(rec.housing_price)} starting · ${rec.housing_period||'period not verified'} · ${rec.housing_year||'year not verified'}`);
 addField(dl,'Accessible routes',unknown);
 if(inputs.housing)addField(dl,'Housing priority','Room and accessible-room vacancies are not verified; contact the provider');
 c.append(dl);
 if(rec.relocation)c.append(el('p','ny20-caveat',rec.relocation));
 c.append(el('p','ny20-unknown','Program-specific offerings, prerequisites, guaranteed transfer credits, admission probabilities, and room/route accessibility are not yet verified in this dataset. Missing values do not mean zero or unavailable.'));
 const l=el('div','ny20-links');link(l,'Programs',rec.links.programs);link(l,'Accessibility services',rec.links.disability_services);link(l,'Housing details',rec.links.housing);link(l,'Financial aid calculator',rec.links.net_price_calculator);link(l,'Transfer resources',rec.links.transfer);link(l,'Institution website',rec.links.institution_website);c.append(l);
 c.append(el('p','ny20-meta','Source: College Scorecard institution extract, June 10, 2026. Underlying price/enrollment cohort years may differ. Academic profiles: cited admitted cohorts, not eligibility criteria.'));
 return c;
}
function inputNumber(id,min,max){const value=String(lookup(id)?.value||'').trim();if(!value)return null;const n=Number(value);return Number.isFinite(n)&&n>=min&&n<=max?n:null;}
function filter(){const s=(lookup('ny20-search')?.value||'').trim().toLowerCase();const sy=lookup('ny20-system')?.value||'';const st=lookup('ny20-state')?.value||'';const sector=lookup('ny20-sector')?.value||'';const setting=lookup('ny20-setting')?.value||'';const size=lookup('ny20-size')?.value||'';const sort=lookup('ny20-sort')?.value||'name';
 const pass=records.filter(r=>{
 if(s&&!`${r.name} ${r.city} ${r.state} ${r.system} ${r.unitid}`.toLowerCase().includes(s))return false;
 if(sy&&r.system!==sy)return false;if(st&&r.state!==st)return false;
 if(sector&&r.sector&&r.sector!==sector)return false;
 // Unknown setting is retained; a missing locale is not proof of an incompatible campus.
 if(setting&&r.reported_setting&&r.reported_setting!==setting)return false;
 // A missing size is preserved as unknown rather than excluded by a numerical filter.
 if(r.size!==null&&size==='small'&&r.size>=5000)return false;
 if(r.size!==null&&size==='medium'&&(r.size<5000||r.size>=15000))return false;
 if(r.size!==null&&size==='large'&&r.size<15000)return false;
 return true});
 pass.sort((a,b)=>sort==='size_desc'?(b.size??-1)-(a.size??-1)||a.name.localeCompare(b.name):sort==='size_asc'?(a.size??Infinity)-(b.size??Infinity)||a.name.localeCompare(b.name):a.name.localeCompare(b.name));return pass;
}
function render(){if(!records.length)return;const inp={income:lookup('ny20-income')?.value||'overall',budget:inputNumber('ny20-budget',0,1000000),hs:inputNumber('ny20-hs',0,100),transfer:inputNumber('ny20-transfer',0,4),sat:inputNumber('ny20-sat',400,1600),act:inputNumber('ny20-act',1,36),housing:!!lookup('ny20-housing')?.checked};
 const arr=filter(),frag=document.createDocumentFragment(),shown=Math.min(arr.length,pageNumber*PAGE_SIZE);
 for(const r of arr.slice(0,shown))frag.append(card(r,inp));
 if(!arr.length)frag.append(el('p','ny20-empty','No institutions meet those confirmed filters. Try a broader location or school-size range.'));
 if(shown<arr.length){const more=el('button','ny20-more',`Show ${Math.min(PAGE_SIZE,arr.length-shown)} more schools`);more.type='button';more.addEventListener('click',()=>{pageNumber+=1;render();});frag.append(more);}
 results.replaceChildren(frag);lookup('ny20-count').textContent=`Showing ${shown} of ${arr.length} matching institutions · ${records.length} in source · descriptive only · ${dataVersion}`;
}
function setOptions(id,values){const sel=lookup(id);if(!sel)return;for(const v of values){if(!v)continue;const x=el('option','',v);x.value=v;sel.append(x);}}
function activate(payload,{preservePilot=false}={}){const d=normalize(payload);
 if(preservePilot){const prior=new Map(records.map(x=>[x.unitid,x]));d.records=d.records.map(x=>{const y=prior.get(x.unitid);if(!y)return x;return {...x,system:y.system,type:y.type,hs:y.hs,transfer:y.transfer,housing:y.housing,housing_price:y.housing_price,housing_period:y.housing_period,housing_year:y.housing_year,office:y.office,relocation:y.relocation,links:{...x.links,...y.links},subject_mix:x.subject_mix,subject_labels:x.subject_labels};});}
 records=d.records;dataVersion=d.version;pageNumber=1;
 for(const id of ['ny20-system','ny20-state','ny20-sector']){const elSel=lookup(id);if(elSel)while(elSel.options.length>1)elSel.remove(1);}
 setOptions('ny20-system',[...new Set(records.map(x=>x.system))].sort());setOptions('ny20-state',[...new Set(records.map(x=>x.state))].sort());setOptions('ny20-sector',[...new Set(records.map(x=>x.sector))].sort());render();
}
function mode(real){pane.hidden=!real;if(root)root.hidden=real;for(const n of demoNotes)n.hidden=real;bReal.setAttribute('aria-pressed',String(real));bDemo.setAttribute('aria-pressed',String(!real));}
bReal.addEventListener('click',()=>mode(true));bDemo.addEventListener('click',()=>mode(false));
for(const id of controls)lookup(id)?.addEventListener('input',()=>{pageNumber=1;render();});
const embedded=lookup('ny20-embedded-data');
try{activate(JSON.parse(embedded.textContent));loadState='bundled';}catch(e){results.replaceChildren(el('p','ny20-empty','Institution records could not be loaded; the program demonstration remains available.'));loadState='failed';}
mode(loadState!=='failed');
// National Scorecard source shards are metadata/identity evidence, never production scoring input.
const national=(async()=>{
 if(typeof fetch!=='function')return;
 const getJSON=async u=>{const r=await fetch(u,{cache:'no-store'});if(!r.ok)throw Error('Source unavailable');return r.json();};
 try{
  const manifest=await getJSON(SOURCE_URL);
  if(!manifest||manifest.schema_version!=='1.0'||manifest.projection_kind!=='institution_reference'||manifest.data_publication_scope!=='DESCRIPTIVE_INSTITUTION_REFERENCE_ONLY'||manifest.scoring_authorized!==false||manifest.admission_predictions_authorized!==false||manifest.program_ranking_authorized!==false||!Array.isArray(manifest.row_layout)||!Array.isArray(manifest.shards)||manifest.shards.length<1||manifest.shards.length>200||!Number.isInteger(manifest.expected_records)||manifest.expected_records<1||manifest.expected_records>30000)throw Error('Manifest rejected');
  const expected=['unitid','name','city','state','control','predominant_degree','highest_degree','size','tuition_in','tuition_out','annual_cost','net_price','income_net_prices','admit_rate','sat_avg','act_mid','locale_code','latitude','longitude','institution_url','net_price_calculator_url','subject_mix','accreditation_agency_as_reported'];
  if(manifest.row_layout.length<3||manifest.row_layout.length>80||new Set(manifest.row_layout).size!==manifest.row_layout.length||!manifest.row_layout.every(x=>typeof x==='string'&&/^[a-z][a-z0-9_]*$/.test(x))||!['unitid','name','state'].every(x=>manifest.row_layout.includes(x)))throw Error('Missing required institution identity fields');
  const list=[],seenParts=new Set();
  for(let i=0;i<manifest.shards.length;i+=4){
   const batch=manifest.shards.slice(i,i+4);
   const received=await Promise.all(batch.map(async sh=>{
    if(!sh||!/^national-[0-9]{2,3}\.json$/.test(sh.file)||!Number.isInteger(sh.count)||sh.count<1||sh.count>520)throw Error('Invalid source descriptor');
    const part=await getJSON(NATIONAL_BASE+sh.file);if(part.schema_version!=='1.0'||!Number.isInteger(part.part)||!Array.isArray(part.records)||part.records.length!==sh.count)throw Error('Invalid source shard');return part;
   }));
   for(const part of received){if(seenParts.has(part.part))throw Error('Duplicate source shard');seenParts.add(part.part);list.push(...part.records);}
  }
  if(list.length!==manifest.expected_records||seenParts.size!==manifest.shards.length)throw Error('Incomplete source coverage');
  const incomeKeys=['0_30k','30_48k','48_75k','75_110k','110k_plus'];
  const normalized=list.map(a=>{
   if(!Array.isArray(a)||a.length!==manifest.row_layout.length)throw Error('Unexpected source record');
   const z=Object.fromEntries(manifest.row_layout.map((field,j)=>[field,a[j]]));
   if(!/^[0-9]{6}(?:[0-9]{2})?$/.test(String(z.unitid))||typeof z.name!=='string'||!z.name.trim())throw Error('Invalid institution identity');
   const controlLabel={1:'Public',2:'Private nonprofit',3:'Private for-profit'};
   const income=Object.fromEntries(incomeKeys.map((k,j)=>[k,{value:Array.isArray(z.income_net_prices)?z.income_net_prices[j]:null}]));
   return {unitid:z.unitid,name:z.name,city:z.city,state:z.state,system:controlLabel[z.control]||'Control not reported',sector:controlLabel[z.control]||'',type:'Source predominant degree '+(z.predominant_degree??'unknown'),
   size:{value:z.size},tuition_in:{value:z.tuition_in},net_price:{value:z.net_price},income_net_prices:income,
   admissions:{hs_admitted_mean:null,transfer_mean:null,historical_admit_rate:{value:z.admit_rate},sat_avg:{value:z.sat_avg},act_mid:{value:z.act_mid},probability:null},
   location:{locale_code_reported:z.locale_code,locale_independently_verified:false},
   housing:{type:'NOT_VERIFIED',starting_price:null,vacancy_verified:false,accessible_vacancy_verified:false},
   accessibility:{routes_verified:false,quality_score:null},programs:null,transfer_rules:null,subject_mix:z.subject_mix,subject_labels:manifest.cip2_labels||{},
   links:{institution_website:z.institution_url,net_price_calculator:z.net_price_calculator_url},score_authorized:false};
  });
  if(new Set(normalized.map(a=>a.unitid)).size!==manifest.expected_records)throw Error('Duplicate institution keys');
  activate({...manifest,institutions:normalized},{preservePilot:true});loadState='national';
 }catch(e){const label=lookup('ny20-count');if(label)label.textContent+=' · nationwide update unavailable, pilot data retained';}
})();

// Separate from the governed program-scoring service: no student data are transmitted.
window.CCXInstitutionReference={normalize,refresh:render,version:()=>dataVersion};
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialize,{once:true});else initialize();
})();