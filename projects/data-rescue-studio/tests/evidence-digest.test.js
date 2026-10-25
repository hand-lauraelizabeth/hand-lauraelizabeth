'use strict';
// Synthetic-only FT-01 original-byte fingerprint and evidence regression.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createHash, webcrypto} = require('node:crypto');
const core = require('../rescue-core.js');
const reader = require('../file-reader.js');
let checks = 0;
const eq = (a,b,label) => { assert.deepEqual(a,b,label); checks++; };
const fail = async (fn,rx) => { await assert.rejects(fn,rx); checks++; };
const throws = (fn,rx) => { assert.throws(fn,rx); checks++; };
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const makeFile = (name, bytes, reportedSize=bytes.length, counter={reads:0}) => ({
 name, size:reportedSize,
 async arrayBuffer(){counter.reads++;return Uint8Array.from(bytes).buffer;}
});
(async()=>{
 const raw='\uFEFFID,Note\r\n0007,"=1+2"\r\n0008,"café\nline two"\r\n';
 const bytes=Buffer.from(raw,'utf8');
 const counter={reads:0};
 const result=await reader.readWithDigest(makeFile('synthetic.csv',bytes,bytes.length,counter),core.parseDelimited,webcrypto.subtle);
 eq(counter.reads,1,'read original file exactly once');
 eq(result.provenance.byteCount,bytes.length,'original byte length, not decoded character count');
 eq(result.provenance.sha256,sha(bytes),'independent Node SHA-256 oracle');
 eq(result.provenance.sha256.length,64,'64 lowercase hex digits');
 eq(result.parsed.headers,['ID','Note'],'BOM stripped from decoded headers only');
 eq(result.parsed.rows[0],['0007','=1+2'],'leading zero and formula-like cell preserved');
 const doc=JSON.parse(core.exportEvidenceJson(result.parsed,'synthetic.csv',result.provenance));
 eq(doc.source.byteCount,bytes.length,'source byte count in JSON');
 eq(doc.source.digestAlgorithm,'SHA-256','algorithm explicit');
 eq(doc.source.sha256,sha(bytes),'JSON hash refers to original bytes');
 eq(doc.records[1].values[1],'café\nline two','decoded multiline retained');
 eq(doc.records.map(x=>x.sourceRecord),[2,3],'logical record positions retained');
 eq(doc.schemaVersion,1,'optional metadata backwards-compatible schema version');
 const legacy=JSON.parse(core.exportEvidenceJson(result.parsed,'synthetic.csv'));
 eq('sha256' in legacy.source,false,'legacy JSON does not invent digest');
 eq('byteCount' in legacy.source,false,'legacy JSON does not invent byte count');
 const noCrypto=await reader.readWithDigest(makeFile('synthetic.csv',bytes),core.parseDelimited,null);
 eq(noCrypto.provenance,null,'no cryptography produces explicit null provenance');
 const noCryptoJson=JSON.parse(core.exportEvidenceJson(noCrypto.parsed,'synthetic.csv',noCrypto.provenance));
 eq('sha256' in noCryptoJson.source,false,'unavailable digest omitted');
 const tampered=Buffer.from(raw.replace('0007','0009'),'utf8');
 const altered=await reader.readWithDigest(makeFile('synthetic.csv',tampered),core.parseDelimited,webcrypto.subtle);
 eq(altered.provenance.sha256===result.provenance.sha256,false,'changed same-length input changes hash');
 eq(altered.provenance.byteCount,result.provenance.byteCount,'same-size changes still detected by digest');
 let hashed=0;
 const spy={digest:async()=>{hashed++;return new ArrayBuffer(32);}};
 await fail(()=>reader.readWithDigest(makeFile('synthetic.csv',bytes,bytes.length+1),core.parseDelimited,spy),/byte count changed|inconsistent/i);
 eq(hashed,0,'never hash inconsistent file bytes');
 await fail(()=>reader.readWithDigest(makeFile('synthetic.csv',Buffer.from([0xff,0xfe])),core.parseDelimited,spy),/UTF-8/);
 eq(hashed,0,'never hash invalid UTF-8 input');
 await fail(()=>reader.readWithDigest(makeFile('synthetic.csv',bytes),core.parseDelimited,{digest:async()=>new ArrayBuffer(16)}),/fingerprint was invalid/);
 const failedCrypto=await reader.readWithDigest(makeFile('synthetic.csv',bytes),core.parseDelimited,{digest:async()=>{throw Error('unsupported');}});
 eq(failedCrypto.provenance,null,'cryptography failure never fabricates digest');
 for(const provenance of [
  {sha256:'0'.repeat(63),byteCount:bytes.length},
  {sha256:'G'.repeat(64),byteCount:bytes.length},
  {sha256:'0'.repeat(64),byteCount:-1},
  {sha256:'0'.repeat(64),byteCount:5_000_001},
  {sha256:'0'.repeat(64),byteCount:1.5},
  {sha256:'0'.repeat(64)}, {byteCount:bytes.length},
  {sha256:'0'.repeat(64),byteCount:'12'},
  'not provenance', []
 ]) throws(()=>core.exportEvidenceJson(result.parsed,'synthetic.csv',provenance),/provenance/);
 const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
 eq(html.includes('DataRescueFileReader.readWithDigest(file,lib.parseDelimited)'),true,'uploaded file uses validated fingerprint reader');
 eq(html.includes('lib.exportEvidenceJson(loaded,loadedSourceName,loadedProvenance)'),true,'JSON includes matching source metadata');
 eq(html.includes('loadedProvenance=null;loadedSourceName'),true,'clear discards previous file fingerprint');
 eq(html.includes('SHA-256 fingerprint of the original bytes'),true,'user-facing byte provenance explanation');
 eq(html.includes('not establish who created the file'),true,'authenticity limitation disclosed');
 eq(html.includes('No original-byte fingerprint available.'),true,'missing crypto disclosed in export status');
 eq(html.includes('Both downloads contain your data'),true,'privacy notice preserved');
 console.log('PASS: '+checks+' original-byte SHA-256, source provenance, privacy and UI assertions.');
})().catch(e=>{console.error(e);process.exitCode=1;});
