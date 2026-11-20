/* USGS/NASA basemaps and measured GTFS/GeoJSON route geography.
   Layers load only after the user's explicit Load real map action. */
const TransitGeography=(()=>{
'use strict';
function routeAtFraction(route,fraction,dist){
 if(!route?.points?.length)return null;
 const points=route.points,between=dist||((a,b)=>{const R=6371008.8,toRad=Math.PI/180,dp=(b.lat-a.lat)*toRad,dl=(b.lon-a.lon)*toRad,q=Math.sin(dp/2)**2+Math.cos(a.lat*toRad)*Math.cos(b.lat*toRad)*Math.sin(dl/2)**2;return R*2*Math.asin(Math.min(1,Math.sqrt(q)));});
 const total=Number(route.lengthM)||points.slice(1).reduce((v,p,i)=>v+between(points[i],p),0);
 let target=Math.max(0,Math.min(1,Number(fraction)||0))*total;
 for(let i=1;i<points.length;i++){
  const a=points[i-1],b=points[i],segment=between(a,b);
  if(target>segment){target-=segment;continue;}
  const part=segment>0?target/segment:0;
  const delta=((b.lon-a.lon+540)%360)-180;
  return {lat:a.lat+(b.lat-a.lat)*part,lon:((a.lon+delta*part+540)%360)-180};
 }
 return {...points.at(-1)};
}
return {routeAtFraction};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitGeography;
(function geographicRealism(){
'use strict';
if(typeof document==='undefined')return;
const root=document.getElementById('leh-transit');
if(!root||root.dataset.geoRealism==='ready')return;root.dataset.geoRealism='ready';
const $=id=>document.getElementById(id),G=TransitGeography;
const host=$('tl-map-card'),controls=document.createElement('div');controls.className='geo-source-controls';
controls.innerHTML='<label for="geo-basemap">Geographic imagery<select id="geo-basemap"><option value="street">OpenStreetMap streets · global</option><option value="aerial">USGS aerial orthophotos · United States</option><option value="topo">USGS topographic map · United States</option><option value="nasa">NASA Blue Marble · global, August 2004</option></select></label><p id="geo-source-caption" role="status" class="small">Maps load only when you select “Load real map.” Source imagery is an external geographic reference, not a camera view from the simulated vehicle.</p><p class="small"><a href="https://www.usgs.gov/faqs/what-are-terms-uselicensing-map-services-and-data-national-map" target="_blank" rel="noopener">USGS public-domain map service</a> · <a href="https://nasa-gibs.github.io/gibs-api-docs/" target="_blank" rel="noopener">NASA GIBS</a>. Available detail and acquisition dates vary by layer and region.</p>';
host.insertBefore(controls,$('tl-geography'));
const css=document.createElement('style');css.textContent='#leh-transit .geo-source-controls{margin:.6rem 0;padding:.8rem;background:#f1f6f1;border:1px solid var(--border);border-radius:9px}#leh-transit .geo-source-controls label{font-size:.84rem}#leh-transit .geo-source-controls select{display:block;width:100%;margin:.35rem 0}#leh-transit .geo-source-controls p{margin:.45rem 0}';
document.head.append(css);
const configs={
 street:{url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',opt:{maxZoom:18,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>'},note:'OpenStreetMap road and place mapping. Source is geographic mapping, not satellite imagery.'},
 aerial:{url:'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}',opt:{maxNativeZoom:16,maxZoom:18,attribution:'USGS The National Map, USDA NAIP and contributing imagery providers'},note:'USGS aerial orthophotography: mostly NAIP in the contiguous United States. Collection dates and pixel resolution vary; imagery is not live.'},
 topo:{url:'https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}',opt:{maxNativeZoom:16,maxZoom:18,attribution:'USGS The National Map'},note:'USGS US Topo layers: mapped terrain and human features. Terrain is contextual imagery; model does not sample actual elevation.'},
 nasa:{url:'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_NextGeneration/default/2004-08-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg',opt:{maxNativeZoom:8,maxZoom:18,attribution:'NASA Earth Observatory / NASA GIBS, Blue Marble Next Generation (2004)'},note:'NASA cloud-reduced global Blue Marble mosaic, August 2004. ~500 m imagery, so street-level enlargement will be pixelated.'}
};
let map=null,base=null,line=null,vehicle=null,stationLayer=null,selectedRoute=null,mode='flight',state=null,trackPoint=null,tileErrors=0;
function swap(layerName){
 if(!map||!window.L)return;
 const config=configs[layerName]||configs.street;
 if(base)map.removeLayer(base);else map.eachLayer(l=>{if(l instanceof window.L.TileLayer)map.removeLayer(l);});
 base=window.L.tileLayer(config.url,config.opt);
 tileErrors=0;
 base.on('tileerror',()=>{
  if(++tileErrors===4){
   $('geo-source-caption').textContent='Some tiles could not load. Check coverage or select OpenStreetMap. No private data is being uploaded.';
  }
 });
 base.addTo(map);$('geo-source-caption').textContent=config.note;
}
$('geo-basemap').addEventListener('change',()=>{if(!map){$('geo-source-caption').textContent='Selected '+$('geo-basemap').selectedOptions[0].textContent+'. Choose Load real map to request external map imagery.';return;}swap($('geo-basemap').value);});
function pointForRail(){
 if(!selectedRoute||!state||mode!=='train')return null;
 return G.routeAtFraction(selectedRoute,state.pos/Math.max(1,state.length),window.TransitDataAdapters?.distance);
}
function showRoute(fit){
 if(!map||!window.L)return;
 if(line){map.removeLayer(line);line=null;}
 if(vehicle){map.removeLayer(vehicle);vehicle=null;}
 if(stationLayer){map.removeLayer(stationLayer);stationLayer=null;}
 if(mode!=='train'||!selectedRoute)return;
 const coords=selectedRoute.points.map(p=>[p.lat,p.lon]);
 line=window.L.polyline(coords,{color:'#e0a03c',weight:4,opacity:.93}).addTo(map);
 const p=pointForRail()||selectedRoute.points[0];
 vehicle=window.L.circleMarker([p.lat,p.lon],{radius:8,color:'#103c34',fillColor:'#f9bf56',fillOpacity:1,weight:3}).addTo(map).bindPopup('Simulated train distance along published route geometry. Not measured train positioning or speed.');
 if(selectedRoute.stations?.length){
  stationLayer=window.L.layerGroup();
  for(const station of selectedRoute.stations.slice(0,120)){
   const node=window.L.circleMarker([station.lat,station.lon],{radius:4,color:'#ffffff',weight:1.3,fillColor:'#237b68',fillOpacity:.9});
   const safe=document.createElement('div');safe.textContent=station.name+' · '+(station.distanceM/1000).toFixed(2)+' km along mapped geometry · offset '+Math.round(station.offsetM)+' m';
   node.bindPopup(safe);stationLayer.addLayer(node);
  }
  stationLayer.addTo(map);
 }
 if(fit)map.fitBounds(line.getBounds(),{padding:[24,24],maxZoom:13});
}
function updateRailPoint(){
 if(mode!=='train'||!selectedRoute)return;
 const p=pointForRail()||selectedRoute.points[0];if(!p)return;
 root.dataset.routeLat=String(p.lat);root.dataset.routeLon=String(p.lon);
 $('tl-coords').textContent='Mapped model point: '+p.lat.toFixed(5)+'°, '+p.lon.toFixed(5)+'° · imported route geometry, simulated vehicle position';
 $('tl-geo-note').textContent='Route reference: '+selectedRoute.name+' ('+(selectedRoute.lengthM/1000).toFixed(2)+' km geographic length). Simulated distance now follows the mapped polyline length; matched station centroids are approximate. This is NOT recorded train GPS, operational odometry, schedule or validated track geometry.';
 if(vehicle)vehicle.setLatLng([p.lat,p.lon]);
}
root.addEventListener('leh-transit-map-ready',event=>{
 map=event.detail?.map||null;if(!map)return;
 swap($('geo-basemap').value);
 showRoute(mode==='train');updateRailPoint();
});
root.addEventListener('leh-transit-route-selected',event=>{
 const r=event.detail?.route;
 if(!r||!Array.isArray(r.points)||r.points.length<2)return;
 selectedRoute=r;
 root.dataset.routeLat=String(r.points[0].lat);root.dataset.routeLon=String(r.points[0].lon);
 if(mode==='train')host.hidden=false;
 showRoute(mode==='train');updateRailPoint();
});
root.addEventListener('leh-transit-route-cleared',()=>{
 selectedRoute=null;delete root.dataset.routeLat;delete root.dataset.routeLon;
 if(map){if(line){map.removeLayer(line);line=null;}if(vehicle){map.removeLayer(vehicle);vehicle=null;}if(stationLayer){map.removeLayer(stationLayer);stationLayer=null;}}
 if(mode==='train')host.hidden=true;
});
root.addEventListener('leh-transit-state',event=>{
 const d=event.detail;if(!d?.state)return;
 const changed=mode!==d.mode;mode=d.mode;state=d.state;
 if(mode==='train'){
  host.hidden=!selectedRoute;
  if(selectedRoute){if(changed)showRoute(true);updateRailPoint();}
 }else{
  host.hidden=false;
  if(changed)showRoute(false);
 }
});
})();
