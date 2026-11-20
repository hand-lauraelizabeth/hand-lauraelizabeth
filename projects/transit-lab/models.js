/* Transit Lab teaching-level point-mass models: SI internal units, explicit assumptions. */
const TransitModels=(()=>{'use strict';
const G=9.80665,EARTH=6371008.8,TO_RAD=Math.PI/180,TO_DEG=180/Math.PI;
const AIRCRAFT={trainer:{name:'Light single-engine trainer · generic',mass:1100,wing:16.2,cd0:.035,k:.045,thrust:2800,clMax:1.5,speed:55,alt:1200,throttle:60},transport:{name:'Twin-jet transport · generic',mass:65000,wing:125,cd0:.026,k:.043,thrust:210000,clMax:1.6,speed:190,alt:3200,throttle:35},glider:{name:'Sailplane · generic',mass:500,wing:15,cd0:.018,k:.028,thrust:0,clMax:1.4,speed:42,alt:2200,throttle:0}};
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
function moveLatLon(lat,lon,north,east){const phi=lat*TO_RAD;const dNorth=north/EARTH;const dLon=east/(EARTH*Math.max(.05,Math.cos(phi)));return {lat:clamp(lat+dNorth*TO_DEG,-89.9,89.9),lon:((lon+dLon*TO_DEG+540)%360)-180};}
function flightInit(model='trainer'){const p=AIRCRAFT[model];if(!p)throw Error('Unknown aircraft profile');return {kind:'flight',profile:model,lat:40.644,lon:-73.782,alt:p.alt,speed:p.speed,heading:45,bank:0,flightPath:0,throttle:p.throttle,time:0,stalled:false,density:1.225,drag:0,liftCoefficient:0,turnRate:0};}
function flightStep(s,dt){const p=AIRCRAFT[s.profile];if(!p)throw Error('Unknown aircraft profile');dt=clamp(Number(dt)||0,0,2);const bank=clamp(s.bank,-45,45)*TO_RAD,gamma=clamp(s.flightPath,-12,12)*TO_RAD;const speed=Math.max(5,s.speed),rho=1.225*Math.exp(-Math.max(0,s.alt)/8500),q=.5*rho*speed*speed;
  // Quasi-steady coordinated flight: sufficient lift to balance weight normal to the flight path; not a 6-DOF flight model.
  const cl=p.mass*G*Math.cos(gamma)/(Math.max(1,q*p.wing)*Math.max(.4,Math.cos(bank)));
  const drag=q*p.wing*(p.cd0+p.k*cl*cl),thrust=p.thrust*clamp(s.throttle,0,100)/100;
  const accel=(thrust-drag-p.mass*G*Math.sin(gamma))/p.mass;
  const nextSpeed=clamp(speed+accel*dt,5,p.maxSpeed??360);const turnRate=G*Math.tan(bank)/Math.max(5,speed);const heading=((s.heading+turnRate*dt*TO_DEG)%360+360)%360;
  const horizontal=.5*(speed+nextSpeed)*Math.cos(gamma)*dt;
  const h=heading*TO_RAD,loc=moveLatLon(s.lat,s.lon,horizontal*Math.cos(h),horizontal*Math.sin(h));
  return {...s,...loc,speed:nextSpeed,alt:Math.max(0,s.alt+.5*(speed+nextSpeed)*Math.sin(gamma)*dt),heading,time:s.time+dt,density:rho,drag,liftCoefficient:cl,stalled:cl>p.clMax,turnRate:turnRate*TO_DEG};
}
const TRAINS={metro:{name:'Metro · generic',limit:22.2,traction:1.1,brake:1.25},regional:{name:'Regional rail · generic',limit:44.4,traction:.75,brake:1.05},highspeed:{name:'High-speed rail · generic',limit:83.3,traction:.55,brake:.9}};
function trainInit(profile='metro'){if(!TRAINS[profile])throw Error('Unknown train profile');return {kind:'train',profile,pos:0,speed:0,throttle:0,brake:0,grade:0,time:0,length:10000,limit:TRAINS[profile].limit,terminalOverrun:false,stops:[0,2500,5500,10000],station:'Depart origin'};}
function brakingDistance(speed,decel){return decel>0?speed*speed/(2*decel):Infinity;}
function trainStep(s,dt){dt=clamp(Number(dt)||0,0,2);const spec=TRAINS[s.profile];const rolling=.03,traction=spec.traction*clamp(s.throttle,0,100)/100,brake=spec.brake*clamp(s.brake,0,100)/100;
  const accel=traction-brake-rolling-G*clamp(s.grade,-4,4)/100;
  let speed=clamp(s.speed+accel*dt,0,s.limit),pos=clamp(s.pos+.5*(s.speed+speed)*dt,0,s.length);
  // Clipping to the route boundary is not a physical or successful platform stop.
  const terminalOverrun=Boolean(s.terminalOverrun)||(pos===s.length&&speed>.5);
  if(pos===s.length)speed=0;
  return {...s,pos,speed,time:s.time+dt,accel,terminalOverrun,brakingDistance:brakingDistance(speed,spec.brake),nearestStop:s.stops.find(x=>x>pos+.1)??s.length};
}
function subInit(){return {kind:'sub',lat:36.14,lon:-74.55,depth:50,verticalSpeed:0,ballast:0,speed:3,heading:90,time:0,waterDensity:1025,pressure:oceanPressure(50),accel:0};}
function oceanPressure(depth,rho=1025){return 101325+rho*G*Math.max(0,depth);} // absolute Pa, surface = standard atmosphere
function subStep(s,dt){dt=clamp(Number(dt)||0,0,2);const rho=clamp(Number(s.waterDensity)||1025,1000,1030),neutralMass=1000000,volume=neutralMass/1025;const totalMass=neutralMass+clamp(s.ballast,-100,100)*50; // ±5 t ballast: illustrative control
  const buoyancy=rho*volume*G,weight=totalMass*G;
  const accel=(weight-buoyancy)/totalMass-.045*s.verticalSpeed*Math.abs(s.verticalSpeed); // velocity opposite drag
  let verticalSpeed=clamp(s.verticalSpeed+accel*dt,-3,3),depth=clamp(s.depth+(s.verticalSpeed+verticalSpeed)*.5*dt,0,1000);if(depth===0||depth===1000)verticalSpeed=0;
  const horizontal=clamp(s.speed,0,20)*.514444*dt,h=s.heading*TO_RAD,loc=moveLatLon(s.lat,s.lon,horizontal*Math.cos(h),horizontal*Math.sin(h));
  return {...s,...loc,depth,verticalSpeed,accel,pressure:oceanPressure(depth,rho),time:s.time+dt};
}
function parseTrackCsv(csv){const lines=String(csv).replace(/^\uFEFF/,'').trim().split(/\r?\n/).filter(Boolean);if(lines.length<2)throw Error('CSV needs a header and at least one row.');
  function parseRow(l){const r=[];let q=false,v='';for(let i=0;i<l.length;i++){const c=l[i];if(c==='"'){if(q&&l[i+1]==='"'){v+='"';i++;}else q=!q;}else if(c===','&&!q){r.push(v.trim());v='';}else v+=c;}r.push(v.trim());return r;}
  const h=parseRow(lines[0]).map(x=>x.toLowerCase().replace(/\s+/g,'_'));
  for(const col of ['time_iso','latitude','longitude','altitude_m'])if(!h.includes(col))throw Error('Missing required column: '+col);
  const result=lines.slice(1).map((line,i)=>{const values=parseRow(line),get=k=>values[h.indexOf(k)]??'',latitude=Number(get('latitude')),longitude=Number(get('longitude')),altitude_m=Number(get('altitude_m')),time_iso=get('time_iso'),t=Date.parse(time_iso),groundspeed_mps=get('groundspeed_mps')===''?null:Number(get('groundspeed_mps')),heading_deg=get('heading_deg')===''?null:Number(get('heading_deg'));
    if(!Number.isFinite(t)||!Number.isFinite(latitude)||Math.abs(latitude)>90||!Number.isFinite(longitude)||Math.abs(longitude)>180||!Number.isFinite(altitude_m)||altitude_m<0||groundspeed_mps!==null&&(!Number.isFinite(groundspeed_mps)||groundspeed_mps<0)||heading_deg!==null&&!Number.isFinite(heading_deg))throw Error('Invalid track values on CSV row '+(i+2));return {time_iso,t,lat:latitude,lon:longitude,alt:altitude_m,speed:groundspeed_mps,heading:heading_deg===null?null:((heading_deg%360)+360)%360};});
  for(let i=1;i<result.length;i++)if(result[i].t<=result[i-1].t)throw Error('Track timestamps must be strictly increasing.');if(result.length>10000)throw Error('Limit: 10,000 track points.');return result;
}
return {G,EARTH,AIRCRAFT,TRAINS,flightInit,flightStep,trainInit,trainStep,subInit,subStep,oceanPressure,brakingDistance,moveLatLon,parseTrackCsv,clamp};
})();if(typeof module!=='undefined'&&module.exports)module.exports=TransitModels;
