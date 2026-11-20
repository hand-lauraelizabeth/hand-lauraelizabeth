/* User-triggered NY Open Data MTA subway route geometry reference. */
const TransitMTA=(()=>{
'use strict';
const URL='https://data.ny.gov/resource/s692-irgq.geojson?$limit=100';
const STATIONS_URL='https://data.ny.gov/resource/39hk-dx4f.json?$select=gtfs_stop_id,stop_name,daytime_routes,gtfs_latitude,gtfs_longitude,structure&$limit=1000';
function convert(feature,A){
const g=feature?.geometry,props=feature?.properties||{};
if(!g||!['LineString','MultiLineString'].includes(g.type))throw Error('Missing railway line geometry.');
const segments=g.type==='LineString'?[g.coordinates]:g.coordinates;
const valid=[];
for(const segment of segments){
 if(!Array.isArray(segment)||segment.length<2)continue;
 const stride=Math.max(1,Math.ceil(segment.length/15000)),selected=segment.filter((_,i)=>i%stride===0||i===segment.length-1);
 try{
 const points=selected.map(p=>({lat:Number(p[1]),lon:Number(p[0])}));
 const name=String(props.service||'?')+' · '+String(props.service_name||'MTA service line');
 valid.push(A.validateRoute(name,points));
 }catch(error){continue;}
}
if(!valid.length)throw Error('No usable continuous route segments.');
valid.sort((a,b)=>b.lengthM-a.lengthM);
return {...valid[0],service:String(props.service||'?'),serviceName:String(props.service_name||'MTA service line'),segmentCount:valid.length,isRepresentative:valid.length>1};
}
function normalize(raw,A){
if(raw?.type!=='FeatureCollection'||!Array.isArray(raw.features))throw Error('Expected GeoJSON FeatureCollection from NY Open Data.');
if(raw.features.length>100)throw Error('Unexpectedly large route listing.');
const lines=[];for(const f of raw.features){try{lines.push(convert(f,A));}catch(error){}}
if(!lines.length)throw Error('No usable service line shapes.');
return lines.sort((a,b)=>a.service.localeCompare(b.service,undefined,{numeric:true})||b.lengthM-a.lengthM);
}
return {URL,STATIONS_URL,convert,normalize};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitMTA;
(function mtaRouteBrowser(){
'use strict';
if(typeof document==='undefined'||typeof TransitDataAdapters==='undefined')return;
const root=document.getElementById('leh-transit');if(!root||root.dataset.mtaRoutes==='ready')return;root.dataset.mtaRoutes='ready';
const $=id=>document.getElementById(id),A=TransitDataAdapters,N=TransitMTA,R=TransitRailGeometry;
const panel=document.createElement('section');panel.className='panel mta-routes';
panel.innerHTML='<div class="top"><div><p class="eyebrow">Real geographic service lines</p><h2>New York subway route explorer</h2></div><span class="pill">NY Open Data</span></div>'+
'<p>Load published MTA subway and Staten Island Railway service-line geometries and nearby official station centroids. The modeled train now uses the selected segment’s measured geographic length; matched station positions become selectable classroom stop objectives. This is <strong>not live train tracking</strong>, a published operating schedule, actual rail odometry, signaling, or a verified track alignment.</p>'+
'<div class="actions"><button id="mta-load" type="button">Load route shapes and stations</button><button id="mta-clear" type="button" class="secondary">Return to generic 10 km track</button><a href="https://data.ny.gov/d/s692-irgq" target="_blank" rel="noopener">MTA Subway Service Lines dataset</a></div>'+
'<label for="mta-select" id="mta-wrap" hidden>Choose a published service line<select id="mta-select"></select></label>'+
'<p id="mta-status" class="mta-message" role="status">No MTA data requested. The generic railway and local GTFS/GeoJSON imports remain available.</p><details id="mta-stations" hidden><summary id="mta-station-summary">Matched station locations</summary><ol id="mta-station-list"></ol></details><p id="mta-next" class="mta-message" role="status" hidden></p>'+
'<p class="mta-foot">Source: State of New York open data, MTA Subway Service Lines (dataset revised December 8, 2025). The longest continuous segment of a branching service is used. Distances are computed along this published polyline; station coordinates are projected onto the nearest segment, not surveyed track chainage. Matching uses weekday daytime-service labels and a 220 m proximity cutoff; some actual stops may be missing or approximate. No line-specific speed limits, grades, signals, schedules, current service or station stopping patterns are inferred.</p>';
const css=document.createElement('style');css.textContent='#leh-transit .mta-routes{display:grid;gap:.8rem}#leh-transit .mta-routes p{line-height:1.48;font-size:.88rem}#leh-transit .mta-routes .mta-foot{font-size:.8rem;color:var(--muted)}#leh-transit .mta-routes label{font-weight:700;font-size:.9rem}#leh-transit .mta-routes select{display:block;width:100%;padding:.55rem;border:1px solid var(--border);border-radius:8px;margin:.35rem 0}#leh-transit .mta-routes [hidden]{display:none!important}#leh-transit .mta-routes .mta-message{background:#edf5ef;border-radius:8px;padding:.65rem}';
document.head.append(css);root.querySelector('.main-stack')?.append(panel);
let routes=[],stations=[],mode='flight',active=null,stationError='';
function listStations(route){
 const host=$('mta-station-list');host.replaceChildren();
 $('mta-stations').hidden=!route.stations?.length;
 if(!route.stations?.length){$('mta-station-summary').textContent='No matching station centroids';return;}
 $('mta-station-summary').textContent=route.stations.length+' matched published station centroids (select to inspect)';
 for(const station of route.stations){
  const li=document.createElement('li');
  li.textContent=station.name+' · '+(station.distanceM/1000).toFixed(2)+' km from mapped start · nearest-line offset '+Math.round(station.offsetM)+' m';
  host.append(li);
 }
}
function activeStationStatus(s){
 if(!active||!Number.isFinite(s?.pos))return;
 const next=active.stations?.find(t=>t.distanceM>s.pos+0.1);
 $('mta-next').hidden=false;
 $('mta-next').textContent=next?'Next mapped station: '+next.name+' · '+Math.max(0,Math.round(next.distanceM-s.pos))+' m modeled distance remaining. Geographic station data are not operating instructions.':'No further matched station on this segment. '+Math.max(0,Math.round(active.lengthM-s.pos))+' m to mapped segment end.';
}
function select(){
 const index=Number($('mta-select').value),raw=routes[index];if(!raw)return;
 const route=stations.length?R.attach(raw,stations):{...raw,stations:[],stationSource:'Station feed unavailable'};
 active=route;listStations(route);
 root.dispatchEvent(new CustomEvent('leh-transit-route-selected',{detail:{route}}));
 $('mta-status').textContent='Selected '+route.service+' · '+route.serviceName+' · measured line geometry '+(route.lengthM/1000).toFixed(2)+' km · '+(route.stations?.length||0)+' proximity-matched published stations'+(route.isRepresentative?' · longest of '+route.segmentCount+' geometric segments':'')+'. The train exercise uses geographic route length rather than 10 km. '+(stationError?'Station data unavailable: '+stationError+'. ':'')+'Signal aspects, track grades and operating limits are still unknown.';
 activeStationStatus(root.transitLatest?.mode==='train'?root.transitLatest.state:null);
}
$('mta-select').addEventListener('change',select);
$('mta-clear').addEventListener('click',()=>{
 active=null;$('mta-stations').hidden=true;$('mta-next').hidden=true;
 root.dispatchEvent(new CustomEvent('leh-transit-route-cleared'));
 $('mta-status').textContent='Mapped route cleared. Generic 10 km train exercise restored.';
});
$('mta-load').addEventListener('click',async()=>{
 const b=$('mta-load'),controller=new AbortController(),timer=setTimeout(()=>controller.abort(),19000);
 b.disabled=true;$('mta-status').textContent='Requesting published MTA line geometry and station centroids…';
 async function fetchJson(url,maxBytes){
  const response=await fetch(url,{signal:controller.signal,headers:{Accept:'application/json'}});
  if(!response.ok)throw Error('NY Open Data returned HTTP '+response.status);
  const raw=await response.text();if(raw.length>maxBytes)throw Error('Dataset exceeds the browser download limit.');
  return JSON.parse(raw);
 }
 try{
  const [lineResult,stationResult]=await Promise.allSettled([
   fetchJson(N.URL,9000000),fetchJson(N.STATIONS_URL,1700000)
  ]);
  if(lineResult.status!=='fulfilled')throw lineResult.reason;
  routes=N.normalize(lineResult.value,A);
  stations=[];stationError='';
  if(stationResult.status==='fulfilled'){
   try{stations=R.stationRows(stationResult.value);}catch(error){stationError=error.message;}
  }else stationError=stationResult.reason?.message||'unavailable';
  const select=$('mta-select');select.replaceChildren();
  routes.forEach((r,i)=>{const option=document.createElement('option');option.value=String(i);option.textContent=r.service+' · '+r.serviceName+' ('+(r.lengthM/1000).toFixed(1)+' km mapped)';select.append(option);});
  $('mta-wrap').hidden=false;select();
 }catch(error){$('mta-status').textContent='Published service lines unavailable: '+error.message+'. You can still import a local GTFS shape or GeoJSON file. The generic simulator remains available.';}
 finally{clearTimeout(timer);b.disabled=false;}
});
root.addEventListener('leh-transit-state',event=>{if(event.detail?.mode==='train'&&active)activeStationStatus(event.detail.state);});

function visibility(next){mode=next;panel.hidden=mode!=='train';}
root.addEventListener('leh-transit-state',e=>{if(e.detail?.mode&&e.detail.mode!==mode)visibility(e.detail.mode);});
visibility(root.querySelector('[data-mode][aria-pressed="true"]')?.dataset.mode||'flight');
})();
