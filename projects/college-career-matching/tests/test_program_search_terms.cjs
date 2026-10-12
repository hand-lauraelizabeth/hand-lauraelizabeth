const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const dir=path.join(__dirname,"../data/programs/ipeds2025");
const registry=JSON.parse(fs.readFileSync(path.join(dir,"program-search-terms.v1.json"),"utf8"));
const titles=JSON.parse(fs.readFileSync(path.join(dir,"cip2020-titles.json"),"utf8"));
test("Plain-language terms are versioned and reference only official 2020 CIP6 classifications",()=>{
 assert.equal(registry.schema_version,"1.0");
 assert.equal(registry.official_taxonomy_url,"https://nces.ed.gov/ipeds/cipcode/Files/CIPCode2020.csv");
 assert.ok(registry.authority.includes("not evidence of current availability"));
 const entries=Object.entries(registry.terms_by_cip);
 assert.equal(entries.length,88);
 let terms=0;
 for(const [code,item] of entries){
  assert.match(code,/^\d{6}$/);
  assert.ok(titles[code],"Unknown official CIP title: "+code);
  assert.ok(Array.isArray(item.aliases)&&item.aliases.length>0);
  for(const term of [...item.aliases,...(item.related||[])]){
   assert.equal(typeof term,"string");
   assert.ok(term.length>0 && term.length<120);
   assert.ok(!/[<>]/.test(term),"No HTML in searchable terms");
   terms++;
  }
 }
 assert.equal(terms,322);
});
test("Common major concepts include both abbreviations and an explicit related category",()=>{
 const m=registry.terms_by_cip;
 for(const [code,word] of [["513801","BSN"],["513901","LPN"],["110701","compsci"],["110201","coding"],["111003","cybersecurity"],["521001","HR"],["520201","MBA"],["220302","paralegal"]]){
  assert.ok(m[code].aliases.some(a=>a.toLowerCase()===word.toLowerCase()),code+" "+word);
 }
 assert.ok(m["110801"].related.includes("UX design"));
 assert.ok(m["500409"].related.includes("UX design"));
 assert.ok(m["513801"].related.includes("patient care"));
});
