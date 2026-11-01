import assert from 'node:assert/strict';
import {startLocalDownload} from './download-guard.mjs';
let checks=0;
function check(value,label){assert.ok(value,label);checks++;}
function fixture(mode='ok'){
  const events=[],timers=[],blobs=[];
  const urlRef={
    createObjectURL(blob){blobs.push(blob);events.push('create');if(mode==='url')throw Error('blocked URL');return 'blob:synthetic';},
    revokeObjectURL(url){events.push('revoke:'+url);}
  };
  const documentRef={body:{append(anchor){events.push('append');if(mode==='append')throw Error('blocked append');anchor.attached=true;}},createElement(tag){
    check(tag==='a','anchor element');return {attached:false,remove(){events.push('remove');this.attached=false;},click(){events.push('click');if(mode==='click')throw Error('blocked click');}};
  }};
  const schedule=(fn,ms)=>{events.push('schedule:'+ms);if(mode==='timer')throw Error('blocked timer');timers.push(fn);};
  const run=(content='\ufeffsourceId,claim\r\n"0001","safe"\r\n')=>startLocalDownload({
    filename:'evidence.csv',content,type:'text/csv;charset=utf-8',
    documentRef,urlRef,BlobRef:Blob,schedule
  });
  return {events,timers,blobs,run};
}
for(const mode of ['url','append','click']){
  const f=fixture(mode);
  assert.throws(()=>f.run(),/blocked/);checks++;
  check(!f.events.includes('schedule:2000'),'failed download does not schedule success cleanup');
  check(!f.events.includes('click')||mode==='click','click only attempted when anchor appended');
  check(f.events.includes('remove')||mode==='url','failed anchor removed when created');
  check(f.events.filter(e=>e==='revoke:blob:synthetic').length===(mode==='url'?0:1),'failed URL revoked exactly once');
  check(f.blobs.length===1,'original Blob constructed without upload');
}
const f=fixture();
check(f.run()===true,'successful activation returns started');
check(f.events.includes('click'),'download activation attempted');
check(f.events.includes('remove'),'temporary anchor removed on success');
check(!f.events.includes('revoke:blob:synthetic'),'URL not revoked before deferred cleanup');
check(f.timers.length===1,'one cleanup scheduled');
check(f.blobs[0].type==='text/csv;charset=utf-8','CSV MIME preserved');
check([...new Uint8Array(await f.blobs[0].arrayBuffer()).slice(0,3)].join(',')==='239,187,191','CSV UTF-8 BOM bytes preserved');
check((await f.blobs[0].text()).startsWith('sourceId,claim\r\n"0001"'),'CSV content unchanged after UTF-8 BOM decoding');
f.timers[0]();
check(f.events.filter(e=>e==='revoke:blob:synthetic').length===1,'URL revoked after successful activation');
const j=fixture();
const json='{"schema":"evidence-timeline-v1","records":[{"sourceId":"0001","claim":"🧪"}]}\n';
check(j.run(json)===true,'exact JSON can start');
check((await j.blobs[0].text())===json,'Unicode and source ID unchanged');
const timer=fixture('timer');
check(timer.run()===true,'timer failure does not falsely claim click failure');
check(timer.events.includes('revoke:blob:synthetic'),'timer failure immediately reclaims URL');
check(timer.events.includes('remove'),'timer failure removes temporary link');
console.log('PASS: '+checks+' guarded local download assertions');
