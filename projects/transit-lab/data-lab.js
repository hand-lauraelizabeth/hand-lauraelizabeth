(function dataLab(){
'use strict';
if(typeof document==='undefined'||typeof TransitModels==='undefined'||typeof TransitDataAdapters==='undefined')return;
const root=document.getElementById('leh-transit');if(!root||root.dataset.integrationLab==='ready')return;
root.dataset.integrationLab='ready';
const A=TransitDataAdapters,M=TransitModels,$=id=>document.getElementById(id);
const css=document.createElement('style');
css.textContent=`
#leh-transit .di-lab{display:grid;gap:.8rem}#leh-transit .di-lab h3{margin:.25rem 0 .35rem;color:var(--ink);font-size:1.14rem;font-family:Georgia,serif}
#leh-transit .di-lab p{font-size:.9rem;line-height:1.53}#leh-transit .di-lab .di-stage{border:1px solid var(--border);border-radius:12px;background:#f2f8f4;padding:.85rem;display:grid;gap:.6rem}
#leh-transit .di-lab .di-stage[hidden]{display:none!important}#leh-transit .di-lab .di-note{font-size:.8rem;color:var(--muted)}
#leh-transit .di-lab .di-quality{background:#fff;border-left:4px solid #3e8f78;border-radius:7px;padding:.7rem;font-size:.88rem;line-height:1.5}
#leh-transit .di-lab label{font-weight:700}#leh-transit .di-lab select,#leh-transit .di-lab input[type=file]{display:block;width:100%;font:inherit;min-width:0;margin-top:.32rem;padding:.5rem;border-radius:8px;border:1px solid #9fb9ad;background:#fff}
#leh-transit .di-lab .di-map{width:100%;height:auto;display:block;border:1px solid #bdd6ce;border-radius:10px;background:#eaf1ed}
#leh-transit .di-lab .di-map-image{display:block;width:100%;border-radius:10px;border:1px solid #b8c9bf;background:#e9f4ed}
#leh-transit .di-lab .di-badge{display:inline-block;background:#e4ebe9;color:#325549;font-size:.78rem;font-weight:800;border-radius:6px;padding:.2rem .5rem}
#leh-transit .di-lab a{overflow-wrap:anywhere}
`;
document.head.append(css);
const panel=document.createElement('section');
panel.className='panel di-lab';panel.setAttribute('aria-labelledby','di-title');
panel.innerHTML=`
<div class="top"><div><p class="eyebrow">Observed ≠ modeled</p><h2 id="di-title">Data Integration Lab</h2></div><span class="di-badge" id="di-kind">Flight data</span></div>
<p>Import a reference dataset or load a sourced map, then compare it with the teaching model. Source files stay on your device. No credentials, API secrets, or imported positions are silently transmitted.</p>
<div id="di-flight" class="di-stage" data-di-mode="flight">
<h3>Aircraft · OpenSky-format state vectors</h3>
<p>Load a <code>.json</code> export containing an OpenSky <code>time</code> and <code>states</code> array, or multiple timestamped snapshots. Choose an aircraft to inspect. This is a local file import, <strong>not a live OpenSky connection</strong>.</p>
<label for="di-open-file">OpenSky-format JSON<input id="di-open-file" type="file" accept=".json,application/json"></label>
<label for="di-aircraft-select" id="di-aircraft-wrap" hidden>Aircraft in file<select id="di-aircraft-select"></select></label>
<div id="di-flight-stats" role="status" class="di-quality">No aircraft data loaded.</div>
<div class="actions"><button id="di-aircraft-use" type="button" disabled>Inspect in flight track</button><button id="di-aircraft-export" type="button" class="secondary" disabled>Download normalized CSV</button></div>
<p class="di-note">Reported ground velocity is <em>not</em> true airspeed. Geometric and barometric altitudes are not interchangeable. File origin and authenticity cannot be verified here. <a href="https://openskynetwork.github.io/opensky-api/rest.html" target="_blank" rel="noopener">OpenSky API field definitions</a>.</p>
</div>
<div id="di-rail" class="di-stage" data-di-mode="train" hidden>
<h3>Railway · GTFS shape geometry</h3>
<p>Import <code>shapes.txt</code> from a GTFS Schedule feed, or a GeoJSON LineString. Actual geographic geometry is shown as a <strong>reference</strong>; the locomotive still follows the generic 10 km teaching track.</p>
<label for="di-shapes-file">GTFS shapes.txt or route GeoJSON<input id="di-shapes-file" type="file" accept=".txt,.csv,.geojson,.json,text/plain,application/json"></label>
<label for="di-route-select" id="di-route-wrap" hidden>Imported route<select id="di-route-select"></select></label>
<svg id="di-route-map" viewBox="0 0 640 240" role="img" aria-label="Imported geographic route outline, not the simulated train position" class="di-map"><text x="25" y="120" fill="#345c4c" font-size="17">No route geometry imported.</text></svg>
<div id="di-route-stats" class="di-quality" role="status">Route geometry, stops and signals are not loaded.</div>
<p class="di-note">Shape lines do not supply signal aspects, vehicle dynamics, gradients, or live locations. GTFS Realtime VehiclePositions are Protocol Buffers and are <strong>not</strong> directly supported by this file input. <a href="https://gtfs.org/documentation/schedule/reference/#shapestxt" target="_blank" rel="noopener">GTFS shapes</a> · <a href="https://gtfs.org/documentation/realtime/reference/" target="_blank" rel="noopener">GTFS Realtime</a>.</p>
</div>
<div id="di-sub" class="di-stage" data-di-mode="sub" hidden>
<h3>Submarine · GEBCO 2026 bathymetry context</h3>
<p>GEBCO publishes global bathymetric imagery, with variable measurement coverage. Request regional context when you choose. The submarine model does <strong>not</strong> read seabed depth from the image or calculate collisions.</p>
<div class="actions"><button id="di-bathy-load" type="button">Load GEBCO regional relief</button><button id="di-bathy-reload" type="button" class="secondary" hidden>Recenter on simulated position</button></div>
<img id="di-bathy-img" class="di-map-image" alt="GEBCO regional bathymetry. Neither submarine position nor seabed clearance is measured from this image." hidden>
<div id="di-bathy-status" role="status" class="di-quality">Not loaded. No external request made.</div>
<p class="di-note">Imagery from the GEBCO_2026 Grid, GEBCO Compilation Group (2026), hosted by BODC. Not for safety at sea. Loading sends an image request to GEBCO. <a href="https://www.gebco.net/data-products/gebco-web-services/web-map-service" target="_blank" rel="noopener">Source, attribution and disclaimer</a>.</p>
</div>
<details class="tv-detail"><summary>What's next for live data?</summary><p><strong>Flight:</strong> restricted, licensed server-side Flightradar24 or OpenSky adapter, with caching, quotas and timestamps. <strong>Rail:</strong> authorized GTFS-RT feed decoding and static-route alignment. <strong>3D:</strong> Google Map Tiles API access, billing, a supported renderer and attribution. None is activated or implied to be free here.</p></details>`;
root.querySelector('.main-stack')?.append(panel);
let flight=null,routes=[],mode='flight',subPosition=M.subInit();
const stages={flight:$('di-flight'),train:$('di-rail'),sub:$('di-sub')};
function setMode(k){
 if(!stages[k])return;mode=k;
 for(const [name,el] of Object.entries(stages))el.hidden=name!==k;
 $('di-kind').textContent={flight:'Flight data',train:'Route geometry',sub:'Bathymetry'}[k];
}
function selectedAircraft(){return flight?.aircraft.find(a=>a.icao24===$('di-aircraft-select').value);}
function describeAircraft(){
 const a=selectedAircraft();if(!a)return;
 const p=a.points.at(-1),age=Date.now()-p.t;
 $('di-flight-stats').textContent=a.callsign+' · '+a.icao24+' · '+a.samples+' position'+(a.samples===1?'':'s')+' · '+p.time_iso+' ('+(age>=0?Math.round(age/60000)+' min old':'future timestamp')+') · '+(p.speed===null?'ground velocity not reported':'ground velocity '+p.speed.toFixed(1)+' m/s')+' · '+p.altKind+'. '+(a.samples===1?'One position is not a flight path.':'Replay uses recorded timestamps.');
}
$('di-open-file').addEventListener('change',async e=>{
 try{
  const file=e.target.files?.[0];if(!file)throw Error('Select a file.');if(file.size>3e6)throw Error('3 MB maximum.');
  flight=A.parseOpenSky(await file.text());
  const select=$('di-aircraft-select');select.replaceChildren();
  for(const a of flight.aircraft.slice(0,100)){const option=document.createElement('option');option.value=a.icao24;option.textContent=a.callsign+' ('+a.icao24+') · '+a.samples+' points';select.append(option);}
  $('di-aircraft-wrap').hidden=false;$('di-aircraft-use').disabled=false;$('di-aircraft-export').disabled=false;describeAircraft();
 }catch(error){flight=null;$('di-aircraft-use').disabled=true;$('di-aircraft-export').disabled=true;$('di-aircraft-wrap').hidden=true;$('di-flight-stats').textContent='Invalid OpenSky-format file: '+error.message;}
});
$('di-aircraft-select').addEventListener('change',describeAircraft);
$('di-aircraft-export').addEventListener('click',()=>{const a=selectedAircraft();if(!a)return;const csv=A.toFlightCSV(a.points),url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download='opensky-normalized-'+a.icao24+'.csv';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);$('di-flight-stats').textContent='Downloaded normalized local CSV for '+a.callsign+'. If automatic handoff is unavailable, load it through the existing flight-track CSV input.';});
$('di-aircraft-use').addEventListener('click',()=>{
 const a=selectedAircraft();if(!a)return;
 try{
 if(root.dataset.dataLabNativeImport==='ready')root.dispatchEvent(new CustomEvent('leh-transit-import',{detail:{points:a.points,source:'OpenSky-format local file (unverified)'}}));
 else{
  const input=$('tl-csv');if(!input||typeof DataTransfer==='undefined'||typeof File==='undefined')throw Error('This browser cannot attach a generated file. Use Download normalized CSV and import it in the existing flight-track input.');
  const normalized=A.toFlightCSV(a.points),file=new File([normalized],'opensky-normalized-local.csv',{type:'text/csv'}),transfer=new DataTransfer();
  transfer.items.add(file);input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));
 }
 $('di-flight-stats').textContent='Sent '+a.samples+' local point'+(a.samples===1?'':'s')+' to the flight-track viewer. '+(a.samples===1?'A single observed position is not a flight path.':'Use the existing scrub/replay controls for timestamped observations.');
 }catch(error){$('di-flight-stats').textContent='Could not import directly: '+error.message;}

});
function renderRoute(){
 const route=routes.find((x,i)=>String(i)===$('di-route-select').value)||routes[0];if(!route)return;
 const pts=A.projection(route.points).map(p=>p.x.toFixed(2)+','+p.y.toFixed(2)).join(' ');
 const svg=$('di-route-map');svg.replaceChildren();
 function el(name,attrs,txt){const e=document.createElementNS('http://www.w3.org/2000/svg',name);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(txt)e.textContent=txt;svg.append(e);}
 el('rect',{width:640,height:240,fill:'#e8f0eb'});
 for(let x=0;x<=640;x+=40)el('path',{d:'M'+x+' 0V240',stroke:'#c4d8cf'});
 for(let y=0;y<=240;y+=40)el('path',{d:'M0 '+y+'H640',stroke:'#c4d8cf'});
 el('polyline',{points:pts,fill:'none',stroke:'#226c50','stroke-width':5,'stroke-linejoin':'round','stroke-linecap':'round'});
 const arr=A.projection(route.points);
 for(const [p,label,color] of [[arr[0],'START','#276b56'],[arr.at(-1),'END','#b46c3d']]){
  el('circle',{cx:p.x,cy:p.y,r:7,fill:color,stroke:'#fff','stroke-width':2});
  el('text',{x:Math.max(12,Math.min(560,p.x+10)),y:Math.max(20,Math.min(225,p.y-10)),fill:'#173e34','font-size':15,'font-weight':700},label);
 }
 svg.setAttribute('aria-label',route.name+' route outline with '+route.count+' points, '+(route.lengthM/1000).toFixed(2)+' km.');
 $('di-route-stats').textContent=route.name+' · '+route.count+' geographic points · approximately '+(route.lengthM/1000).toFixed(2)+' km · start '+route.points[0].lat.toFixed(4)+'°, '+route.points[0].lon.toFixed(4)+'°. The train simulation is still a separate generic 10 km route.';
}
$('di-shapes-file').addEventListener('change',async e=>{
 try{
  const file=e.target.files?.[0];if(!file)throw Error('Choose a file.');if(file.size>6e6)throw Error('6 MB maximum.');
  const raw=await file.text();routes=/\.(geojson|json)$/i.test(file.name)?A.parseGeoJSON(raw):A.parseGTFSShapes(raw);
  const select=$('di-route-select');select.replaceChildren();
  for(let i=0;i<routes.length;i++){const option=document.createElement('option');option.value=String(i);option.textContent=routes[i].name+' · '+(routes[i].lengthM/1000).toFixed(2)+' km';select.append(option);}
  $('di-route-wrap').hidden=false;renderRoute();
 }catch(error){routes=[];$('di-route-wrap').hidden=true;$('di-route-stats').textContent='Route import failed: '+error.message;}
});
$('di-route-select').addEventListener('change',renderRoute);
function loadBathy(){
 const {lat,lon}=subPosition,lat0=Math.max(-89,lat-2),lat1=Math.min(89,lat+2),lon0=Math.max(-179,lon-3),lon1=Math.min(179,lon+3);
 const args=new URLSearchParams({SERVICE:'WMS',VERSION:'1.3.0',REQUEST:'GetMap',LAYERS:'gebco_latest_sub_ice_topo',STYLES:'',FORMAT:'image/jpeg',WIDTH:'1000',HEIGHT:'650',CRS:'EPSG:4326',BBOX:[lat0,lon0,lat1,lon1].join(',')});
 const img=$('di-bathy-img');img.hidden=true;
 $('di-bathy-status').textContent='Requesting GEBCO relief near '+lat.toFixed(3)+'°, '+lon.toFixed(3)+'°. Not a depth measurement.';
 img.onload=()=>{img.hidden=false;$('di-bathy-reload').hidden=false;$('di-bathy-status').textContent='GEBCO_2026 regional relief loaded. Bathymetry is geographic context only; no model collision or clearance calculation.';};
 img.onerror=()=>{$('di-bathy-status').textContent='GEBCO image unavailable (network, provider, or browser restriction); source link remains available.';};
 img.src='https://wms.gebco.net/mapserv?'+args.toString();
}
$('di-bathy-load').addEventListener('click',loadBathy);
$('di-bathy-reload').addEventListener('click',loadBathy);
root.addEventListener('leh-transit-state',e=>{const d=e.detail;if(!d)return;if(d.mode==='sub'&&d.state)subPosition={lat:d.state.lat,lon:d.state.lon};if(d.mode!==mode)setMode(d.mode);});
root.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>setMode(button.dataset.mode)));
setMode(root.querySelector('[data-mode][aria-pressed="true"]')?.dataset.mode||'flight');
})();
