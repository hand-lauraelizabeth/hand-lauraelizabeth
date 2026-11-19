/* Transit Data Lab format adapters. No network, accounts or credentials. */
const TransitDataAdapters=(()=>{
'use strict';
const RAD=Math.PI/180, R=6371008.8;
const finite=(n)=>typeof n==='number'&&Number.isFinite(n);
function coord(lat,lon){if(!finite(lat)||!finite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)throw Error('Coordinates must be finite WGS84 latitude/longitude.');return {lat,lon};}
function distance(a,b){const p1=a.lat*RAD,p2=b.lat*RAD,dp=(b.lat-a.lat)*RAD,dl=(b.lon-a.lon)*RAD,s=Math.sin(dp/2)**2+Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)**2;return 2*R*Math.asin(Math.min(1,Math.sqrt(s)));}
function decodeCSV(text){const data=String(text).replace(/^\uFEFF/,'');if(data.length>6e6)throw Error('Maximum file size 6 MB.');const rows=[];let current=[],field='',quoted=false;for(let i=0;i<data.length;i++){const c=data[i];if(c==='"'){if(quoted&&data[i+1]==='"'){field+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){current.push(field.trim());field='';}else if((c==='\r'||c==='\n')&&!quoted){if(c==='\r'&&data[i+1]==='\n')i++;current.push(field.trim());if(current.some(x=>x!==''))rows.push(current);current=[];field='';}else field+=c;}if(quoted)throw Error('Unclosed quoted value in CSV.');current.push(field.trim());if(current.some(x=>x!==''))rows.push(current);return rows;}
function parseOpenSky(json){
 const obj=typeof json==='string'?JSON.parse(json):json,snapshots=Array.isArray(obj)?obj:[obj];if(!snapshots.length||snapshots.length>500)throw Error('Provide 1–500 OpenSky snapshot objects.');
 const groups=new Map(),stats={input:0,skipped:0};
 for(const snap of snapshots){if(!snap||!Array.isArray(snap.states)||!finite(snap.time))throw Error('OpenSky snapshot needs numeric time and states array.');if(snap.states.length>25000)throw Error('Snapshot too large.');for(const row of snap.states){stats.input++;if(!Array.isArray(row)||typeof row[0]!=='string'){stats.skipped++;continue;}const id=String(row[0]||'').trim().toLowerCase();const lat=row[6],lon=row[5],alt=finite(row[13])?row[13]:row[7],posTime=finite(row[3])?row[3]:null;
 if(!/^[a-f0-9]{6}$/.test(id)||!finite(lat)||!finite(lon)||!finite(alt)||posTime===null||alt<0||Math.abs(lat)>90||Math.abs(lon)>180){stats.skipped++;continue;}
 const t=posTime*1000;if(!finite(t)||t<0){stats.skipped++;continue;}
 const p={t,time_iso:new Date(t).toISOString(),lat,lon,alt,speed:finite(row[9])&&row[9]>=0?row[9]:null,heading:finite(row[10])?(row[10]%360+360)%360:null,source:'OpenSky-format JSON',altKind:finite(row[13])?'geometric altitude':'barometric altitude',icao24:id,callsign:String(row[1]||'').trim(),onGround:row[8]===true};
 const points=groups.get(id)||[];if(points.length<10000)points.push(p);groups.set(id,points);
 }}
 if(!groups.size)throw Error('No usable OpenSky state vectors with coordinates, timestamps and altitude were found.');
 const aircraft=[...groups].map(([icao24,points])=>{points.sort((a,b)=>a.t-b.t);const unique=points.filter((p,i)=>i===0||p.t!==points[i-1].t);return {icao24,callsign:unique.at(-1).callsign||icao24,points:unique,samples:unique.length,onGround:unique.at(-1).onGround,latest:unique.at(-1).time_iso};}).sort((a,b)=>b.samples-a.samples||a.icao24.localeCompare(b.icao24));
 return {aircraft,stats};
}
function validateRoute(name,coords){
 if(coords.length<2||coords.length>20000)throw Error('Route requires 2–20,000 points.');
 const p=coords.map(v=>coord(v.lat,v.lon));let length=0;for(let i=1;i<p.length;i++)length+=distance(p[i-1],p[i]);if(length<=0||length>2000000)throw Error('Route length is outside a useful teaching range (0–2,000 km).');
 return {name:String(name||'Imported route').slice(0,100),points:p,lengthM:length,count:p.length};
}
function parseGeoJSON(data){const o=typeof data==='string'?JSON.parse(data):data;const features=o?.type==='FeatureCollection'?o.features:o?.type==='Feature'?[o]:[{geometry:o,properties:{}}];
 if(!Array.isArray(features)||features.length>1500)throw Error('Invalid GeoJSON feature list.');
 const routes=[];for(const f of features){const g=f.geometry;if(!g||!['LineString','MultiLineString'].includes(g.type))continue;const segments=g.type==='LineString'?[g.coordinates]:g.coordinates;
 for(let i=0;i<segments.length;i++){const coords=segments[i].map(p=>{if(!Array.isArray(p)||p.length<2)throw Error('GeoJSON coordinates need [longitude,latitude].');return {lat:Number(p[1]),lon:Number(p[0])};});
 routes.push(validateRoute(f.properties?.route_short_name||f.properties?.name||f.id||'GeoJSON line',coords));if(routes.length>50)throw Error('Too many route lines (maximum 50).');}}
 if(!routes.length)throw Error('GeoJSON must contain one or more LineString geometries.');return routes;}
function parseGTFSShapes(csv){const rows=decodeCSV(csv);if(rows.length<3)throw Error('GTFS shapes.txt needs at least two positions.');const h=rows.shift().map(x=>x.toLowerCase());const needed=['shape_id','shape_pt_lat','shape_pt_lon','shape_pt_sequence'];for(const name of needed)if(!h.includes(name))throw Error('GTFS shapes.txt missing '+name);if(rows.length>30000)throw Error('Too many shape rows (max 30,000).');
 const idx=k=>h.indexOf(k),groups=new Map();for(const r of rows){const name=r[idx('shape_id')];const latitude=Number(r[idx('shape_pt_lat')]),longitude=Number(r[idx('shape_pt_lon')]),sequence=Number(r[idx('shape_pt_sequence')]);if(!name||!Number.isSafeInteger(sequence)||sequence<0)throw Error('GTFS shape ID and sequence must be valid.');const p=coord(latitude,longitude),set=groups.get(name)||[];set.push({sequence,...p});groups.set(name,set);}
 if(groups.size>100)throw Error('More than 100 GTFS shapes; supply a smaller extract.');const routes=[];
 for(const [name,points] of groups){points.sort((a,b)=>a.sequence-b.sequence);for(let i=1;i<points.length;i++)if(points[i].sequence===points[i-1].sequence)throw Error('Duplicate shape_pt_sequence for '+name);routes.push(validateRoute(name,points));}
 return routes;}
function toFlightCSV(points){if(!Array.isArray(points)||!points.length||points.length>10000)throw Error('Select up to 10,000 positions.');return 'time_iso,latitude,longitude,altitude_m,groundspeed_mps,heading_deg\n'+points.map(p=>[p.time_iso,p.lat,p.lon,p.alt,p.speed??'',p.heading??''].join(',')).join('\n');}
function projection(points,width=640,height=240){if(!points.length)throw Error('No route points.');const xs=points.map(p=>p.lon),ys=points.map(p=>p.lat),lon0=Math.min(...xs),lon1=Math.max(...xs),lat0=Math.min(...ys),lat1=Math.max(...ys),aspect=Math.max(.05,Math.cos((lat0+lat1)*RAD/2)),dx=Math.max((lon1-lon0)*aspect,.00001),dy=Math.max(lat1-lat0,.00001),scale=Math.min((width-48)/dx,(height-48)/dy),xmid=(lon0+lon1)/2,ymid=(lat0+lat1)/2;
 return points.map(p=>({x:width/2+(p.lon-xmid)*aspect*scale,y:height/2-(p.lat-ymid)*scale}));}
return {coord,distance,decodeCSV,parseOpenSky,validateRoute,parseGeoJSON,parseGTFSShapes,toFlightCSV,projection};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitDataAdapters;
