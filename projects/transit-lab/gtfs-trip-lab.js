/* GTFS Schedule trip-pattern importer: local files, exact trip_id/stop_id joins. */
const TransitTripPatterns=(()=>{
'use strict';
function fields(line){
 const out=[];let value='',quoted=false;
 const text=String(line).replace(/^\uFEFF/,'');
 for(let i=0;i<text.length;i++){
  const c=text[i];
  if(c==='"'){if(quoted&&text[i+1]==='"'){value+='"';i++;}else quoted=!quoted;}
  else if(c===','&&!quoted){out.push(value.trim());value='';}
  else value+=c;
 }
 if(quoted)throw Error('Unclosed CSV quote.');
 out.push(value.trim());return out;
}
function header(line,needed){
 const columns=fields(line).map(x=>x.toLowerCase().trim());
 for(const col of needed)if(!columns.includes(col))throw Error('GTFS column missing: '+col);
 return columns;
}
function object(columns,values){const result={};columns.forEach((c,i)=>{result[c]=values[i]??''});return result;}
function trips(content,limit=60000){
 if(String(content).length>18000000)throw Error('trips.txt exceeds 18 MB import limit; select a smaller GTFS extract.');
 const rows=String(content).trim().split(/\r?\n/),cols=header(rows.shift(),['trip_id','route_id','service_id']);
 if(rows.length>limit)throw Error('Too many trips; supply a smaller extract.');
 const result=[];
 for(const line of rows){if(!line.trim())continue;const r=object(cols,fields(line));if(r.trip_id&&r.route_id)result.push({tripId:r.trip_id,routeId:r.route_id,serviceId:r.service_id||'',headsign:r.trip_headsign||'',direction:r.direction_id||'',shapeId:r.shape_id||''});}
 return result;
}
function seconds(time){
 const m=/^(\d{1,2}):([0-5]\d):([0-5]\d)$/.exec(String(time));
 if(!m)return null;const h=Number(m[1]);return h<=47?h*3600+Number(m[2])*60+Number(m[3]):null;
}
function normalizeStopId(id){return String(id||'').trim().toUpperCase().replace(/([0-9A-Z]{2,})[NS]$/,'$1');}
function stopTimes(content,allowed){
 const lines=String(content).trim().split(/\r?\n/),columns=header(lines.shift(),['trip_id','arrival_time','departure_time','stop_id','stop_sequence']);
 return parseStopTimeRows(lines,columns,allowed);
}
function parseStopTimeRows(rows,cols,allowed){
 const set=allowed instanceof Set?allowed:new Set(allowed);
 const collected=new Map([...set].map(x=>[x,[]]));
 for(const line of rows){
  if(!line.trim())continue;
  const fieldsArray=fields(line),id=fieldsArray[cols.indexOf('trip_id')];
  if(!set.has(id))continue;
  const r=object(cols,fieldsArray),sequence=Number(r.stop_sequence);
  if(!Number.isSafeInteger(sequence)||sequence<0||!r.stop_id)continue;
  collected.get(id).push({tripId:id,stopId:r.stop_id,sequence,arrival:r.arrival_time,departure:r.departure_time,arrivalSec:seconds(r.arrival_time),departureSec:seconds(r.departure_time)});
 }
 for(const v of collected.values())v.sort((a,b)=>a.sequence-b.sequence);
 return collected;
}
async function streamStopTimes(file,allowed,progress){
 if(!file||file.size>180000000)throw Error('stop_times.txt larger than 180 MB; supply a route-specific extract.');
 const reader=file.stream().getReader(),decoder=new TextDecoder();let pending='',columns=null,bytes=0,scanned=0;
 const collected=new Map([...allowed].map(id=>[id,[]]));
 function line(raw){
  if(!columns){columns=header(raw,['trip_id','arrival_time','departure_time','stop_id','stop_sequence']);return;}
  if(!raw.trim())return;
  scanned++;const values=fields(raw),id=values[columns.indexOf('trip_id')];
  if(!allowed.has(id))return;
  const r=object(columns,values),sequence=Number(r.stop_sequence);
  if(!Number.isSafeInteger(sequence)||sequence<0||!r.stop_id)return;
  const a=collected.get(id);
  if(a.length>=250)throw Error('One trip has more than 250 stop rows.');
  a.push({tripId:id,stopId:r.stop_id,sequence,arrival:r.arrival_time,departure:r.departure_time,arrivalSec:seconds(r.arrival_time),departureSec:seconds(r.departure_time)});
 }
 try{
 while(true){
  const item=await reader.read();if(item.done)break;
  bytes+=item.value.byteLength;pending+=decoder.decode(item.value,{stream:true});
  if(pending.length>500000)throw Error('Unexpectedly long GTFS record.');
  let i;
  while((i=pending.indexOf('\n'))!==-1){const lineText=pending.slice(0,i).replace(/\r$/,'');pending=pending.slice(i+1);line(lineText);}
  if(progress&&bytes%1800000<item.value.byteLength)progress(bytes,file.size,scanned);
 }
 pending+=decoder.decode();if(pending.trim())line(pending.replace(/\r$/,''));
 for(const rows of collected.values())rows.sort((a,b)=>a.sequence-b.sequence);
 if(!columns)throw Error('Empty stop_times.txt');
 return {collected,scanned,bytes};
 }finally{reader.releaseLock();}
}
function sliceLine(route,start,end,reverse=false){
 const points=route.points;if(!Array.isArray(points)||points.length<2)throw Error('Polyline missing');
 const R=TransitRailGeometry;
 const cumulative=[0];for(let i=1;i<points.length;i++)cumulative.push(cumulative.at(-1)+R.distance(points[i-1],points[i]));
 const length=cumulative.at(-1),a=Math.max(0,Math.min(length,start)),b=Math.max(0,Math.min(length,end));
 if(b-a<100)throw Error('Trip spans less than 100 mapped meters.');
 function at(distance){
  for(let i=1;i<cumulative.length;i++){
   if(distance<=cumulative[i]||i===cumulative.length-1){
    const part=(distance-cumulative[i-1])/Math.max(1e-9,cumulative[i]-cumulative[i-1]),p=points[i-1],q=points[i];
    const delta=((q.lon-p.lon+540)%360)-180;
    return {lat:p.lat+(q.lat-p.lat)*part,lon:((p.lon+delta*part+540)%360)-180};
   }
  }
  return points.at(-1);
 }
 const sliced=[at(a)];
 for(let i=1;i<cumulative.length-1;i++)if(cumulative[i]>a&&cumulative[i]<b)sliced.push({...points[i]});
 sliced.push(at(b));
 return reverse?sliced.reverse():sliced;
}
function routeForTrip(route,trip,rows){
 if(!route?.stations?.length)throw Error('Load route shapes with matched MTA stations before importing a trip.');
 if(!Array.isArray(rows)||rows.length<2)throw Error('Trip needs at least two stop-time records.');
 const stationsById=new Map(route.stations.map(x=>[normalizeStopId(x.id),x]));
 const matched=[];
 for(const r of rows){
  const station=stationsById.get(normalizeStopId(r.stopId));
  if(station&&Number.isFinite(station.distanceM))matched.push({...station,arrival:r.arrival,departure:r.departure,arrivalSec:r.arrivalSec,departureSec:r.departureSec,tripSequence:r.sequence});
 }
 if(matched.length<2)throw Error('Fewer than two scheduled trip stops matched published service geometry.');
 const reverse=matched.at(-1).distanceM<matched[0].distanceM;
 for(let i=1;i<matched.length;i++){
  const change=(matched[i].distanceM-matched[i-1].distanceM)*(reverse?-1:1);
  if(change< -40)throw Error('Trip changes direction or branches across the selected service-line shape. Choose another trip or segment.');
 }
 const start=Math.min(matched[0].distanceM,matched.at(-1).distanceM),end=Math.max(matched[0].distanceM,matched.at(-1).distanceM);
 const first=matched[0].departureSec??matched[0].arrivalSec;
 const stations=matched.map(st=>({...st,distanceM:reverse?end-st.distanceM:st.distanceM-start,scheduledElapsedSec:Number.isFinite(first)&&Number.isFinite(st.arrivalSec)?st.arrivalSec-first:null}));
 const points=sliceLine(route,start,end,reverse),lengthM=end-start;
 if(lengthM<100)throw Error('Schedule trip covers insufficient mapped distance.');
 return {...route,points,lengthM,stations,name:route.name+' · '+(trip.headsign||trip.tripId),trip:{...trip,reverse,firstDeparture:matched[0].departure,plannedMinutes:Number.isFinite(matched.at(-1).arrivalSec)&&Number.isFinite(first)?(matched.at(-1).arrivalSec-first)/60:null,matchedStops:stations.length},geometrySource:'MTA service-line centerline, trimmed to scheduled matched stops'};
}
return {fields,header,trips,seconds,normalizeStopId,stopTimes,parseStopTimeRows,streamStopTimes,routeForTrip,sliceLine};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=TransitTripPatterns;
(function tripStudio(){
'use strict';
if(typeof document==='undefined'||typeof TransitRailGeometry==='undefined')return;
const root=document.getElementById('leh-transit');if(!root||root.dataset.tripStudio==='ready')return;root.dataset.tripStudio='ready';
const T=TransitTripPatterns,$=id=>document.getElementById(id);
const box=document.createElement('section');box.className='panel gt-lab';
box.innerHTML='<div class="top"><div><p class="eyebrow">Scheduled stop patterns</p><h2>Published GTFS timetable explorer</h2></div><span class="pill">Local source files</span></div>'+
'<p>Use <strong>trips.txt</strong> and <strong>stop_times.txt</strong> from the same published MTA static GTFS ZIP. Read the published stop sequence for a specific trip and run the model over its ordered station calls. The feed’s <code>service_id</code> is not a guarantee the trip runs today.</p>'+
'<p class="gt-small"><a href="https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip" target="_blank" rel="noopener">Official MTA static GTFS ZIP</a> · <a href="https://gtfs.org/documentation/schedule/reference/" target="_blank" rel="noopener">GTFS Schedule reference</a>. Extract the two text files before importing; files stay on your device. The stop-times file may be large.</p>'+
'<label for="gt-trips">trips.txt <input id="gt-trips" type="file" accept=".txt,.csv,text/plain"></label>'+
'<label for="gt-stoptimes">stop_times.txt <input id="gt-stoptimes" type="file" accept=".txt,.csv,text/plain"></label>'+
'<div class="actions"><button id="gt-import" type="button">Read scheduled trips</button><button id="gt-exit" type="button" class="secondary">Restore full route</button></div>'+
'<label for="gt-choice" id="gt-choice-wrap" hidden>Choose a published trip<select id="gt-choice"></select></label>'+
'<p id="gt-status" role="status" class="gt-status">First load a published MTA service route above, then select the two GTFS files. No network request has been made for timetable records.</p>'+
'<div id="gt-pattern" class="gt-pattern" hidden><h3>Scheduled station calls</h3><ol id="gt-stops"></ol><p id="gt-progress" role="status"></p></div>'+
'<p class="gt-small">Timetable times are published GTFS local service-day values; 24:xx and later indicate the next clock day on the same service day. Mapped station positions are approximate point-to-line matches. This is not a live train, real arrival prediction, dispatch model or signal system.</p>';
const css=document.createElement('style');css.textContent='#leh-transit .gt-lab{display:grid;gap:.67rem}#leh-transit .gt-lab h3{font:700 1.04rem Georgia,serif;margin:.15rem 0}#leh-transit .gt-lab p{font-size:.88rem;line-height:1.5}#leh-transit .gt-lab .gt-small{font-size:.78rem;color:var(--muted)}#leh-transit .gt-lab input[type=file]{display:block;width:100%;margin:.25rem 0}#leh-transit .gt-lab select{display:block;width:100%;margin:.35rem 0}#leh-transit .gt-lab .gt-status{padding:.65rem;background:#eaf3ee;border-radius:8px}#leh-transit .gt-lab .gt-pattern{padding:.7rem;border:1px solid var(--border);border-radius:9px}#leh-transit .gt-lab ol{padding-left:1.3rem;max-height:250px;overflow:auto;font-size:.84rem}#leh-transit .gt-lab li{margin:.3rem 0}#leh-transit .gt-lab [hidden]{display:none!important}';
document.head.append(css);root.querySelector('.main-stack')?.append(box);
let base=null,chosen=null,options=[],timetable=null,mode='flight';
function alert(message){$('gt-status').textContent=message;}
function renderTrip(option){
 if(!base||!timetable)return;
 const rows=timetable.get(option.tripId)||[];
 try{
  chosen=T.routeForTrip(base,option,rows);
  root.dispatchEvent(new CustomEvent('leh-transit-route-selected',{detail:{route:chosen}}));
  $('gt-pattern').hidden=false;const ol=$('gt-stops');ol.replaceChildren();
  for(const st of chosen.stations){const li=document.createElement('li');li.textContent=(st.arrival||'—')+' '+st.name+' · '+(st.distanceM/1000).toFixed(2)+' km; mapped offset '+Math.round(st.offsetM)+' m';ol.append(li);}
  alert('Loaded published '+option.routeId+' trip toward '+(option.headsign||'unspecified headsign')+' · GTFS service '+option.serviceId+' · '+chosen.stations.length+' mapped scheduled stop calls · '+(chosen.lengthM/1000).toFixed(2)+' km derived shape length. '+(Number.isFinite(chosen.trip.plannedMinutes)?chosen.trip.plannedMinutes.toFixed(0)+' scheduled minutes':'Timing incomplete')+'. A GTFS service calendar is not loaded; no claim this trip operates today.');
 }catch(error){$('gt-pattern').hidden=true;alert('Trip cannot be aligned confidently: '+error.message);}
}
$('gt-choice').addEventListener('change',()=>{const option=options[Number($('gt-choice').value)];if(option)renderTrip(option);});
$('gt-import').addEventListener('click',async()=>{
 if(!base){alert('Load a MTA line with official station locations first.');return;}
 const a=$('gt-trips').files?.[0],b=$('gt-stoptimes').files?.[0];
 if(!a||!b){alert('Select both trips.txt and stop_times.txt extracted from one MTA feed version.');return;}
 if(a.size>18000000){alert('trips.txt exceeds 18 MB; select a smaller route extract.');return;}
 const button=$('gt-import');button.disabled=true;
 try{
  alert('Reading published trip IDs…');
  const all=T.trips(await a.text()),service=String(base.service||'').toUpperCase();
  options=all.filter(x=>x.routeId.toUpperCase()===service).slice(0,60);
  if(!options.length)throw Error('No trips for the selected service '+service+'. Check that both sources are from the MTA subway feed.');
  alert('Reading the selected trip subset from stop_times.txt. Large files are streamed, not entirely loaded into memory.');
  const ids=new Set(options.map(o=>o.tripId)),result=await T.streamStopTimes(b,ids,(bytes,total)=>alert('Reading published stop times: '+Math.round(bytes/total*100)+'% · '+Math.round(bytes/1048576)+' MiB. No files uploaded.'));
  timetable=result.collected;options=options.filter(x=>(timetable.get(x.tripId)||[]).length>=2);
  if(!options.length)throw Error('No complete stop sequences for the sampled trips. Try a route-specific extract or another GTFS version.');
  options.sort((x,y)=>(timetable.get(x.tripId)?.[0]?.departureSec??Infinity)-(timetable.get(y.tripId)?.[0]?.departureSec??Infinity));
  const dropdown=$('gt-choice');dropdown.replaceChildren();
  options.forEach((trip,i)=>{const o=document.createElement('option');o.value=String(i);const first=timetable.get(trip.tripId)[0];o.textContent=(first.departure||'time unavailable')+' · '+trip.routeId+' '+(trip.headsign||'')+' · service '+trip.serviceId;dropdown.append(o);});
  $('gt-choice-wrap').hidden=false;renderTrip(options[0]);
 }catch(error){alert('Timetable import unavailable: '+error.message+'. Existing published-line geometry and generic controls still work.');}
 finally{button.disabled=false;}
});
$('gt-exit').addEventListener('click',()=>{
 if(base){chosen=null;root.dispatchEvent(new CustomEvent('leh-transit-route-selected',{detail:{route:base}}));$('gt-pattern').hidden=true;alert('Full published MTA route restored. A timetable trip is not selected.');}
});
root.addEventListener('leh-transit-route-selected',event=>{
 const r=event.detail?.route;if(!r||r.trip)return;
 base=r;chosen=null;options=[];timetable=null;$('gt-choice-wrap').hidden=true;$('gt-pattern').hidden=true;
 alert('Selected '+r.name+'. Upload matching official GTFS trips.txt and stop_times.txt to inspect individual scheduled stopping patterns.');
});
root.addEventListener('leh-transit-route-cleared',()=>{base=null;chosen=null;options=[];timetable=null;$('gt-pattern').hidden=true;$('gt-choice-wrap').hidden=true;alert('No published route selected.');});
root.addEventListener('leh-transit-state',event=>{
 const d=event.detail;if(!d?.state)return;
 mode=d.mode;box.hidden=mode!=='train';
 if(chosen&&mode==='train'){
  const next=chosen.stations.find(x=>x.distanceM>d.state.pos+.2&&Number.isFinite(x.scheduledElapsedSec));
  $('gt-progress').textContent=next?'Next scheduled call: '+next.name+' · published '+next.arrival+' · '+Math.round(next.distanceM-d.state.pos)+' modeled meters away. '+(Number.isFinite(next.scheduledElapsedSec)?'Planned elapsed '+Math.round(next.scheduledElapsedSec/60)+' min; simulated elapsed '+(d.state.time/60).toFixed(1)+' min.':''):'End of selected trip. Published stop sequence is reference, not observed running.';
 }
});
box.hidden=root.transitLatest?.mode!=='train';
})();
