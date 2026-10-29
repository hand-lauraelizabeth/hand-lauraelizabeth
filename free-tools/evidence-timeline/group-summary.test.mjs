import assert from 'node:assert/strict';
import {formatGroupSummary,MAX_PREVIEW_GROUPS,MAX_PREVIEW_SOURCE_IDS} from './group-summary.mjs';
let n=0;
const check=(value,label)=>{assert.ok(value,label);n++;};
check(MAX_PREVIEW_GROUPS===8,'bounded groups');
check(MAX_PREVIEW_SOURCE_IDS===3,'bounded source IDs');
check(formatGroupSummary([])==='No related-record groups to review.','empty');
const one=formatGroupSummary([{group:'café',sourceIds:['0001','0002']}]);
check(one.includes('1 related-record group'),'singular group');
check(one.includes('"0001", "0002"'),'leading zero identifiers');
check(one.includes('exact JSON exports'),'full JSON evidence');
const groups=Array.from({length:5000},(_,i)=>({group:'group-'+i,sourceIds:['A'+i,'B'+i]}));
const old=groups.map(g=>'Review group '+g.group+': '+g.sourceIds.join(', ')).join(' · ');
const short=formatGroupSummary(groups);
check(old.length>150000,'old preview unbounded negative control');
check(short.length<2500,'new preview bounded');
check(short.includes('5000 related-record groups'),'accurate group count');
check(short.includes('4992 additional groups not shown'),'explicit omitted groups');
check(short.includes('group-7')&&!short.includes('group-8'),'only first eight shown');
check(short.includes('Search by group label'),'path to hidden groups');
check(short.includes('spreadsheet CSV is available only'),'CSV safety caveat');
const many=formatGroupSummary([{group:'café',sourceIds:['001','002','003','004','005']}]);
check(many.includes('5 records'),'full group size');
check(many.includes('2 additional source IDs not shown'),'omitted ID count');
check(!many.includes('"004"'),'source ID cap');
const hostile=formatGroupSummary([{group:'<img src=x onerror=alert(1)>\u202e',sourceIds:['ID\u200bX','ID"\\Y']}]);
check(hostile.includes('<img src=x onerror=alert(1)>\\u202e'),'directional override visible');
check(hostile.includes('ID\\u200bX'),'zero-width escape visible');
check(hostile.includes('ID\\"\\\\Y'),'quote and slash visible');
const original=JSON.stringify(groups);formatGroupSummary(groups);
check(JSON.stringify(groups)===original,'no mutation');
for(const invalid of [null,{},Array.from({length:5001},()=>({group:'x',sourceIds:['1','2']})),
 [{group:'x',sourceIds:['1']}],[{group:'x',sourceIds:[null,'2']}],[{group:null,sourceIds:['1','2']}]]) {
 assert.throws(()=>formatGroupSummary(invalid),/Invalid group summary/);n++;
}
const rows=Array.from({length:10000},(_,i)=>({sourceId:String(i).padStart(5,'0'),group:'g'+Math.floor(i/2)}));
const byGroup=new Map();
for(const row of rows){const ids=byGroup.get(row.group)||[];ids.push(row.sourceId);byGroup.set(row.group,ids);}
const result=formatGroupSummary([...byGroup].map(([group,sourceIds])=>({group,sourceIds})));
check(result.length<2500,'10k record summary bounded');
check(result.includes('5000 related-record groups'),'10k group accounting');

const longGroup='🧪'+'L'.repeat(118); // 120 UTF-16 units, within import limit
const longId='0'.repeat(120);
const oversizedPreview=formatGroupSummary([{group:longGroup,sourceIds:[longId,'keep-002']}]);
check(oversizedPreview.includes('"🧪'+'L'.repeat(47)+'"'),'astral code point preserved at preview boundary');
check(oversizedPreview.includes('71 additional characters not shown'),'group omitted code point count');
check(oversizedPreview.includes('72 additional characters not shown'),'ID omitted code point count');
check(!oversizedPreview.includes(longGroup)&&!oversizedPreview.includes(longId),'full long fields absent from preview');
check(oversizedPreview.includes('"keep-002"'),'short exact IDs remain unchanged');
check(longGroup.length===120&&longId.length===120,'fixtures respect import field limits');
const longGroups=Array.from({length:8},(_,i)=>({group:'G'.repeat(120),sourceIds:['A'.repeat(120),'B'.repeat(120),'C'.repeat(120),'D'.repeat(120)]}));
const boundedLong=formatGroupSummary(longGroups);
check(boundedLong.length<4000,'maximum visible groups with long fields stay bounded');
check(boundedLong.includes('1 additional source IDs not shown'),'source count unaffected');
check(longGroups[0].group.length===120&&longGroups[0].sourceIds[0].length===120,'input strings unmodified');
const boundary=formatGroupSummary([{group:'Q'.repeat(47)+'\u202e'+'Z'.repeat(72),sourceIds:['S1','S2']}]);
check(boundary.includes('\\u202e'),'control at preview boundary remains visible');

// Default-ignorable characters can make different exact identifiers look alike.
// The preview must reveal them without modifying source IDs or evidence.
const invisibleRows=[{group:'lab\u034f\ufe0f\u{e0100}\u206f',sourceIds:['A\u3164\u115f','B']}];
const invisibleBefore=JSON.stringify(invisibleRows);
const invisiblePreview=formatGroupSummary(invisibleRows);
for(const escaped of ['\\u034f','\\ufe0f','\\u{e0100}','\\u206f','\\u3164','\\u115f'])
  check(invisiblePreview.includes(escaped),'preview reveals '+escaped);
check(!invisiblePreview.includes(invisibleRows[0].group),'raw invisible group not rendered in preview');
check(!invisiblePreview.includes(invisibleRows[0].sourceIds[0]),'raw invisible identifier not rendered in preview');
check(JSON.stringify(invisibleRows)===invisibleBefore,'original default-ignorable source data remains exact');
check(invisiblePreview.length<1200,'escaped invisible preview stays bounded');

console.log('PASS: '+n+' bounded group-summary assertions; baseline '+old.length+' chars, fixed '+short.length+' chars');
