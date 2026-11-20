/* Opt-in public elevation samples; no automated data requests or safe-navigation claims. */
const TransitTerrain=(()=>{
'use strict';
const RAD=Math.PI/180,R=6371008.8;
const point=(lat,lon)=>{if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)throw Error('Invalid coordinates.');return {lat,lon};};
function distance(a,b){point(a.lat,a.lon);point(b.lat,b.lon);const p=a.lat*RAD,q=b.lat*RAD,x=(b.lat-a.lat)*RAD,y=(b.lon-a.lon)*RAD,c=Math.sin(x/2)**2+Math.cos(p)*Math.cos(q)*Math.sin(y/2)**2;return 2*R*Math.asin(Math.min(1,Math.sqrt(c)));}
function usgsUrl(lat,lon){point(lat,lon);return 'https://epqs.nationalmap.gov/v1/json?'+new URLSearchParams({x:lon.toFixed(6),y:lat.toFixed(6),wkid:'4326',units:'Meters',includeDate:'true'});}
function usgsParse(body){if(body?.value===null||body?.value===undefined||body.value===''||typeof body.value==='boolean')throw Error('USGS did not provide a numeric elevation.');const meters=Number(body.value);if(!Number.isFinite(meters)||meters< -500||meters>9000)throw Error('Invalid ground elevation.');return {meters,source:'USGS 3DEP EPQS',acquired:body?.attributes?.AcquisitionDate||null,resolution:body?.resolution||null};}
function etopoUrl(lat,lon){point(lat,lon);const normalized=((lon%360)+360)%360;const query='z[('+lat.toFixed(5)+')][('+normalized.toFixed(5)+')]';return 'https://oceanwatch.pifsc.noaa.gov/erddap/griddap/ETOPO_2022_v1_60s.json?'+encodeURIComponent(query);}
function etopoParse(body){const cols=body?.table?.columnNames,rows=body?.table?.rows;if(!Array.isArray(cols)||!Array.isArray(rows)||rows.length!==1)throw Error('NOAA did not return one elevation cell.');const i=cols.indexOf('z'),raw=rows[0]?.[i],meters=Number(raw);if(i<0||raw===null||raw===''||!Number.isFinite(meters)||meters<=-99998||meters< -12000||meters>9000)throw Error('No valid NOAA elevation available.');return {meters,source:'NOAA NCEI ETOPO 2022 60s'};}
function ahead(state,km,M){const h=state.heading*RAD,m=km*1000;return M.moveLatLon(state.lat,state.lon,Math.cos(h)*m,Math.sin(h)*m);}
function assess(mode,state,sample,threshold=1800){if(!sample||!state)return {status:'unavailable'};const separation=distance(state,sample);if(separation>threshold)return {status:'stale',separation};if(mode==='flight'){const clearance=state.alt-sample.meters;return {status:clearance<0?'below-terrain':clearance<300?'low':'target',clearance,separation};}if(mode==='sub'){if(sample.meters>=0)return {status:'not-water'};const clearance=-sample.meters-state.depth;return {status:clearance<0?'below-seabed':clearance<100?'low':'target',clearance,separation};}return {status:'unavailable'};}
return {point,distance,usgsUrl,usgsParse,etopoUrl,etopoParse,ahead,assess};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitTerrain;
(function terrainUI(){
'use strict';
if(typeof document==='undefined'||typeof TransitModels==='undefined')return;
const root=document.getElementById('leh-transit');if(!root||root.dataset.terrainChallenges==='ready')return;root.dataset.terrainChallenges='ready';
const T=TransitTerrain,M=TransitModels,$=id=>document.getElementById(id);
const panel=document.createElement('section');panel.className='panel tc-lab';
panel.innerHTML='<div class="top"><div><p class="eyebrow">Geography affects decisions</p><h2>Terrain and seabed challenges</h2></div><span class="pill">Measured grid ≠ model</span></div>'+
'<p class="tc-note">Survey real geographic elevation at a simulated location. Assess terrain margins without inventing continuous terrain, actual obstacle clearance, or certified operating limits. Requests transmit only the modeled coordinates to USGS or NOAA, not your location.</p>'+
'<div id="tc-flight"><button type="button" id="tc-flight-survey">Survey terrain: here, 2 km and 5 km ahead</button><p class="tc-note">USGS 3DEP samples isolated ground points; they do not establish the terrain between them, structures, or the exact vertical datum of the modeled aircraft.</p></div>'+
'<div id="tc-sub" hidden><button type="button" id="tc-sub-survey">Survey seafloor at current position</button><p class="tc-note">NOAA ETOPO 2022 global relief, 60 arc-second cell (~1–2 km). This is not a nautical depth sounding, sea chart, or hull-clearance measurement.</p></div>'+
'<p id="tc-results" role="status" class="tc-results">No external elevation queries made.</p><p id="tc-assess" role="status" class="tc-assess">No sampled terrain challenge active.</p>'+
'<div class="actions"><button type="button" id="tc-clear" class="secondary">Clear samples</button><a href="https://epqs.nationalmap.gov/v1/docs" target="_blank" rel="noopener">USGS elevation source</a><a href="https://www.ncei.noaa.gov/products/etopo-global-relief-model" target="_blank" rel="noopener">NOAA bathymetry source</a></div>'+
'<p class="tc-note">Surveys are user-triggered and do not run continuously. Once a vehicle moves more than 1.8 km from every relevant sample, proximity-dependent assessment expires. All unmeasured terrain remains unknown.</p>';
const css=document.createElement('style');css.textContent='#leh-transit .tc-lab{display:grid;gap:.65rem}#leh-transit .tc-lab .tc-note{font-size:.85rem;line-height:1.5}#leh-transit .tc-lab [hidden]{display:none!important}#leh-transit .tc-lab .tc-results{background:#eef5ef;border:1px solid var(--border);border-radius:8px;padding:.65rem;font-size:.87rem}#leh-transit .tc-lab .tc-assess{border-left:4px solid #80958e;padding:.55rem;font-size:.9rem;font-weight:650}#leh-transit .tc-lab .tc-assess.warn{border-color:#bb7a1a;background:#fff7e6}#leh-transit .tc-lab .tc-assess.danger{border-color:#b44132;background:#fff0ee}#leh-transit .tc-lab .actions a{font-size:.8rem}';
document.head.append(css);root.querySelector('.main-stack')?.append(panel);
let mode='flight',state=null,flight=[],seabed=null,generation=0,map=null,markers=[];
const fmt=n=>Number(n).toLocaleString('en-US',{maximumFractionDigits:1});
function result(message){$('tc-results').textContent=message;}
function message(s,level=''){$('tc-assess').className='tc-assess'+(level?' '+level:'');$('tc-assess').textContent=s;}
function annotate(){
if(!state||mode==='train'){message('This feature uses flight and submarine models.');return;}
const sample=mode==='flight'?flight.reduce((best,p)=>!best||T.distance(state,p)<T.distance(state,best)?p:best,null):seabed;
const x=T.assess(mode,state,sample);
if(x.status==='unavailable'){message('No geographic sample available. Use the survey button to begin.');return;}
if(x.status==='stale'){message('No nearby surveyed elevation. Nearest measurement '+fmt(x.separation/1000)+' km away; resurvey before evaluating.');return;}
if(x.status==='not-water'){message('NOAA returned land or nonnegative elevation for this cell. Underwater clearance cannot be evaluated.','warn');return;}
if(x.status==='below-terrain'||x.status==='below-seabed'){message('MODEL CHALLENGE: nominal altitude/depth is below this nearby sampled terrain elevation by '+fmt(-x.clearance)+' m. No real collision or safe-navigation claim.','danger');return;}
const target=mode==='flight'?300:100;
if(x.status==='low'){message('MODEL CHALLENGE: '+fmt(x.clearance)+' m nominal margin at the closest sample, below the illustrative '+target+' m exercise goal.','warn');return;}
message('Nearby sample: nominal margin '+fmt(x.clearance)+' m, above the '+target+' m exercise goal at this point only. Unsampled terrain remains unknown.');
}
function showSamples(){
if(mode==='flight')result(flight.length?'USGS 3DEP surveyed points: '+flight.map(p=>p.km+' km: '+fmt(p.meters)+' m'+(p.acquired?' (data acquired '+p.acquired+')':'')).join(' · ')+'. No continuous path coverage.':'No USGS samples loaded.');
else if(mode==='sub')result(seabed?'NOAA ETOPO elevation '+fmt(seabed.meters)+' m at simulated '+seabed.lat.toFixed(4)+'°, '+seabed.lon.toFixed(4)+'° (coarse numerical relief cell).':'No NOAA samples loaded.');
}
function redrawMarkers(){
if(map)for(const marker of markers)map.removeLayer(marker);markers=[];
if(!map||!window.L)return;
for(const p of mode==='flight'?flight:seabed?[seabed]:[]){
 const c=window.L.circleMarker([p.lat,p.lon],{radius:6,color:'#fff',weight:2,fillColor:'#2d7064',fillOpacity:1}).addTo(map);
 c.bindPopup((mode==='flight'?'USGS terrain':'NOAA seafloor')+' sampled elevation '+fmt(p.meters)+' m; not a vehicle position.');markers.push(c);
}}
async function query(url){
const ac=new AbortController(),timeout=setTimeout(()=>ac.abort(),14000);
try{const response=await fetch(url,{signal:ac.signal,headers:{Accept:'application/json'}});if(!response.ok)throw Error('HTTP '+response.status);return await response.json();}finally{clearTimeout(timeout);}
}
function setMode(next){
mode=next;$('tc-flight').hidden=mode!=='flight';$('tc-sub').hidden=mode!=='sub';
if(mode==='train')result('Use the real railway geography importer for routes.');else showSamples();
redrawMarkers();annotate();
}
$('tc-flight-survey').addEventListener('click',async()=>{
if(!state||mode!=='flight')return;const snapshot={...state},id=++generation,button=$('tc-flight-survey');button.disabled=true;const samples=[],failures=[];
result('Requesting three USGS elevation points. Data requests are sequential; the exercise does not track terrain continuously.');
try{
for(const km of [0,2,5]){
if(id!==generation)break;
const p=T.ahead(snapshot,km,M);
try{samples.push({...T.usgsParse(await query(T.usgsUrl(p.lat,p.lon))),...p,km});}
catch(error){failures.push(km+' km: '+error.message);}
}
if(id!==generation)return;
flight=samples;showSamples();
if(failures.length)result($('tc-results').textContent+' Unavailable: '+failures.join('; ')+'.');
redrawMarkers();annotate();
}finally{button.disabled=false;}
});
$('tc-sub-survey').addEventListener('click',async()=>{
if(!state||mode!=='sub')return;const snapshot={...state},id=++generation,button=$('tc-sub-survey');button.disabled=true;
result('Requesting one NOAA global relief grid cell.');
try{const v=T.etopoParse(await query(T.etopoUrl(snapshot.lat,snapshot.lon)));if(id!==generation)return;seabed={...v,lat:snapshot.lat,lon:snapshot.lon};showSamples();redrawMarkers();annotate();}
catch(error){if(id===generation){seabed=null;result('Seafloor query unavailable: '+error.message);annotate();}}
finally{button.disabled=false;}
});
$('tc-clear').addEventListener('click',()=>{generation++;flight=[];seabed=null;result('Locally held samples cleared.');redrawMarkers();annotate();});
root.addEventListener('leh-transit-state',event=>{if(!event.detail?.state)return;state=event.detail.state;if(mode!==event.detail.mode)setMode(event.detail.mode);else annotate();});
root.addEventListener('leh-transit-map-ready',event=>{map=event.detail?.map||null;redrawMarkers();});
setMode(root.querySelector('[data-mode][aria-pressed="true"]')?.dataset.mode||'flight');
})();
