const assert=require('node:assert/strict'),T=require('./gtfs-trip-lab.js');
assert.equal(T.seconds('24:15:00'),87300);assert.equal(T.seconds('47:59:59'),172799);
assert.equal(T.seconds('48:00:00'),null);
assert.equal(T.normalizeStopId('701N'),'701');
assert.equal(T.normalizeStopId('701S'),'701');
assert.deepEqual(T.fields('"A,B",c,"D""E"'),['A,B','c','D"E']);
const trips=T.trips('route_id,service_id,trip_id,trip_headsign,direction_id\n7,W,TRIP1,Flushing,0\nA,W,TRIP2,Uptown,1\n');
assert.equal(trips.length,2);assert.equal(trips[0].routeId,'7');
const stopTimes=T.stopTimes('trip_id,stop_id,stop_sequence,arrival_time,departure_time\nTRIP1,701N,1,23:00:00,23:00:30\nTRIP1,702N,2,23:02:00,23:02:00\nTRIP2,A01N,1,20:00:00,20:00:10\n',new Set(['TRIP1']));
assert.equal(stopTimes.get('TRIP1').length,2);
const base={name:'7 Line',service:'7',lengthM:2100,points:[{lat:40,lon:-74},{lat:40,lon:-73.9753}],stations:[
 {id:'701',name:'One',lat:40,lon:-74,offsetM:5,distanceM:0},
 {id:'702',name:'Two',lat:40,lon:-73.98765,offsetM:4,distanceM:1050},
 {id:'703',name:'Three',lat:40,lon:-73.9753,offsetM:6,distanceM:2100}]};
const forward=T.routeForTrip(base,trips[0],[{stopId:'701N',sequence:1,arrival:'23:00:00',departure:'23:00:30',arrivalSec:82800,departureSec:82830},{stopId:'702N',sequence:2,arrival:'23:02:00',departure:'23:02:00',arrivalSec:82920,departureSec:82920}]);
assert.equal(forward.stations.length,2);assert.equal(forward.lengthM,1050);
assert.equal(forward.stations[0].distanceM,0);assert.equal(forward.stations[1].distanceM,1050);
assert.ok(forward.stations[1].scheduledElapsedSec===90);
const reversed=T.routeForTrip(base,trips[0],[{stopId:'703S',sequence:1,departure:'23:00:00',departureSec:82800,arrivalSec:82800},{stopId:'702S',sequence:2,arrival:'23:02:00',arrivalSec:82920}]);
assert.equal(reversed.trip.reverse,true);assert.equal(reversed.stations[0].distanceM,0);assert.equal(reversed.stations[1].distanceM,1050);
assert.throws(()=>T.routeForTrip(base,trips[0],[]));
console.log('GTFS trips, quoted CSV, 24+ hour times, directional stop IDs and mapped trips passed.');
