import test from 'node:test';
import assert from 'node:assert/strict';
import {startLocalDownload} from './download-guard.mjs';

function harness({createFails=false,appendFails=false,clickFails=false}={}){
 const state={links:[],urls:[],revoked:[],timers:[],clicked:0,blob:null};
 const urlApi={
  createObjectURL(blob){state.blob=blob;if(createFails)throw Error('private /home/example.csv');const url='blob:synthetic-'+state.urls.length;state.urls.push(url);return url;},
  revokeObjectURL(url){state.revoked.push(url);}
 };
 const documentRef={
  body:{append(link){if(appendFails)throw Error('append failed');state.links.push(link);}},
  createElement(tag){assert.equal(tag,'a');const link={href:'',download:'',click(){state.clicked++;if(clickFails)throw Error('secret path');},remove(){state.links=state.links.filter(v=>v!==link);}};return link;}
 };
 const schedule=(fn,delay)=>state.timers.push({fn,delay});
 const run=()=>startLocalDownload({data:'"V-0007","Café 供應商"\n',filename:'rfp-comparison.csv',mime:'text/csv',documentRef,urlApi,schedule});
 return {state,run};
}

test('blocked object URL creation is fail-closed and does not leak exception text',()=>{
 const {state,run}=harness({createFails:true});
 assert.throws(run,e=>e.message.includes('try again')&&!e.message.includes('/home/'));
 assert.equal(state.clicked,0);assert.equal(state.links.length,0);assert.equal(state.timers.length,0);
});
test('blocked DOM attachment preserves the evaluation and revokes URL',()=>{
 const {state,run}=harness({appendFails:true});
 assert.throws(run,/could not start/);assert.deepEqual(state.revoked,state.urls);
 assert.equal(state.links.length,0);assert.equal(state.timers.length,0);
});
test('blocked activation removes temporary link and revokes URL',()=>{
 const {state,run}=harness({clickFails:true});
 assert.throws(run,e=>e.message.includes('unchanged')&&!e.message.includes('secret'));
 assert.equal(state.clicked,1);assert.equal(state.links.length,0);
 assert.deepEqual(state.revoked,state.urls);assert.equal(state.timers.length,0);
});
test('successful initiation is not reported as a saved file; revocation is scheduled',async()=>{
 const {state,run}=harness();
 assert.equal(run(),undefined);assert.equal(state.clicked,1);assert.equal(state.links.length,0);
 assert.equal(state.timers.length,1);assert.equal(state.timers[0].delay,3000);
 assert.equal(await state.blob.text(),'"V-0007","Café 供應商"\n');
 assert.equal(state.blob.type,'text/csv;charset=utf-8');
 state.timers[0].fn();assert.deepEqual(state.revoked,state.urls);
});
test('failed attempt followed by successful retry uses original bytes',async()=>{
 const first=harness({clickFails:true});assert.throws(first.run,/could not start/);
 const second=harness();second.run();assert.equal(await second.state.blob.text(),'"V-0007","Café 供應商"\n');
});
