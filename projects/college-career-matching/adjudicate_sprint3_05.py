"""S3-05: source-grounded UNITID→Census Place candidate adjudication.

Research-only. Only approved *place identity proxies*, never latitude/longitude,
campus entrance points, ZIP delivery zones or route distances, may be exported.
Unclear or legally changing institution identities must stay unresolved.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from html import unescape
import hashlib
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from audit_sprint3_independent import main as generate_s3_04
from audit_sprint3_geography import ROOT

INPUT = ROOT / "research_work/s3_04_independent_review_queue.json"
FULL = ROOT / "research_work/s3_05_full_adjudication.json"
REGISTRY = ROOT / "research_aggregate/s3_05_approved_city_place_registry.json"
SUMMARY = ROOT / "research_aggregate/s3_05_adjudication_summary.json"
REPORT = ROOT / "S3_05_ADJUDICATION.md"

# Hand-reviewed on institution-controlled sites, 2026-10-10.
# These are the *only* records which can be eligible for a city-place proxy.
# A reproduced official-page check and independently supported Census GEOID
# are both necessary; all others fail closed. Original wording is cited.
POSITIVE = {
    "107840": {
        "institution":"Shorter College", "expected_city":"N Little Rock", "state":"AR",
        "url":"https://shortercollege.edu/contact-us-full/",
        "terms":["shorter college","604","locust","north little rock","72114"],
        "decision_note":"Official North Little Rock campus contact address; Scorecard abbreviation only.",
    },
    "150303": {
        "institution":"Tricoci University of Beauty Culture — Highland campus",
        "expected_city":"Highland","state":"IN",
        "url":"https://www.tricociuniversity.edu/contact-us/",
        "terms":["tricoci","2549","highway avenue","highland","46322"],
        "decision_note":"Institution distinguishes Highland campus; Census point-in-place selected only one same-name place.",
    },
    "170639": {
        "institution":"Lake Superior State University",
        "expected_city":"Sault Ste Marie", "state":"MI",
        "url":"https://www.lssu.edu/campus-map/",
        "terms":["lake superior state university","650","easterday","sault ste","49783"],
        "decision_note":"Official campus map and address; typographic abbreviation of Sault Ste. Marie only.",
    }
}
HOLDS = {
    "115746": {
        "decision":"hold_multiple_campuses_transition",
        "official_urls":[
            "https://www.pacifica.edu/",
            "https://www.pacifica.edu/pacificas-campus-transition/",
        ],
        "reason":"Pacifica currently lists Carpinteria Lambert and Santa Barbara Ladera locations, and a dated 2026–27 consolidation; do not force unqualified Scorecard city to one permanent Census place.",
    },
    "125897": {
        "decision":"hold_postmerger_unitid",
        "official_urls":[
            "https://www.redlands.edu/about/office-of-the-president/presidents-messages/2026/university-of-redlands-and-woodbury-university-complete-historic-merger",
            "https://woodbury.edu/about/people/directory/",
        ],
        "reason":"Redlands reports completed July 6 2026 merger; continuing institution is Redlands with former Woodbury campus now Redlands Los Angeles. The original Woodbury UNITID needs post-merger verification even though Burbank campus address remains published.",
    }
}

def page_check(url,expected):
    try:
        req=Request(url,headers={"User-Agent":"Mozilla/5.0 CollegeSearch/2026 research QA"})
        with urlopen(req,timeout=24) as response:
            final=response.geturl()
            raw=response.read(2_000_001)
            status=getattr(response,"status",200)
        if len(raw)>2_000_000:raise ValueError("oversized page")
        s=raw.decode("utf-8",errors="replace")
        s=re.sub(r"<(script|style)\b[^>]*>.*?</\1>"," ",s,flags=re.S|re.I)
        visible=re.sub(r"<[^>]+>"," ",s)
        visible=unescape(visible)
        normalized=" ".join(re.findall(r"[\w]+",visible.casefold()))
        missing=[term for term in expected
                 if " ".join(re.findall(r"[\w]+",term.casefold())) not in normalized]
        return {
            "retrieved":True,"http_status":status, "final_url":final,
            "visible_text_sha256":hashlib.sha256(visible.encode()).hexdigest(),
            "all_terms_present":not missing,"missing_terms":missing,
        }
    except Exception as e:
        return {"retrieved":False,"all_terms_present":False,"error":repr(e)[:190]}

def main():
    generate_s3_04()  # checks original census and federal IPEDS; may take time
    q=json.loads(INPUT.read_text(encoding="utf-8"))
    cases=q["cases"]
    if len(cases)!=52:raise ValueError("S3-04 ledger not 52 records")
    asof=datetime.now(timezone.utc).isoformat()
    checked={uid:page_check(src["url"],src["terms"]) for uid,src in POSITIVE.items()}
    results, approved, counts=[],[],Counter()
    for case in cases:
        uid=case["unitid"]
        official=POSITIVE.get(uid)
        note=HOLDS.get(uid)
        out={"unitid":uid,"reported_city":case["city"],"state":case["state"],
             "baseline_group":case["review_group"],"s3_04_result":case["review_status"],
             "candidate_geoids":sorted({v["geoid"] for v in case["proposed_official_places"]}),
             "review_date_utc":asof,
             "selected_geoid":None,"approved_city_place_proxy":False}
        if note:
            out.update(note)
        elif official:
            check=checked[uid]
            candidate_geoid=case["independent_geo_evidence"].get("supported_geoid")
            is_supported=(
                case["review_status"]=="census_polygon_supported_candidate"
                and isinstance(candidate_geoid,str)
                and candidate_geoid in out["candidate_geoids"]
                and official["expected_city"].casefold()==case["city"].casefold()
                and official["state"]==case["state"]
            )
            out["official_evidence"]={"url":official["url"],"fetch":check}
            if is_supported and check["all_terms_present"]:
                out["decision"]="approve_census_city_place_proxy"
                out["approved_city_place_proxy"]=True
                out["selected_geoid"]=candidate_geoid
                out["reason"]=official["decision_note"]
                approved.append({
                    "unitid":uid,"census_place_geoid":candidate_geoid,
                    "state":case["state"],"city_label":case["city"],
                    "location_scope":"Census place ID proxy; NOT verified campus coordinates",
                    "institution_name_at_review":official["institution"],
                    "official_institution_url":official["url"],
                    "official_page_text_sha256":check["visible_text_sha256"],
                    "national_scorecard_vintage":"2026-06-10",
                    "ipeds_directory_vintage":"2024",
                    "census_polygon_lookup_vintage":"Current_Current",
                    "census_gazetteer_vintage":"2026",
                    "review_date_utc":asof,
                })
            else:
                out["decision"]="hold_official_page_or_polygon_check"
                out["reason"]="No approval without independent polygon support AND current institution-controlled page text corroborating address/identity."
        elif case["review_status"]=="census_polygon_does_not_support_candidates":
            out["decision"]="reject_suggested_place_not_supported"
            out["reason"]="Official IPEDS point-in-Census-place evidence contradicts the suggested Census identity; original record remains unresolved."
        elif case["review_status"]=="no_current_ipeds_identity":
            out["decision"]="hold_missing_2024_ipeds_identity"
            out["reason"]="No matching 2024 NCES institution record; may be new branch or change of UNITID; require current legal campus identity."
        else:
            out["decision"]="hold_unverified_institutional_campus"
            out["reason"]="No independently reviewed, current institution-controlled campus identity/address source for this UNITID."
        counts[out["decision"]]+=1
        results.append(out)
    assert len(results)==52
    assert sum(counts.values())==52
    assert len({o["unitid"] for o in results})==52
    assert all(o["selected_geoid"] is None for o in results if not o["approved_city_place_proxy"])
    assert all(o["approved_city_place_proxy"] and re.fullmatch(r"\d{7}",o["census_place_geoid"]) for o in approved)
    assert not any(any(k in o for k in ("latitude","longitude","coordinates")) for o in approved)
    registry={
        "registry_type":"reviewed Census place ID proxies, not campuses",
        "created_utc":asof,
        "source_release":"2026-06-10",
        "accepted_records":len(approved),
        "records":sorted(approved,key=lambda o:o["unitid"]),
        "prohibited_uses":["road distance","campus point","ZIP deliverability","driving time",
                           "merger/closure status inferred from historical IPEDS UNITID"],
        "deployment_approved":False,
    }
    summary={
        "audit_utc":asof, "reviewed_52":52,
        "decisions":dict(sorted(counts.items())),
        "approved_city_place_proxy_count":len(approved),
        "pending_or_rejected":52-len(approved),
        "baseline_prior_city_place_matches":5659,
        "research_only_potential":5659+len(approved),
        "national_institutions_unchanged":6243,
        "remaining_original_584_unresolved_for_public_release":584,
        "not_measured":["school campus coordinate accuracy","current USPS ZIP universe",
                        "browser bundle gzip size","host LCP"],
        "all_positive_cases":{k:{"url":v["url"],"terms":v["terms"],
                                  "evidence_status":checked[k]} for k,v in POSITIVE.items()},
        "institution_identity_holds":HOLDS,
        "published_on_wordpress":False,
    }
    FULL.parent.mkdir(parents=True,exist_ok=True)
    FULL.write_text(json.dumps({"asof":asof,"cases":results},indent=2,sort_keys=True)+"\n")
    REGISTRY.parent.mkdir(parents=True,exist_ok=True)
    REGISTRY.write_text(json.dumps(registry,indent=2,sort_keys=True)+"\n")
    SUMMARY.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    lines=["# S3-05 — Adjudicated institution–Census-place identities", "",
       "**Review date:** "+asof,"",
       "**Research-only: no new coordinates, no distance control, no WordPress edits, no site release.**",
       "The input is the immutable 52-case candidate review set derived from 32 bounded"
       " aliases and 20 Census ambiguities. Source records from 2026 Census and 2024 NCES"
       " IPEDS are independently checked; institution-controlled website pages are"
       " inspected for the explicitly reviewed cases. The output registry identifies a"
       " **Census Place GEOID only**, never an address, building, latitude/longitude,"
       " accessible route or campus coordinate.", "",
       "## Decision counts", "",
       "| Adjudication | Records |","|---|---:|"]
    for key,count in sorted(counts.items()):
        lines.append("| "+key.replace("_"," ")+" | "+str(count)+" |")
    lines+=["",
      "**Approved city-place proxies:** "+str(len(approved))+" / 52 researched cases. "
      "All others carry null/unassigned Census place identity for this proposal.",
      "**Existing public baseline remains 5,659/6,243:** these review results are not "
      "deployed and cannot be added to user-facing coverage until a separate release gate.",
      "",
      "## Source-verified individual cases",""]
    for uid in POSITIVE:
        decision=next(x for x in results if x["unitid"]==uid)
        lines.append("- **UNITID "+uid+" — "+POSITIVE[uid]["institution"]+
                     ":** "+decision["decision"]+"; "+
                     "[institution-controlled page]("+POSITIVE[uid]["url"]+")"+
                     "; proposed Census place: "+
                     (decision["selected_geoid"] or "unresolved")+
                     ". "+decision.get("reason",""))
    lines+=["","## Institutional identity and multi-campus holds",""]
    for uid,record in HOLDS.items():
        decision=next(x for x in results if x["unitid"]==uid)
        lines.append("- **UNITID "+uid+":** "+record["reason"]+" "+
                    " / ".join("["+str(i+1)+"]("+url+")"
                             for i,url in enumerate(record["official_urls"]))+
                    ". Decision: "+decision["decision"]+".")
    lines+=["","## Acceptance rules and remaining work","",
        "- Approval requires a valid UNITID, consistent campus state/city, one Census"
        " place GEOID supported by IPEDS/Census point-in-place, and a contemporaneously"
        " fetched institution-controlled campus address. It does **not** validate"
        " campus coordinate precision.",
        "- Approved records are tagged as **research-only city-place identities**."
        " For any future feature, accurate campus points and current official campus"
        " identity must be reviewed independently; no driving/transit claims.",
        "- Missing census place polygons, missing historical IPEDS institutions,"
        " potential parent/branch changes, or institution mergers remain null.",
        "- Full case-by-case notes are in the restricted-to-repository-permissions"
        " GitHub Actions evidence artifact, not a public address/coordinate dump.",
        "- The official IPEDS 2025 directory should be rechecked (the previous 2025"
        " raw ZIP request failed); merger-aware identifier updates must occur"
        " before any national coverage promotion.",
        "",
        "Sources: [2026 Gazetteer](https://www.census.gov/geographies/reference-files/2026/geo/gazetter-file.html);"
        " [IPEDS directory downloads](https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx?gotoReportId=7);"
        " [Census Geocoder](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html)."]
    REPORT.write_text("\n".join(lines)+"\n")
    print("S3_05_ADJUDICATION_PASS "+json.dumps({"decisions":dict(counts),
       "approved":len(approved),"all_reviewed":len(results),
       "official_page_status":{k:v["retrieved"] for k,v in checked.items()}},sort_keys=True))

if __name__=="__main__":
    main()
