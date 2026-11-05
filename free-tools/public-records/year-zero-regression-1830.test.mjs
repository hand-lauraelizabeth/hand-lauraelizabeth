import assert from 'node:assert/strict';
import test from 'node:test';
import {validateWorkspace,exportJSON} from './core.mjs';

const request=(submittedOn)=>({id:'req-0001',jurisdiction:'federal',agency:'Example agency',stage:'submitted',submittedOn,agencyTrackingId:'',description:'Synthetic fixture'});
const event=(date)=>({id:'evt-0001',requestId:'req-0001',date,kind:'note',sourceId:'src-0001',description:'Synthetic event'});
const workspace=(submittedOn,date)=>({version:1,requests:[request(submittedOn)],events:[event(date)]});

test('Gregorian historical dates reject year zero, preserve exact IDs, and respect leap centuries',()=>{
  for(const invalid of ['0000-01-01','0000-02-29','0100-02-29','1900-02-29','2026-02-29']){
    assert.throws(()=>validateWorkspace(workspace(invalid,'2000-02-29')),/Invalid submitted date/);
    assert.throws(()=>validateWorkspace(workspace('2000-02-29',invalid)),/Invalid event date/);
  }
  for(const valid of ['0001-01-01','0099-12-31','0100-02-28','0400-02-29','2000-02-29']){
    const result=validateWorkspace(workspace(valid,valid));
    assert.equal(result.requests[0].submittedOn,valid);
    assert.equal(result.events[0].date,valid);
    const reopened=JSON.parse(exportJSON(result));
    assert.equal(reopened.requests[0].id,'req-0001');
    assert.equal(reopened.events[0].sourceId,'src-0001');
  }
});
