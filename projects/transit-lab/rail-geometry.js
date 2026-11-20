/* Published MTA station coordinates projected onto published service-line geometry.
   Geometry-derived chainage is not track odometry or a certified alignment. */
const TransitRailGeometry=(()=>{
'use strict';
const RAD=Math.PI/180,EARTH=6371008.8;
function distance(a,b){
 const p=a.lat*RAD,q=b.lat*RAD,dp=(b.lat-a.lat)*RAD,dl=((b.lon-a.lon+540)%360-180)*RAD;
 const w=Math.sin(dp/2)**2+Math.cos(p)*Math.cos(q)*Math.sin(dl/2)**2;
 return 2*EARTH*Math.asin(Math.min(1,Math.sqrt(w)));
}
function project(point,route){
 if(!route||!Array.isArray(route.points)||route.points.length<2)throw Error('Route needs a nonempty polyline.');
 if(!Number.isFinite(point.lat)||!Number.isFinite(point.lon))throw Error('Station coordinate invalid.');
 let best=null,chainage=0;
 for(let i=1;i<route.points.length;i++){
  const a=route.points[i-1],b=route.points[i],segment=distance(a,b);
  if(segment<.01)continue;
  const scale=Math.cos(((a.lat+b.lat)/2)*RAD);
  const delta=(longitude)=>((longitude-a.lon+540)%360)-180;
  const ex=delta(b.lon)*RAD*EARTH*scale,ny=(b.lat-a.lat)*RAD*EARTH;
  const px=delta(point.lon)*RAD*EARTH*scale,py=(point.lat-a.lat)*RAD*EARTH;
  const fraction=Math.max(0,Math.min(1,(px*ex+py*ny)/Math.max(1e-8,ex*ex+ny*ny)));
  const offset=Math.hypot(px-fraction*ex,py-fraction*ny);
  if(!best||offset<best.offsetM)best={distanceM:chainage+segment*fraction,offsetM:offset,segmentIndex:i-1,segmentFraction:fraction};
  chainage+=segment;
 }
 if(!best)throw Error('Route has no measurable segments.');
 return best;
}
function stationRows(rows){
 if(!Array.isArray(rows)||rows.length>1500)throw Error('Expected bounded MTA station JSON rows.');
 return rows.flatMap(row=>{
  const lat=Number(row?.gtfs_latitude),lon=Number(row?.gtfs_longitude);
  if(!row||row.gtfs_latitude==null||row.gtfs_longitude==null||!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180||!row.stop_name)return [];
  return [{id:String(row.gtfs_stop_id||row.stop_name).slice(0,30),name:String(row.stop_name).slice(0,85),lat,lon,daytimeRoutes:String(row.daytime_routes||'').toUpperCase(),structure:String(row.structure||'').slice(0,45)}];
 });
}
function matchesService(station,service){
 const s=String(service||'').trim().toUpperCase();
 if(!s||s==='?')return false;
 const tokens=station.daytimeRoutes.toUpperCase().split(/[\s,;/|]+/).filter(Boolean);
 const aliases=s==='SI'?['SI','SIR']:s==='SIR'?['SIR','SI']:s==='H'?['H','S']: [s];
 return aliases.some(alias=>tokens.includes(alias));
}
function attach(route,rows,{maxOffsetM=220}={}){
 if(!route||!Number.isFinite(route.lengthM)||route.lengthM<=0)throw Error('Route length must be measured.');
 const entries=[],service=route.service;
 for(const s of rows){
  if(!matchesService(s,service))continue;
  const p=project(s,route);
  if(p.offsetM>maxOffsetM||p.distanceM>route.lengthM+100)continue;
  entries.push({...s,...p,distanceM:Math.max(0,Math.min(route.lengthM,p.distanceM))});
 }
 entries.sort((a,b)=>a.distanceM-b.distanceM||a.offsetM-b.offsetM);
 const dedup=[];
 for(const s of entries){
  const prior=dedup.at(-1);
  if(prior&&Math.abs(s.distanceM-prior.distanceM)<35&&prior.name.toLowerCase()===s.name.toLowerCase()){
   if(s.offsetM<prior.offsetM)dedup[dedup.length-1]=s;
   continue;
  }
  dedup.push(s);
 }
 return {...route,stations:dedup,stationSource:'MTA Subway Stations (GTFS centroids), matched to nearest service-line geometry within '+maxOffsetM+' m',geometryLengthM:route.lengthM};
}
function checkpoints(route){
 if(!route?.stations?.length)return [route.lengthM];
 const ordered=route.stations.filter(s=>Number.isFinite(s.distanceM)&&s.distanceM>=0&&s.distanceM<=route.lengthM)
  .sort((a,b)=>a.distanceM-b.distanceM);
 const positions=ordered.map(s=>s.distanceM);
 positions.push(route.lengthM);
 return [...new Set(positions.map(x=>Math.round(x*10)/10))];
}
return {distance,project,stationRows,matchesService,attach,checkpoints};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitRailGeometry;
