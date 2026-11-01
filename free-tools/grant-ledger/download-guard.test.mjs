import assert from 'node:assert/strict';
import {startLocalDownload} from './download-guard.mjs';

let checks=0;
const ok=(value,label)=>{assert.ok(value,label);checks++;};
for(const [filename,type,content] of [
  ['grant-transactions.csv','text/csv;charset=utf-8','"0001","=2+2"\r\n'],
  ['grant-current-state.json','application/json;charset=utf-8','{"id":" 0001 ","note":"日本語"}'],
  ['grant-evidence.json','application/json;charset=utf-8','{"correctionHistory":{"entries":[]}}']
]){
  for(const failure of ['none','url','append','click','timer']){
    let created=0,revoked=0,appended=0,removed=0,clicked=0,blob=null,scheduled=null;
    const urlRef={
      createObjectURL(value){blob=value;if(failure==='url')throw Error('private internal exception');created++;return 'blob:synthetic';},
      revokeObjectURL(value){ok(value==='blob:synthetic','revoke correct URL');revoked++;}
    };
    const anchor={
      hidden:false,href:'',download:'',
      click(){clicked++;if(failure==='click')throw Error('private internal exception');},
      remove(){if(appended>removed)removed++;}
    };
    const documentRef={
      createElement(tag){ok(tag==='a','anchor element');return anchor;},
      body:{append(value){ok(value===anchor,'append correct anchor');if(failure==='append')throw Error('private internal exception');appended++;}}
    };
    const schedule=(fn,delay)=>{ok(delay===2000,'bounded revoke delay');if(failure==='timer')throw Error('timer blocked');scheduled=fn;};
    let threw=false;
    try{
      ok(startLocalDownload({filename,content,type,documentRef,urlRef,BlobRef:Blob,schedule})===true,'download initiated');
    }catch{threw=true;}
    ok(threw===(failure==='url'||failure==='append'||failure==='click'),'expected exception only for failed initiation');
    ok(appended===removed,'no temporary anchor remains');
    ok(created===(failure==='url'?0:1),'URL creation accounting');
    ok(clicked===(failure==='url'||failure==='append'?0:1),'click accounting');
    if(scheduled)scheduled();
    ok(revoked===created,'created URL revoked on failure or timer');
    if(blob){
      ok(blob.type===type,'exact MIME');
      ok(await blob.text()===content,'exact evidence content');
    }
    if(failure==='none')ok(anchor.download===filename&&anchor.href==='blob:synthetic'&&anchor.hidden,'download metadata');
  }
}
console.log('PASS: '+checks+' FT-06 synthetic download lifecycle assertions');
