import test from 'node:test';
import assert from 'node:assert/strict';
import {bindReopen} from './reopen-ui.mjs';

function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return {promise, resolve};
}
function mockInput() {
  const attrs = new Map(), listeners = new Map();
  let files = [], focusCount = 0;
  return {
    get files() { return files; }, set files(next) { files = next; },
    set value(value) { if (value === '') files = []; },
    get value() { return files.length ? 'C:\\fakepath\\fixture.json' : ''; },
    setAttribute(name, value) { attrs.set(name, value); },
    getAttribute(name) { return attrs.get(name) ?? null; },
    removeAttribute(name) { attrs.delete(name); },
    addEventListener(name, callback) { listeners.set(name, callback); },
    emit(name) { return listeners.get(name)(); },
    focus() { focusCount++; },
    get focusCount() { return focusCount; }
  };
}
function fixture(valid) {
  const text = valid
    ? JSON.stringify({version:1, requests:[{
        id:'REQ-00007', jurisdiction:'federal', agency:'Example agency',
        stage:'draft', submittedOn:'', agencyTrackingId:'0000987',
        description:'Synthetic only'
      }], events:[]})
    : '{"version":1,"requests":[],"events":[],"\\u0076ersion":1}';
  const bytes = Buffer.from(text, 'utf8'), gate = deferred();
  return {
    gate,
    file: {
      name:'fixture.json', type:'application/json', size:bytes.length,
      arrayBuffer: () => gate.promise
    },
    finish() { gate.resolve(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength)); }
  };
}

for (const method of ['cancel', 'empty-change']) {
  for (const valid of [true, false]) {
    test(`${method} aborts ${valid ? 'valid' : 'invalid'} pending import without stale mutation`, async () => {
      const input = mockInput();
      globalThis.document = {getElementById: id => id === 'open-json' ? input : null};
      let state = {requests:[], events:[]}, writes = 0, status = '';
      bindReopen(() => state, next => {state=next;writes++;}, text => {status=text;});
      const pending = fixture(valid);
      input.files = [pending.file];
      const read = input.emit('change');
      assert.equal(input.getAttribute('aria-busy'),'true');
      assert.match(status,/Reading saved workspace locally/);
      if(method === 'cancel') {
        input.emit('cancel');
      } else {
        input.files = [];
        await input.emit('change');
      }
      assert.equal(input.getAttribute('aria-busy'),'false');
      assert.equal(input.getAttribute('aria-describedby'),'import-help');
      assert.equal(input.files.length,0);
      assert.match(status,/import canceled/);
      pending.finish();
      await read;
      assert.equal(writes,0);
      assert.deepEqual(state,{requests:[],events:[]});
      assert.match(status,/import canceled/);
      assert.equal(input.getAttribute('aria-invalid'),null);
      assert.equal(input.focusCount,0);
      const retry = fixture(true);
      input.files = [retry.file];
      const resumed = input.emit('change');
      retry.finish();
      await resumed;
      assert.equal(writes,1);
      assert.equal(state.requests[0].id,'REQ-00007');
      assert.equal(state.requests[0].agencyTrackingId,'0000987');
      assert.equal(input.getAttribute('aria-busy'),'false');
      assert.match(status,/Imported 1 requests/);
    });
  }
}

test('cancel event when idle does not erase the last status', () => {
  const input=mockInput();
  globalThis.document={getElementById:()=>input};
  let status='Existing confirmation';
  bindReopen(()=>({requests:[],events:[]}),()=>{},value=>{status=value;});
  input.emit('cancel');
  assert.equal(status,'Existing confirmation');
  assert.equal(input.getAttribute('aria-busy'),null);
});
