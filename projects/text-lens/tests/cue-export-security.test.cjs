'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const html=fs.readFileSync(path.join(__dirname,'..','text-lens.html'),'utf8');
function between(begin,end){
 const a=html.indexOf(begin),b=html.indexOf(end,a+begin.length);
 assert.ok(a>=0&&b>a,'Expected inline application functions');
 return html.slice(a,b);
}
const csvSource=between('function cueCsvRisk(value){','function exportEvidence(){');
const {cueCsvRisk,cueCsvCell}=vm.runInNewContext(csvSource+';({cueCsvRisk,cueCsvCell})');
const unsafe=[
 '=1+1','+1+1','-1+1','@SUM(1,1)',
 '＝1+1','＋1+1','－1+1','＠SUM(1)',
 "'=1+1",'"=1+1','  =1+1','\t=1+1',
 '\u200b=1+1','\u202e@foo','a\nb','a\r\nb',
 'a\u0000b','\ufeffnormal','\u2060hello','\u2028new',
 'a\u2029b','\u001b[31m','\u200djoiner','\u00adsoft-hyphen',
 ' \u00a0＝2+2','\u2066+1','\u202a@a','\u0007bell'
];
const safe=[
 'plain','a,b','quote"here',"St. John's",'ruination',
 'café','日本語','0.00','12.3','O’Brien','"quotation"',
 'space between words','emoji 😀','percent 3%','semicolon;value',
 'lineage: Hyde','evidence [a]','Greek αβγ','empty below',''
];

test('unsafe spreadsheet prefixes, controls and format characters fail closed',()=>{
 for(const raw of unsafe){
  assert.equal(cueCsvRisk(raw),true,JSON.stringify(raw));
  assert.throws(()=>cueCsvCell(raw),/Unsafe spreadsheet evidence cell/,JSON.stringify(raw));
 }
});
test('normal Unicode, quotes and delimiters retain exact values',()=>{
 for(const raw of safe){
  assert.equal(cueCsvRisk(raw),false,JSON.stringify(raw));
  const encoded=cueCsvCell(raw);
  assert.equal(encoded[0],'"');
  assert.equal(encoded.at(-1),'"');
  assert.equal(encoded.slice(1,-1).replace(/""/g,'"'),raw);
 }
});
test('source evidence cannot evade checks through quoted or whitespace prefixes',()=>{
 for(const prefix of ['',' ','  ','\u00a0',"'",'"'," '","'\""]){
  for(const sign of ['=','+','-','@','＝','＋','－','＠']){
   const raw=prefix+sign+'1+1';
   assert.equal(cueCsvRisk(raw),true,JSON.stringify(raw));
  }
 }
});
function harness(rows){
 const status={textContent:'',tabIndex:0,focused:false,focus(){this.focused=true}};
 const downloads=[];
 const env={
  cueCsvCell,evidenceFiltered:()=>rows,
  $:()=>status,
  Blob:class{constructor(parts,opts){this.parts=parts;this.opts=opts;}},
  URL:{createObjectURL(blob){downloads.push(blob);return'blob:local'},revokeObjectURL(){}},
  document:{body:{appendChild(){}},createElement(){return{href:'',download:'',click(){},remove(){}}}},
  setTimeout(){},Date,JSON
 };
 const exportSource=between('function exportEvidence(){','function evidenceJsonPayload(');
 const jsonSource=between('function evidenceJsonPayload(','let evidenceRows=[],evidencePage=0;');
 vm.runInNewContext(exportSource+';this.exportEvidence=exportEvidence',env);
 vm.runInNewContext(jsonSource+';this.evidenceJsonPayload=evidenceJsonPayload;this.downloadEvidenceJson=downloadEvidenceJson',env);
 return {env,status,downloads};
}
function row(term='ruin',source='source.txt'){
 return {side:'A',source,term,polarity:'thematic',categories:['memory'],adjustments:[],sentence:1,line:2,char:3,word:4,percent:5.5,passage:'a passage',voice:'unattributed',speaker:'',speakerMention:'',speakerStatus:'unresolved',actorRule:'none',aspect:'',aspectRule:'none',from:2,to:6};
}
test('CSV export blocks unsafe evidence, announces error and moves keyboard focus',()=>{
 for(const field of ['term','source','passage','speaker','aspect']){
  const record=row();record[field]='＝1+1';
  const {env,status,downloads}=harness([record]);
  env.exportEvidence();
  assert.equal(downloads.length,0,field);
  assert.equal(status.focused,true,field);
  assert.equal(status.tabIndex,-1,field);
  assert.match(status.textContent,/CSV export blocked/);
  assert.match(status.textContent,/JSON/);
 }
});
test('valid CSV export still works after unsafe record is removed',()=>{
 const {env,status,downloads}=harness([row()]);
 env.exportEvidence();
 assert.equal(downloads.length,1);
 assert.match(downloads[0].parts[1],/source_file/);
 assert.match(downloads[0].parts[1],/"ruin"/);
 assert.match(status.textContent,/Downloaded 1 evidence rows/);
});
test('JSON fallback preserves exact risky source fields and original positions',()=>{
 const records=[row('＝1+1','\u200barchive.csv'),row('"quoted",line','second.txt')];
 const {env,downloads}=harness(records);
 const payload=env.evidenceJsonPayload(records,'2026-10-24T00:00:00Z');
 assert.equal(payload.generated_at,'2026-10-24T00:00:00Z');
 assert.equal(payload.rows[0].term,'＝1+1');
 assert.equal(payload.rows[0].source,'\u200barchive.csv');
 assert.equal(payload.rows[0].char,3);
 assert.equal(payload.rows[1].term,'"quoted",line');
 env.downloadEvidenceJson();
 assert.equal(downloads.length,1);
 const saved=JSON.parse(downloads[0].parts.join(''));
 assert.equal(saved.rows[0].term,'＝1+1');
 assert.equal(saved.rows[0].source,'\u200barchive.csv');
 assert.equal(saved.rows[1].term,'"quoted",line');
 assert.equal(saved.rows[1].from,2);
});
test('both export controls are available and wired to the inline application',()=>{
 assert.match(html,/id="cueCsv"/);
 assert.match(html,/id="cueJson"/);
 assert.match(html,/\$\('cueCsv'\)\.onclick=exportEvidence/);
 assert.match(html,/\$\('cueJson'\)\.onclick=downloadEvidenceJson/);
 assert.match(html,/id="status" role="status" aria-live="polite"/);
});
