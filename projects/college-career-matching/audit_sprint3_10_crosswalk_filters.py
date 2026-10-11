"""S3-10 federal source-recovery and 456 extended-ID reporting-roster crosschecks.

Checks ED original file availability without inventing any raw OPEID fields.
Uses official NCES IPEDS reported-data branch rosters as a separate authoritative
crosswalk of survey reporting IDs to parent survey rosters where retrievable.
Audits only existing immutable 23-field national Scorecard projection for filters.
No site modification, automated parent assignment, or geographic inference.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
import json
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from audit_sprint3_geography import ROOT
from build_sprint2_national import build, GZIP_PATH, BUDGET_BYTES
from recover_sprint3_07 import checked_official_archive

MANIFEST=ROOT/"data/national/manifest.v1.json"
S3_09=ROOT/"research_aggregate/s3_09_identity_provenance_summary.json"
SUMMARY=ROOT/"research_aggregate/s3_10_official_roster_and_filters.json"
REPORT=ROOT/"S3_10_CROSSWALK_AND_FILTERS.md"
LEDGER=ROOT/"research_work/s3_10_456_branch_identity_ledger.json"
DOC=ROOT/"S3_10_FILTER_INVENTORY.md"
SCORECARD_URL="https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_06102026.zip"
NCES_ROSTER="https://nces.ed.gov/ipeds/reported-data/html/{unitid}?surveyNumber=1&viewmode=print&year=2024"

def fetch_publisher_roster(parent):
    url=NCES_ROSTER.format(unitid=parent)
    try:
        req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; CollegeSearch source verification/1.0)"})
        with urlopen(req,timeout=24) as response:
            raw=response.read(2_500_001)
            final=response.geturl()
        if len(raw)>2_500_000: raise ValueError("Roster page > 2.5MB")
        html=raw.decode("utf-8","replace")
        # This source may contain entire IC form; test branch-list presence separately.
        clean=re.sub(r"<(script|style)[^>]*>.*?</\1>"," ",html,flags=re.I|re.S)
        clean=unescape(re.sub(r"<[^>]*>"," ",clean))
        clean=" ".join(clean.split())
        marker=re.search(r"(Branch Campus List|Campus List)",clean,re.I)
        if not marker:
            return {"retrieved":True,"has_campus_list":False,"url":url,"final_url":final,"ids":[]}
        # The first list only: IDs must occur close after its header, before
        # survey-text repeats. Eight-digit codes alone prove roster appearance.
        segment=clean[marker.end():marker.end()+38_000]
        ends=re.search(r"(Part [A-Z] - |Institutional Characteristics (Header|Component) Summary|### Summary)",segment,re.I)
        if ends:segment=segment[:ends.start()]
        ids=sorted(set(re.findall(r"(?<!\d)\d{8}(?!\d)",segment)))
        return {"retrieved":True,"has_campus_list":True,"url":url,"final_url":final,
                "page_text_sha256":sha256(clean.encode()).hexdigest(),
                "ids":ids,"list_excerpt_sha256":sha256(segment.encode()).hexdigest()}
    except Exception as e:
        return {"retrieved":False,"has_campus_list":False,"url":url,"error":repr(e)[:190],"ids":[]}

def original_file_probe():
    req=Request(SCORECARD_URL,headers={"User-Agent":"Mozilla/5.0 CollegeSearch/1.0"},method="HEAD")
    try:
        with urlopen(req,timeout=28) as r:
            return {"url":SCORECARD_URL,"method":"HEAD","http_status":r.status,
                    "content_length":r.headers.get("Content-Length"),
                    "retrieved_full_zip":False}
    except Exception as e:
        return {"url":SCORECARD_URL,"method":"HEAD","status":"unavailable",
                "error":repr(e)[:180],"retrieved_full_zip":False}

def main():
    manifest=json.loads(MANIFEST.read_text())
    national,_,_=build()  # verify all 13 shard SHA-256
    rows=national["institutions"]
    long={k for k in rows if len(k)==8}
    assert len(rows)==6243 and len(long)==456
    national_rows={}
    metrics=Counter()
    unique=defaultdict(set)
    ctrl=Counter()
    loc=Counter()
    degrees=Counter()
    for shard in manifest["shards"]:
        path=ROOT/"data/national"/shard["file"]
        if sha256(path.read_bytes()).hexdigest()!=shard["sha256"]:raise ValueError("Source shard drift")
        for a in json.loads(path.read_text())["records"]:
            key=a[0]
            if key in national_rows:raise ValueError("duplicate Scorecard source key")
            national_rows[key]=a
            for name,val in (("name",a[1]),("city",a[2]),("state",a[3]),
               ("control",a[4]),("predominant_degree",a[5]),("highest_degree",a[6]),
               ("undergraduate_size",a[7]),("tuition_in_state",a[8]),
               ("tuition_out_state",a[9]),("annual_cost",a[10]),("net_price",a[11]),
               ("income_net_price_brackets",a[12]),("admission_rate",a[13]),
               ("sat_average",a[14]),("act_midpoint",a[15]),("locale_code",a[16]),
               ("latitude",a[17]),("longitude",a[18]),("institution_url",a[19]),
               ("academic_subject_mix",a[21] if len(a)>21 else None),
               ("accreditation_as_reported",a[22] if len(a)>22 else None)):
                usable=isinstance(val,(str,int,float)) or bool(val) if name!="income_net_price_brackets" else isinstance(val,list) and any(v is not None for v in val)
                if usable:metrics[name]+=1
                if name in ("city","state","control","locale_code","predominant_degree","highest_degree") and usable:
                    unique[name].add(str(val))
            ctrl[str(a[4])]+=1
            loc[str(a[16])]+=1
            degrees[str(a[5])]+=1
    assert len(national_rows)==6243
    assert metrics["city"]==metrics["state"]==metrics["control"]==6243
    assert metrics["undergraduate_size"]==5462
    assert metrics["annual_cost"]==5022
    assert metrics["net_price"]==5021
    assert metrics["admission_rate"]==1909
    assert metrics["sat_average"]==1037
    assert metrics["act_midpoint"]==970
    # Original projection has no school ZIP, on-campus housing, family size,
    # scholarship types, specific majors, exact campus addresses, or current travel routes.
    available_browser_fields=["name","city","state","control","locale","undergraduate_size"]
    raw_only_fields=["predominant_degree","highest_degree","tuition_in_state","tuition_out_state",
      "annual_cost","net_price","income_net_price_brackets","admission_rate",
      "sat_average","act_midpoint","academic_subject_mix","accreditation_as_reported"]
    unsupported=["school_zip","on_campus_housing","housing_capacity","family_size",
      "aid_type","exact_campus_point","driving_or_transit_distance","specific_major_offer"]

    nces,hd,errors=checked_official_archive()
    if not hd:raise RuntimeError("NCES 2025 original ZIP failed "+repr(errors))
    prev=json.loads((ROOT/"research_aggregate/s3_07_hd2025_source_recovery.json").read_text())
    assert hd["zip_sha256"]==prev["hd2025_metadata"]["zip_sha256"]
    roots=sorted({key[:6] for key in long})
    assert len(roots)==180
    assert all(root in nces for root in roots)

    receipts={}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures={pool.submit(fetch_publisher_roster,root):root for root in roots}
        for f in as_completed(futures):
            root=futures[f]
            try:receipts[root]=f.result()
            except Exception as e:receipts[root]={"retrieved":False,"has_campus_list":False,"error":repr(e)[:180],"ids":[]}

    decisions=Counter()
    by_school=[]
    for key in sorted(long):
        row=national_rows[key]
        root=key[:6]
        evidence=receipts[root]
        is_rostered=key in evidence["ids"]
        # A roster can be dated 2024 even where current campus status differs:
        # cite exactly this status, never "present/open now".
        if evidence.get("retrieved") and is_rostered:
            status="listed_as_branch_in_2024_nces_reported_data"
        elif evidence.get("retrieved") and evidence.get("has_campus_list"):
            status="not_in_2024_parent_branch_list"
        elif evidence.get("retrieved"):
            status="2024_source_page_without_roster"
        else:
            status="nces_parent_reported_data_unavailable"
        decisions[status]+=1
        by_school.append({
          "source_key":key,"source_name":row[1],"source_city":row[2],"source_state":row[3],
          "six_digit_roster_id":root,
          "official_parent_name_2025_nces":nces[root]["INSTNM"],
          "nces_2024_reported_data_url":evidence.get("url",NCES_ROSTER.format(unitid=root)),
          "source_page_retrieved":evidence.get("retrieved",False),
          "source_page_sha256":evidence.get("page_text_sha256"),
          "eight_digit_id_appears_in_2024_branch_list":is_rostered if evidence.get("retrieved") and evidence.get("has_campus_list") else None,
          "evidence_status":status,
          "authentic_2026_opeid8":None,
          "authentic_2026_opeid6":None,
          "legal_parent_link_verified":False,
          "current_campus_operation_verified":False,
          "campus_geolocation_approved":None,
        })
    assert len(by_school)==456 and sum(decisions.values())==456
    assert len({x["source_key"] for x in by_school})==456
    assert all(x["campus_geolocation_approved"] is None for x in by_school)
    probed=original_file_probe()
    now=datetime.now(timezone.utc).isoformat()
    evidence={
      "audit_utc":now,
      "scope":"NCES official 2024 survey branch roster corroboration; 2026 Scorecard OPEID is a separate unresolved source",
      "scorecard_2026_original_archive_access_check":probed,
      "scorecard_manifest_sha256":sha256(MANIFEST.read_bytes()).hexdigest(),
      "scorecard_2026_source_archive_recorded_sha256":manifest["source_archive_sha256"],
      "direct_2026_opeid6_opeid8_extracted":False,
      "nces_hd2025_zip_sha256":hd["zip_sha256"],
      "nces_2024_reporting_url_template":NCES_ROSTER,
      "extended_ids":456,
      "six_digit_roster_ids":len(roots),
      "roster_pages_retrieved":sum(bool(r.get("retrieved")) for r in receipts.values()),
      "roster_pages_with_campus_lists":sum(bool(r.get("has_campus_list")) for r in receipts.values()),
      "official_roster_evidence_counts":dict(sorted(decisions.items())),
      "recognized_2024_nces_branch_list_count":decisions["listed_as_branch_in_2024_nces_reported_data"],
      "reviewed_2026_root_opeid_links":0,
      "new_approved_federal_opeid_crosswalks":0,
      "new_campus_geocoordinates":0,
      "all_original_national_records_retained":6243,
      "existing_national_gzip_bytes":GZIP_PATH.stat().st_size,
      "existing_national_gzip_budget":BUDGET_BYTES,
      "new_browser_asset_created":False,
      "filters":{"browser":available_browser_fields,"source_shard_additional":raw_only_fields,
          "not_in_compiled_source":unsupported,
          "raw_source_nonnull_counts":dict(sorted(metrics.items())),
          "unique_city_labels":len(unique["city"]),
          "unique_state_territory_codes":len(unique["state"]),
          "ownership_codes":dict(ctrl),"raw_locale_codes":dict(loc),
          "predominant_degree_codes":dict(degrees)},
      "prohibited_claims":[
       "NCES 2024 roster membership is not a verified current/2026 campus operating status.",
       "A valid reported branch ID does not supply independently verified OPEID6/OPEID8 for 2026.",
       "No inferred college ZIP or driving distance from administrative city or Census internal point.",
       "Record key and OPEID are not interchangeable, do not use six digit truncation as legal crosswalk."
      ],
      "word_press_modified":False,
    }
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    SUMMARY.write_text(json.dumps(evidence,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    LEDGER.parent.mkdir(parents=True,exist_ok=True)
    LEDGER.write_text(json.dumps({"audited":now,"records":by_school},indent=2,sort_keys=True,ensure_ascii=False)+"\n")

    note=[
      "# S3-10 — Federal reporting-roster identity evidence and Scorecard OPEID source status",
      "",
      "**UTC audit:** "+now,
      "",
      "S3-10 preserves all 6,243 national College Scorecard projected source records and does not modify any location or WordPress page. The original June 2026 source ZIP has a pinned recorded SHA, but its raw OPEID6/OPEID8 fields are not accessible to this runner and remain null.",
      "",
      "## Direct Scorecard ZIP recovery",
      "",
      "Official source: "+SCORECARD_URL+". HTTP HEAD status: "+str(probed.get("http_status") or probed.get("error"))+
      ". A successful HEAD response is not proof of retrieved CSV data; **no 2026 OPEIDs were extracted**.",
      "",
      "## Alternative first-party federal reporting evidence",
      "",
      "NCES publishes public IPEDS Institutional Characteristics survey responses at "+NCES_ROSTER.format(unitid="135081")+
      ". These include a published **Branch Campus List** showing eight-digit branch IDs and campus names beneath a parent six-digit survey header (e.g., Keiser University). This is authoritative evidence of that reported 2024 survey-roster relationship, not proof of current 2026 legal, financial-aid or physical campus identity.",
      "",
      "- Source-hashed 2025 NCES HD2025 directory records: "+str(len(nces))+".",
      "- Distinct six-digit reporting roots across the 456 source keys: **"+str(len(roots))+"**.",
      "- Retrieved official NCES 2024 reporting pages: **"+str(evidence["roster_pages_retrieved"])+" / "+str(len(roots))+"**.",
      "- Pages with extractable explicit branch lists: **"+str(evidence["roster_pages_with_campus_lists"])+"**.",
      "",
      "| 2024 NCES branch-list verification outcome | Extended Scorecard IDs |","|---|---:|"
    ]
    for key,count in sorted(decisions.items()):
        note.append("| "+key.replace("_"," ")+" | "+str(count)+" |")
    note.extend([
      "",
      "No current OPEID6/OPEID8 mapping is accepted from a numerical prefix. The 2024 reporting roster is a different published source from the inaccessible June 2026 Scorecard OPEID fields. Every record remains unchanged.",
      "",
      "## Filter audit",
      "",
      "See [national filter field inventory](./S3_10_FILTER_INVENTORY.md), validated against all 13 SHA-pinned national Scorecard projection shards. **School ZIP is not included in this projection.** City, state, ownership and campus setting can be supported without external geography; site browser v2 already contains those fields plus undergraduate size.",
      "",
      "This research does not implement filters, changes to WordPress, browser data or distances. Full 456-record source/branch listing is retained as a 30-day CI artifact.",
      "",
      "Sources: [IPEDS reporting-unit groupings](https://nces.ed.gov/ipeds/use-the-data/institutional-groupings-in-ipeds), [NCES 2024 published Keiser survey](https://nces.ed.gov/ipeds/reported-data/html/135081?surveyNumber=1&viewmode=print&year=2024), [College Scorecard files](https://collegescorecard.ed.gov/data/).",
    ])
    REPORT.write_text("\n".join(note)+"\n")
    filter_table=[
       ("School name search","browser",metrics["name"],"Text search; distinguish name from type."),
       ("State / territory","browser",metrics["state"],"Use stated source state; 59 valid codes in national file."),
       ("City label","browser",metrics["city"],"Free text/autocomplete; city string is not a campus polygon or ZIP."),
       ("Control: public/private nonprofit/private for-profit","browser",metrics["control"],"Codes 1, 2, 3 mapped; one control per action."),
       ("Campus setting: city/suburb/town/rural","browser",6243-531,"531 unknown; exclude on chosen value, report unknown."),
       ("Undergraduate size bands","browser",metrics["undergraduate_size"],"Under 5k / 5k–14,999 / 15k+; null excluded."),
       ("Predominant degree level","source_only",metrics["predominant_degree"],"Original coded field; validate user wording and unknown values."),
       ("Highest degree level","source_only",metrics["highest_degree"],"Original coded field; not evidence all specific programs offered."),
       ("Tuition: in-state / out-of-state","source_only",metrics["tuition_in_state"],"3,601 with tuition; residency/pricing cohorts vary."),
       ("Total annual cost","source_only",metrics["annual_cost"],"Cost cohorts differ; no personalized tuition claim."),
       ("Average net price after grant aid","source_only",metrics["net_price"],"5,021 source values; not family's specific award."),
       ("Average net price by income bracket","source_only",metrics["income_net_price_brackets"],"Income brackets only; NO family-size field."),
       ("Admissions selectivity","source_only",metrics["admission_rate"],"1,909 observations; low coverage and not individual chance."),
       ("SAT / ACT average","source_only",metrics["sat_average"],"SAT 1,037; ACT 970; descriptive only."),
       ("Academic subject mix (CIP2)","source_only",metrics["academic_subject_mix"],"Broad discipline shares, not verified specific majors."),
       ("School ZIP","requires_new_source",0,"Not in 23-field projection or v2 JSON; official separate dated source needed."),
       ("Campus housing / roommates","requires_new_source",0,"Not in 23-field projection."),
       ("Family size, aid type, individualized need","requires_new_source",0,"Income net-price brackets are not family size or grants inventory."),
       ("Distance, commute, campus accessibility","requires_new_source",0,"Require campus point/accessibility evidence and disclosed metric.")
    ]
    q=["# S3-10 — Filter inventory using existing national data", "",
       "**Audit:** "+now,
       "",
       "The 6,243-source-row national projection has **23 indexed fields** across 13 SHA-verified shards; the compact browser v2 JSON includes only a subset. All counts below were computed from those shards, not guessed from documentation.",
       "",
       "| Filter | Availability | Nonmissing records | Interpretation |",
       "|---|---|---:|---|"]
    for label,src,n,caution in filter_table:
        q.append("| "+label+" | "+src.replace("_"," ")+" | "+str(n)+" | "+caution+" |")
    q.extend(["",
      "## Suggested user-facing order",
      "",
      "1. Geographic: state/territory then **city** search (not ZIP; source has no ZIP).",
      "2. Control: public, private nonprofit, private for-profit.",
      "3. Setting and size: city/suburb/town/rural and undergraduate enrollment bands.",
      "4. Additional data already compiled in original source shards: predominant/highest degree, in/out-state tuition, annual cost, income-bracket net price, admissions rate, average SAT/ACT and broad academic fields, after new v2 projection and QA.",
      "",
      "## Current behavior constraints",
      "",
      "- Keep one active filter at a time until the current working UI explicitly supports combinations.",
      "- Selecting a known value excludes null or unsupported source codes; visible results counts and unknown totals must match.",
      "- Avoid presenting national acceptance rates as probability of individual admission, or average net prices as household-specific awards.",
      "- No school ZIP, housing availability, specific major offering, legal branch relationship or road distance is derived from city labels.",
      "- No new UI, data asset, or WordPress change was made during this task.",
    ])
    DOC.write_text("\n".join(q)+"\n")
    print("S3_10_ROSTER_FILTER_AUDIT_PASS "+json.dumps({
       "roots":len(roots),"retrieved":evidence["roster_pages_retrieved"],
       "branch_match_count":evidence["recognized_2024_nces_branch_list_count"],
       "classes":dict(decisions),"controls":dict(ctrl),
       "city_count":len(unique["city"]),"zip_in_projected_data":False
    },sort_keys=True))
if __name__=="__main__":
    main()
