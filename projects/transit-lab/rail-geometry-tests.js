const assert=require('node:assert/strict'),R=require('./rail-geometry.js');
const route={name:'Demo 7',service:'7',lengthM:2000,points:[{lat:40.75,lon:-73.95},{lat:40.75,lon:-73.9263}]};
const rows=R.stationRows([
 {gtfs_stop_id:'701',stop_name:'First',gtfs_latitude:'40.7501',gtfs_longitude:'-73.948',daytime_routes:'7 7X',structure:'Elevated'},
 {gtfs_stop_id:'702',stop_name:'Second',gtfs_latitude:40.7501,gtfs_longitude:-73.935,daytime_routes:'7',structure:'Elevated'},
 {gtfs_stop_id:'703',stop_name:'Wrong route',gtfs_latitude:40.75,gtfs_longitude:-73.94,daytime_routes:'A C'},
 {gtfs_stop_id:'704',stop_name:'Far from route',gtfs_latitude:40.755,gtfs_longitude:-73.93,daytime_routes:'7'},
 {gtfs_stop_id:'705',stop_name:'Bad data',gtfs_latitude:999,gtfs_longitude:-74,daytime_routes:'7'}
]);
assert.equal(rows.length,4);
assert.equal(R.matchesService(rows[0],'7'),true);
assert.equal(R.matchesService(rows[2],'7'),false);
assert.equal(R.matchesService({daytimeRoutes:'SIR'},'SI'),true);
const projected=R.project(rows[1],route);
assert.ok(projected.distanceM>900&&projected.distanceM<1600);
assert.ok(projected.offsetM<30);
const enriched=R.attach(route,rows);
assert.equal(enriched.stations.length,2);
assert.ok(enriched.stations[0].distanceM<enriched.stations[1].distanceM);
assert.ok(enriched.stations[0].offsetM<20);
assert.equal(R.checkpoints(enriched).length,3);
assert.equal(R.checkpoints(enriched).at(-1),2000);
assert.deepEqual(R.checkpoints({...route,stations:[]}),[2000]);
assert.throws(()=>R.project({lat:40,lon:-73},{points:[]}));
const wrap={name:'Dateline',service:'1',lengthM:22239,points:[{lat:0,lon:179.9},{lat:0,lon:-179.9}]};
const projectedWrap=R.project({lat:0,lon:180},wrap);
assert.ok(projectedWrap.offsetM<1);assert.ok(projectedWrap.distanceM>10000&&projectedWrap.distanceM<12000);
console.log('Station parsing, service filtering, nearest-track chainage and dateline tests passed.');
