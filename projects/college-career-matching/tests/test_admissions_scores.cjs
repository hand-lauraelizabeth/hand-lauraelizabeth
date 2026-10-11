const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const base = path.join(__dirname, "..");
const source = fs.readFileSync(path.join(base, "college-search-sprint3-embed.js"), "utf8");
const html = fs.readFileSync(path.join(base, "college-search-sprint3.html"), "utf8");
const overlay = JSON.parse(fs.readFileSync(path.join(base, "data/sprint3/college-search-scores.v2.json"), "utf8"));
const context = {window:{}, document:{getElementById:()=>null}, Intl, Number, Object, Set};
vm.runInNewContext(source, context);
const core = context.window.CollegeSearchCore;
const school=(name,sat_avg,act_mid)=>({
    name,unitid:name,state:"NY",city:"New York",control:"public",locale:"city",
    undergraduate_size:12000,average_net_price:11000,annual_cost:23000,
    sat_avg,act_mid
});

test("national source and actual Scorecard test-score coverage",()=>{
    assert.equal(overlay.school_count,6243);
    assert.equal(overlay.source_release,"2026-06-10");
    assert.equal(overlay.school_scores.sat_avg,1037);
    assert.equal(overlay.school_scores.act_mid,970);
    assert.equal(overlay.schema_version,2);
    assert.equal(overlay.verified_band_counts.sat_complete_bands,949);
    assert.equal(overlay.verified_band_counts.act_complete_bands,920);
    assert.equal(Object.keys(overlay.institutions).length,1199);
    assert.equal(overlay.source_registry.scorecard_2026.cohort,"Fall 2024");
    for(const values of Object.values(overlay.institutions)){
        assert.equal(values.length,10);
        if(values[2]!=null) assert.ok(values[2]<=values[3]&&values[3]<=values[4]);
        if(values[5]!=null) assert.ok(values[5]<=values[6]&&values[6]<=values[7]);
        if(values[0]!=null || values[2]!=null)assert.equal(values[8],"scorecard_2026");
        if(values[1]!=null || values[5]!=null)assert.equal(values[9],"scorecard_2026");
    }
});

test("score range filters act only when non-default and exclude unknowns",()=>{
    const records=[school("A",1270,27),school("B",1410,35),school("C",null,null)];
    assert.equal(core.filterSchools(records,{}).length,3);
    assert.equal(core.filterSchools(records,{satRange:{min:1200,max:1300}}).length,1);
    assert.equal(core.filterSchools(records,{actRange:{min:30,max:36}})[0].name,"B");
    assert.equal(core.filterSchools(records,{
        satRange:{min:1100,max:1500},actRange:{min:20,max:30}
    }).length,1);
    assert.equal(core.filterSchools(records,{satRange:{min:1500,max:1600}}).length,0);
});

test("category labels require personal scores and valid complete source percentile bands",()=>{
    const r={sat_p25:1000,sat_p50:1200,sat_p75:1400,act_p25:22,act_p50:26,act_p75:31};
    assert.equal(core.admissionsCategory(r,1450,null),"SAFETY");
    assert.equal(core.admissionsCategory(r,1200,null),"TARGET");
    assert.equal(core.admissionsCategory(r,950,null),"REACH");
    assert.equal(core.admissionsCategory(r,null,32),"SAFETY");
    assert.equal(core.admissionsCategory(r,null,22),"TARGET");
    assert.equal(core.admissionsCategory(r,1450,21),null,"Disagreement never generates a label");
    assert.equal(core.admissionsCategory({...r,sat_p50:null},1450,null),null);
    assert.equal(core.admissionsCategory({...r,act_p75:null},null,32),null);
    assert.equal(core.admissionsCategory(r,null,null),null);
});

test("score inputs, defaults, coverage and prominent caveat appear in accessible HTML",()=>{
    for(const id of ["cs-sat-low","cs-sat-high","cs-act-low","cs-act-high",
        "cs-own-sat","cs-own-act","cs-admissions-note","cs-sat-unknown",
        "cs-act-unknown","cs-sat-band-unknown","cs-act-band-unknown",
        "cs-scores-status"]){
        assert.ok(html.includes('id="'+id+'"'),"Missing "+id);
    }
    assert.ok(html.includes("data-scores-src=\"./data/sprint3/college-search-scores.v2.json\""));
    assert.ok(source.includes("Test-score source:"));
    assert.ok(source.includes("sourceRegistry"));
    assert.ok(source.includes("payload.verified_band_counts"));
    assert.ok(html.includes("not concrete predictions or projections"));
    assert.ok(html.includes("TOEFL"));
    assert.ok(html.includes('id="cs-result-count"'));
    assert.ok(html.includes('id="cs-city-selected"'));
});
