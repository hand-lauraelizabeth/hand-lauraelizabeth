'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'..','text-lens.html'),'utf8');
const script=[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map(x=>x[1]).find(s=>s.includes('function contextualSentiment'));
assert.ok(script,'Contextual sentiment code must be included in the published HTML');
test('complete Text Lens script parses',()=>assert.doesNotThrow(()=>new vm.Script(script)));
const fragment=script.slice(script.indexOf('const SC_POS='),script.indexOf('function sentimentLabel('));
const ctx={
 POS:new Set('good great excellent wonderful helpful happy better love useful clear success'.split(' ')),
 NEG:new Set('bad awful terrible confusing poor broken hate failure difficult'.split(' ')),
 NOT:new Set("not no never without hardly barely cannot isn't wasn't don't didn't doesn't won't couldn't shouldn't".split(' ')),
 WORD_RE:/[\p{L}\p{M}]+(?:['’][\p{L}\p{M}]+)*/gu,
 norm:w=>w.toLowerCase().replace(/’/g,"'"),
 esc:s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'),
 fmt:(n,p=0)=>Number(n).toFixed(p),
 sentimentLabel:(x,n)=>!n?'no cue':x>0?'positive':x<0?'negative':'mixed'
};
vm.createContext(ctx);
const segmentCode=script.slice(script.indexOf('function sentenceSegments('),script.indexOf('function median('));
vm.runInContext(segmentCode,ctx);
vm.runInContext(fragment,ctx);
const evidenceCode=script.slice(script.indexOf('function evidenceFor('),script.indexOf('function evidenceFiltered('));
ctx.sourceDocs={a:[],b:[]};
vm.runInContext(evidenceCode,ctx);
const scores=[
 ['good',s=>s.score>0],
 ['bad',s=>s.score<0],
 ['not good',s=>s.score<0&&s.negations===1],
 ['not bad',s=>s.score>0&&s.negations===1],
 ['not only good but great',s=>s.score>0],
 ['good, but terrible',s=>s.score<0&&s.contrasts===1],
 ['bad, but great',s=>s.score>0&&s.contrasts===1],
 ['slightly good',s=>s.modifiers===1],
 ['very good',s=>s.modifiers===1],
 ['good. bad.',s=>s.distribution.positive===1&&s.distribution.negative===1],
 ['ordinary table is sitting',s=>s.hits.length===0],
 ['good and bad',s=>s.distribution.mixed===1]
];
for(const [input,verify] of scores){
 test('contextual polarity: '+input,()=>assert.ok(verify(ctx.contextualSentiment(input)),input));
}
test('HTML-sensitive input is escaped in highlights',()=>{
 const src='<script>alert(1)</script> and good';
 const out=ctx.contextHighlightV6(src,ctx.contextualSentiment(src),ctx.affectAnalyze(src));
 assert.ok(out.includes('&lt;script&gt;'));assert.ok(!out.includes('<script>'));
});
test('trajectory is generated for scored multi-sentence text',()=>{
 assert.match(ctx.sentimentTrajectory(ctx.contextualSentiment('good. bad.')),/svg/);
});

test('literary foreboding, evil, and death are independently captured',()=>{
 const text='Death and evil forebodings haunted the house.';
 const a=ctx.affectAnalyze(text),s=ctx.contextualSentiment(text),highlight=ctx.contextHighlightV6(text,s,a);
 assert.ok(a.counts['Mortality & violence']>=1);
 assert.ok(a.counts['Malevolence & betrayal']>=1);
 assert.ok(a.counts['Foreboding & threat']>=1);
 assert.match(highlight,/Thematic cue/);
 assert.match(highlight,/Negative evaluative cue/);
});
test('mention of mortality does not force a negative attitude',()=>{
 const s=ctx.contextualSentiment('Death is a common topic in literature.');
 assert.equal(s.hits.length,0);
 const a=ctx.affectAnalyze('Death is a common topic in literature.');
 assert.equal(a.counts['Mortality & violence'],1);
});
test('business risk, friction and trust can be separately observed',()=>{
 const a=ctx.affectAnalyze('Users reported delays and fraud, but praised responsive support and trust.');
 assert.ok(a.counts['Customer friction']>=1);
 assert.ok(a.counts['Risk & compliance']>=1);
 assert.ok(a.counts['Trust & credibility']>=1);
 assert.ok(a.counts['Satisfaction & support']>=1);
});
test('heatmap, thematic cue cloud and panel render safely',()=>{
 const a=ctx.affectAnalyze('evil forebodings and death.');
 assert.match(ctx.affectHeatmap(a),/affect-heatmap/);
 assert.match(ctx.affectCloud(a),/affect-cloud/);
 assert.match(ctx.affectPanel({affect:a}),/Literary atmosphere/);
});

test('physical line wrapping does not imply sentence boundaries',()=>{
 const text='The evil forebodings hung over the\\nold manor without relief.\\nHe trembled at the door.'.replace(/\\n/g,'\n');
 const sentences=ctx.sentenceSegments(text);
 assert.equal(sentences.length,2);
 assert.match(sentences[0].text,/over the\nold manor/);
 assert.equal(ctx.contextualSentiment(text).sentences.length,2);
});
test('punctuation, quoted end stops and abbreviations govern boundaries',()=>{
 assert.equal(ctx.sentenceSegments('Dr. Vale spoke to Mr. Smith. The answer was clear.').length,2);
 assert.equal(ctx.sentenceSegments('“Go!” she said.\\nThen she left.'.replace(/\\n/g,'\n')).length,3);
 assert.equal(ctx.sentenceSegments('There was no full stop\\njust a line break'.replace(/\\n/g,'\n')).length,1);
});
test('source passage and positions are available for each independent cue',()=>{
 const sample='Death and evil forebodings hung\\nover the house. Grief followed.'.replace(/\\n/g,'\n');
 const result={t:sample,W:11,affect:ctx.affectAnalyze(sample),sentiment:ctx.contextualSentiment(sample)};
 const hits=ctx.evidenceFor(result,'a');
 assert.ok(hits.length>=4);
 assert.equal(hits[0].term,'Death');
 assert.equal(hits[0].char,1);
 assert.ok(hits[0].passage.includes('Death and evil'));
 assert.equal(hits.find(x=>x.term.toLowerCase()==='grief').sentence,2);
 assert.ok(hits.find(x=>x.term.toLowerCase()==='grief').line>=2);
});
test('file names, document-relative offsets and excerpt boundaries are preserved',()=>{
 const first='Death without punctuation',second='Evil forebodings. Hope returned.';
 ctx.sourceDocs.a=[{name:'chapter-one.txt',text:first},{name:'chapter-two.txt',text:second}];
 const text=first+'\n\n'+second;
 const result={t:text,W:7,affect:ctx.affectAnalyze(text),sentiment:ctx.contextualSentiment(text)};
 const hits=ctx.evidenceFor(result,'a');
 const death=hits.find(x=>x.term.toLowerCase()==='death');
 const evil=hits.find(x=>x.term.toLowerCase()==='evil');
 assert.equal(death.source,'chapter-one.txt');
 assert.equal(evil.source,'chapter-two.txt');
 assert.equal(evil.char,1);
 assert.ok(!evil.passage.includes('Death'));
 ctx.sourceDocs.a=[];
});
test('long-form punctuation segmentation supports 400000 characters',()=>{
 const text='A hard-wrapped line\\ncontinued until the ending. '.replace(/\\n/g,'\n').repeat(8200).slice(0,400000);
 assert.equal(text.length,400000);
 const segments=ctx.sentenceSegments(text);
 assert.ok(segments.length>7000);
 assert.ok(segments[0].text.includes('\n'));
 assert.ok(segments[segments.length-1].end<=400000);
});
