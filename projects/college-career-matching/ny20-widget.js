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
const controls=['ny20-search','ny20-system','ny20-state','ny20-size','ny20-income','ny20-budget','ny20-hs','ny20-transfer','ny20-housing','ny20-sort'];
const unknown='Not reported / not yet verified';
const groups=[['0_30k','$0–$30,000'],['30_48k','$30,001–$48,000'],['48_75k','$48,001–$75,000'],['75_110k','$75,001–$110,000'],['110k_plus','Over $110,000']];
const SOURCE_URL='https://raw.githubusercontent.com/hand-lauraelizabeth/hand-lauraelizabeth/main/projects/college-career-matching/data/ny20-institution-evidence.v1.json';
let records=[],dataVersion='not loaded',loadState='';
function val(e){if(e==null)return null;if(typeof e==='object'&&!Array.isArray(e)&&Object.prototype.hasOwnProperty.call(e,'value'))return val(e.value);return (typeof e==='number'&&Number.isFinite(e))?e:null;}
function url(v){return typeof v==='string'&&/^https:\/\/[^\s<>"']+$/i.test(v)?v:null;}
function clean(r){
 if(!r||typeof r!=='object'||!/^[0-9]{6}$/.test(String(r.unitid||''))||typeof r.name!=='string'||!r.name.trim())return null;
 const a=r.admissions||{},h=r.housing||{},loc=r.location||{},links=r.links||{};
 return {unitid:String(r.unitid),name:r.name.trim(),city:String(r.city||''),state:String(r.state||''),system:String(r.system||'Other'),type:String(r.type||''),
 size:val(r.size),tuition:val(r.tuition_in),net:val(r.net_price),income:r.income_net_prices&&typeof r.income_net_prices==='object'?r.income_net_prices:{},
 hs:a.hs_admitted_mean&&a.hs_admitted_mean.scale==='hs_percent_100'?a.hs_admitted_mean:null,
 transfer:a.transfer_mean&&a.transfer_mean.scale==='college_gpa_4'?a.transfer_mean:null,
 historical_admissions:val(a.historical_admit_rate),
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
function filter(){const s=(lookup('ny20-search')?.value||'').trim().toLowerCase();const sy=lookup('ny20-system')?.value||'';const st=lookup('ny20-state')?.value||'';const size=lookup('ny20-size')?.value||'';const sort=lookup('ny20-sort')?.value||'name';
 const pass=records.filter(r=>{
 if(s&&!`${r.name} ${r.city} ${r.state} ${r.system} ${r.unitid}`.toLowerCase().includes(s))return false;
 if(sy&&r.system!==sy)return false;if(st&&r.state!==st)return false;
 // A missing size is preserved as unknown rather than excluded by a numerical filter.
 if(r.size!==null&&size==='small'&&r.size>=5000)return false;
 if(r.size!==null&&size==='medium'&&(r.size<5000||r.size>=15000))return false;
 if(r.size!==null&&size==='large'&&r.size<15000)return false;
 return true});
 pass.sort((a,b)=>sort==='size_desc'?(b.size??-1)-(a.size??-1)||a.name.localeCompare(b.name):sort==='size_asc'?(a.size??Infinity)-(b.size??Infinity)||a.name.localeCompare(b.name):a.name.localeCompare(b.name));return pass;
}
function render(){if(!records.length)return;const inp={income:lookup('ny20-income')?.value||'overall',budget:inputNumber('ny20-budget',0,1000000),hs:inputNumber('ny20-hs',0,100),transfer:inputNumber('ny20-transfer',0,4),housing:!!lookup('ny20-housing')?.checked};
 const arr=filter(),frag=document.createDocumentFragment();for(const r of arr)frag.append(card(r,inp));if(!arr.length)frag.append(el('p','ny20-empty','No institutions meet those confirmed filters. Try a broader location or school-size range.'));
 results.replaceChildren(frag);lookup('ny20-count').textContent=`Showing ${arr.length} of ${records.length} institutions · descriptive records only · ${dataVersion}`;
}
function setOptions(id,values){const sel=lookup(id);if(!sel)return;for(const v of values){if(!v)continue;const x=el('option','',v);x.value=v;sel.append(x);}}
function activate(payload){const d=normalize(payload);records=d.records;dataVersion=d.version;
 for(const id of ['ny20-system','ny20-state']){const elSel=lookup(id);if(elSel)while(elSel.options.length>1)elSel.remove(1);}
 setOptions('ny20-system',[...new Set(records.map(x=>x.system))].sort());setOptions('ny20-state',[...new Set(records.map(x=>x.state))].sort());render();
}
function mode(real){pane.hidden=!real;if(root)root.hidden=real;for(const n of demoNotes)n.hidden=real;bReal.setAttribute('aria-pressed',String(real));bDemo.setAttribute('aria-pressed',String(!real));}
bReal.addEventListener('click',()=>mode(true));bDemo.addEventListener('click',()=>mode(false));
for(const id of controls)lookup(id)?.addEventListener('input',render);
const embedded=lookup('ny20-embedded-data');
try{activate(JSON.parse(embedded.textContent));loadState='bundled';}catch(e){results.replaceChildren(el('p','ny20-empty','Institution records could not be loaded; the program demonstration remains available.'));loadState='failed';}
mode(loadState!=='failed');
// Independently versioned public projection can expand to more schools; retain bundled fallback if unavailable.
if(typeof fetch==='function')fetch(SOURCE_URL,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('network unavailable');return r.json()}).then(d=>{activate(d);loadState='remote';}).catch(()=>{});
// Separate from the governed program-scoring service: no student data are transmitted.
window.CCXInstitutionReference={normalize,refresh:render,version:()=>dataVersion};
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialize,{once:true});else initialize();
})();