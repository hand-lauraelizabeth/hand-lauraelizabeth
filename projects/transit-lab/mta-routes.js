/* User-triggered NY Open Data MTA subway route geometry reference. */
const TransitMTA=(()=>{
'use strict';
const URL='https://data.ny.gov/resource/s692-irgq.geojson?$limit=100';
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
return {URL,convert,normalize};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitMTA;
(function mtaRouteBrowser(){
'use strict';
if(typeof document==='undefined'||typeof TransitDataAdapters==='undefined')return;
const root=document.getElementById('leh-transit');if(!root||root.dataset.mtaRoutes==='ready')return;root.dataset.mtaRoutes='ready';
const $=id=>document.getElementById(id),A=TransitDataAdapters,N=TransitMTA;
const panel=document.createElement('section');panel.className='panel mta-routes';
panel.innerHTML='<div class="top"><div><p class="eyebrow">Real geographic service lines</p><h2>New York subway route explorer</h2></div><span class="pill">NY Open Data</span></div>'+
'<p>Load published MTA subway and Staten Island Railway service-line geometries. Select a line to place a simulated train marker along its published path. This is <strong>not live train tracking</strong>, train scheduling, station-by-station operation or a verified detailed track alignment.</p>'+
'<div class="actions"><button id="mta-load" type="button">Load official route shapes</button><a href="https://data.ny.gov/d/s692-irgq" target="_blank" rel="noopener">MTA Subway Service Lines dataset</a></div>'+
'<label for="mta-select" id="mta-wrap" hidden>Choose a published service line<select id="mta-select"></select></label>'+
'<p id="mta-status" class="mta-message" role="status">No MTA data requested. The built-in generic route and local GTFS/GeoJSON imports remain available.</p>'+
'<p class="mta-foot">Source: State of New York open data, MTA Subway Service Lines (dataset revised December 8, 2025). The longest continuous segment of a branching line is used as one example. Simulated 10 km progress is projected over its published geographic length. Signals, station stops, train frequency, travel time, grades and current service are not provided by this dataset.</p>';
const css=document.createElement('style');css.textContent='#leh-transit .mta-routes{display:grid;gap:.8rem}#leh-transit .mta-routes p{line-height:1.48;font-size:.88rem}#leh-transit .mta-routes .mta-foot{font-size:.8rem;color:var(--muted)}#leh-transit .mta-routes label{font-weight:700;font-size:.9rem}#leh-transit .mta-routes select{display:block;width:100%;padding:.55rem;border:1px solid var(--border);border-radius:8px;margin:.35rem 0}#leh-transit .mta-routes [hidden]{display:none!important}#leh-transit .mta-routes .mta-message{background:#edf5ef;border-radius:8px;padding:.65rem}';
document.head.append(css);root.querySelector('.main-stack')?.append(panel);
let routes=[],mode='flight';
function select(){
const s=$('mta-select'),route=routes[Number(s.value)];if(!route)return;
root.dispatchEvent(new CustomEvent('leh-transit-route-selected',{detail:{route}}));
$('mta-status').textContent='Selected '+route.service+' · '+route.serviceName+' · mapped segment '+(route.lengthM/1000).toFixed(2)+' km · '+route.count+' points'+(route.isRepresentative?' · selected longest of '+route.segmentCount+' geometric segments':'')+'. A 10 km simulated run will be stretched along this geography, not the real train distance or timetable. Select Load real map to view the route.';
}
$('mta-select').addEventListener('change',select);
$('mta-load').addEventListener('click',async()=>{
const b=$('mta-load'),controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),18000);
b.disabled=true;$('mta-status').textContent='Requesting published MTA service-line geometry from NY Open Data…';
try{
const response=await fetch(N.URL,{signal:controller.signal,headers:{Accept:'application/geo+json'}});
if(!response.ok)throw Error('NY Open Data returned HTTP '+response.status);
const text=await response.text();if(text.length>9000000)throw Error('Download exceeds 9 MB browser limit.');
routes=N.normalize(JSON.parse(text),A);
const s=$('mta-select');s.replaceChildren();
routes.forEach((r,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=r.service+' · '+r.serviceName+' ('+(r.lengthM/1000).toFixed(1)+' km segment)';s.append(o);});
$('mta-wrap').hidden=false;select();
}catch(error){$('mta-status').textContent='Published shapes unavailable: '+error.message+'. Local GTFS shapes.txt or GeoJSON import is still supported. This request does not affect the core simulator.';}
finally{clearTimeout(timeout);b.disabled=false;}
});
function visibility(next){mode=next;panel.hidden=mode!=='train';}
root.addEventListener('leh-transit-state',e=>{if(e.detail?.mode&&e.detail.mode!==mode)visibility(e.detail.mode);});
visibility(root.querySelector('[data-mode][aria-pressed="true"]')?.dataset.mode||'flight');
})();
