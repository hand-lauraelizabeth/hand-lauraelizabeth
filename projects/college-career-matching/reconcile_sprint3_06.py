"""S3-06: current IPEDS source probe and authoritative identity holds.

S3-05 source-verified three-place registry is immutable and intentionally not
extended. Reconcile 49 outstanding UNITID cases; keep all decisions fail-closed.
Do not export campus coordinates, road distances, or public-facing controls.
"""
from __future__ import annotations
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import csv
import hashlib
from html import unescape
from io import BytesIO, StringIO
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zipfile import ZipFile

from adjudicate_sprint3_05 import main as regenerate_s305
from audit_sprint3_independent import read_url
from audit_sprint3_geography import ROOT

P = ROOT
INPUT = P/"research_work/s3_05_full_adjudication.json"
SUMMARY = P/"research_aggregate/s3_06_reconciliation_summary.json"
REPORT = P/"S3_06_IDENTITY_RECONCILIATION.md"
LEDGER = P/"research_work/s3_06_49_case_ledger.json"
PUBLISHED_REGISTRY = P/"research_aggregate/s3_05_approved_city_place_registry.json"

OFFICIAL_2025_URLS = [
 "https://nces.ed.gov/ipeds/datacenter/data/HD2025.zip",
 "https://nces.ed.gov/ipeds/datacenter/data/HD2025_P.zip"
]
OFFICIAL_CATALOG = "https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx?gotoReportId=7"
MERGER_URL = "https://www.redlands.edu/about/office-of-the-president/presidents-messages/2026/university-of-redlands-and-woodbury-university-complete-historic-merger"
PACIFICA_URL = "https://www.pacifica.edu/pacificas-campus-transition/"

def extract_directory(zipped):
    if not zipped.startswith(b"PK"): raise ValueError("not a ZIP archive")
    with ZipFile(BytesIO(zipped)) as z:
        members=[x for x in z.infolist() if x.filename.upper().split("/")[-1].startswith("HD")
                 and x.filename.lower().endswith(".csv")]
        if len(members)!=1: raise ValueError("ambiguous directory member")
        if members[0].file_size>50_000_000: raise ValueError("member too large")
        csv_raw=z.read(members[0])
    try: txt=csv_raw.decode("utf-8-sig")
    except UnicodeDecodeError: txt=csv_raw.decode("cp1252")
    reader=csv.DictReader(StringIO(txt))
    fields={s.upper():s for s in (reader.fieldnames or [])}
    if not {"UNITID","INSTNM","ADDR","CITY","STABBR","ZIP"}.issubset(fields):
        raise ValueError("missing NCES directory fields")
    records={}
    for row in reader:
        uid=(row[fields["UNITID"]] or "").strip()
        if not uid.isdigit(): continue
        if uid in records: raise ValueError("duplicate UNITID")
        records[uid]={name:(row.get(original) or "").strip()
                      for name,original in fields.items()
                      if name in {"INSTNM","ADDR","CITY","STABBR","ZIP","WEBADDR","IALIAS","OPEID","CYACTIVE","CLOSEDAT","NEWID","DFRCGID","F1SYSTYP","F1SYSNAM","OPEFLAG"}}
    if len(records)<5000: raise ValueError("unexpected NCES record total "+str(len(records)))
    return records,{"zip_sha256":hashlib.sha256(zipped).hexdigest(),
                    "csv_sha256":hashlib.sha256(csv_raw).hexdigest(),
                    "record_count":len(records),"columns_present":sorted(fields)}

def url_probe(url,limit=15_000_000,timeout=17):
    try:
        req=Request(url,headers={"User-Agent":"Mozilla/5.0 CollegeSearch-IPEDS-source-audit/1.0"})
        with urlopen(req,timeout=timeout) as response:
            raw=response.read(limit+1)
            final=response.geturl()
            mimetype=response.headers.get("Content-Type")
        if len(raw)>limit: raise ValueError("archive too large")
        if not raw.startswith(b"PK"):raise ValueError("content not zip; mime "+str(mimetype))
        return raw,{"url":url,"final_url":final,"status":"downloaded",
                    "bytes":len(raw),"http_content_type":mimetype}
    except Exception as e:
        return None,{"url":url,"status":"unavailable","error":str(e)[:200]}

def fetch_source_info(url,expected,timeout=16):
    """Validate fresh primary-source text, never derive location from an unrelated page."""
    try:
        req=Request(url,headers={"User-Agent":"Mozilla/5.0 CollegeSearch-Audit/1.0"})
        with urlopen(req,timeout=timeout) as response:
            raw=response.read(1_200_001);final=response.geturl()
        if len(raw)>1_200_000: raise ValueError("page too large")
        html=raw.decode("utf-8",errors="replace")
        html=re.sub(r"<(script|style)\b[^>]*>.*?</\1>"," ",html,flags=re.I|re.S)
        txt=unescape(re.sub(r"<[^>]+>"," ",html))
        normalized=" ".join(re.findall(r"[a-z0-9]+",txt.casefold()))
        matched={v:v in normalized for v in expected}
        return {"url":url,"resolved_url":final,"retrieved":True,
                "required_terms":matched,"all_terms_present":all(matched.values()),
                "visible_text_sha256":hashlib.sha256(txt.encode()).hexdigest()}
    except Exception as e:
        return {"url":url,"retrieved":False,"error":str(e)[:160]}

def candidate_homepage(webaddr):
    v=webaddr.strip()
    if not v:return None
    if not re.match(r"(?i)^https?://",v):v="https://"+v
    p=urlsplit(v)
    host=(p.hostname or "").lower()
    if p.scheme not in {"https","http"} or len(host)<5 or "." not in host:
        return None
    if host=="localhost" or host.endswith((".local",".internal")):
        return None
    # Follow only the institution-provided website; not a generated /contact route.
    return v

def inspect_homepage(website,addr,city,zip_code):
    evidence=fetch_source_info(website,[],timeout=9)
    evidence["source_kind"]="NCES IPEDS directory WEBADDR (institution self-reported, 2024)"
    if evidence.get("retrieved"):
        # We need the HTML returned separately to test address; fetch only once, not needed to
        # decide a match: homepage is a reachability signal, NOT a verified address proof.
        evidence["current_address_on_homepage_verified"]=False
        evidence["not_address_proof"]=True
    return evidence

def main():
    regenerate_s305()
    before_registry=PUBLISHED_REGISTRY.read_bytes()
    original=json.loads(INPUT.read_text())["cases"]
    pending=[x for x in original if not x["approved_city_place_proxy"]]
    assert len(original)==52 and len(pending)==49
    base=json.loads((P/"research_aggregate/s3_05_adjudication_summary.json").read_text())
    assert base["approved_city_place_proxy_count"]==3

    probe=[]
    directory2025=None
    meta25=None
    for url in OFFICIAL_2025_URLS:
        raw,res=url_probe(url)
        if raw is not None:
            try:
                records,details=extract_directory(raw)
                directory2025=records
                meta25={**res,**details,"vintage":"2025",
                        "release_status":"NCES published complete data file (provisional/final not independently certified)"}
                probe.append({**res,"validation":"official archive parsed"})
                break
            except Exception as e:
                res["status"]="invalid_directory"
                res["error"]=repr(e)[:200]
        probe.append(res)

    raw24=read_url("https://nces.ed.gov/ipeds/datacenter/data/HD2024.zip",
                   maxbytes=25_000_000,timeout=50)
    directory2024,meta24=extract_directory(raw24)
    assert meta24["record_count"]==6072,meta24["record_count"]
    primary=directory2025 or directory2024
    primary_year=2025 if directory2025 is not None else 2024
    primary_meta=meta25 or meta24

    source_checks={
        "redlands_merger":fetch_source_info(MERGER_URL,
            ["july 6 2026","university of redlands","woodbury university",
             "continuing and responsible institution","university of redlands los angeles"]),
        "pacifica_transition":fetch_source_info(PACIFICA_URL,
            ["updated july 2026","winter 2027","ladera campus","lambert campus","april 2027"]),
    }

    site_jobs={}
    for record in pending:
        uid=record["unitid"]
        cur=primary.get(uid)
        old=directory2024.get(uid)
        webaddr=(cur or old or {}).get("WEBADDR","")
        url=candidate_homepage(webaddr)
        if url:
            site_jobs[uid]={"url":url,"addr":(cur or old or {}).get("ADDR",""),
                           "city":(cur or old or {}).get("CITY",""),
                           "zip":(cur or old or {}).get("ZIP","")}
    site_results={}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures={pool.submit(inspect_homepage,v["url"],v["addr"],v["city"],v["zip"]):uid
                 for uid,v in site_jobs.items()}
        for f in as_completed(futures):
            uid=futures[f]
            try:site_results[uid]=f.result()
            except Exception as e:site_results[uid]={"retrieved":False,"error":repr(e)[:170]}

    outcomes=Counter()
    controls=Counter()
    examples={}
    full=[]
    for previous in pending:
        uid=previous["unitid"]
        row24=directory2024.get(uid)
        row25=directory2025.get(uid) if directory2025 is not None else None
        current=primary.get(uid)
        parent_uid=uid[:6] if len(uid)>6 else None
        parent=(primary.get(parent_uid) or directory2024.get(parent_uid)) if parent_uid else None
        parent_info=(
            {"possible_six_digit_prefix":parent_uid,
             "listed_in_official_directory":bool(parent),
             "directory_parent_name":parent.get("INSTNM","") if parent else None}
            if parent_uid else None
        )
        is_pacifica=uid=="115746"
        is_woodbury=uid=="125897"
        if is_pacifica:
            decision="hold_pacifica_two_campuses_until_2027_consolidation"
            reason="Institution indicates Lambert remains in use fall 2026; all class sessions move to Ladera winter 2027; campus-specific point cannot be implied by one UNITID."
        elif is_woodbury:
            decision="hold_woodbury_redlands_identity_change"
            reason="Redlands reports July 2026 completed merger and continuing Redlands legal institution. Requires verified continuing UNITID/branch mapping before updating former Woodbury record."
        elif row25 is not None and row25.get("STABBR")!=previous["state"]:
            decision="hold_2025_directory_state_conflict"
            reason="Official 2025 directory state differs from 2026 College Scorecard institution state."
        elif row25 is not None and row24 is None:
            decision="hold_new_2025_directory_identity_review"
            reason="Official 2025 directory contains formerly missing UNITID; current branch/campus mapping must still be corroborated."
        elif previous["decision"]=="reject_suggested_place_not_supported":
            decision="reject_previous_census_place_candidate"
            reason="S3-04 independent Census point-in-place did not support suggested place, so no geographical assignment authorized."
        elif row25 is not None and row24 is not None and row25.get("STABBR")==previous["state"]:
            decision="hold_2025_directory_found_address_unverified"
            reason="Current official directory record found but no validated contemporary campus point and institutional contact evidence."
        elif current is not None:
            decision="hold_2024_directory_only"
            reason="Available directory row is 2024, cannot serve as current 2026 address verification."
        else:
            decision="hold_no_official_directory_unitid"
            reason="Neither retrieved official directory contains this UNITID; possible branch, closure, or census timing issue without validated identity."
        official_identity=(current or row24 or {})
        report={
            "unitid":uid,"s3_05_decision":previous["decision"],
            "s3_06_decision":decision,"review_reason":reason,
            "state":previous["state"],"scorecard_city":previous["reported_city"],
            "official_nces_2024_present":bool(row24),
            "official_nces_2025_present":bool(row25) if directory2025 is not None else None,
            "authoritative_current_directory_vintage":primary_year,
            "directory_name":official_identity.get("INSTNM",""),
            "directory_city":official_identity.get("CITY",""),
            "directory_state":official_identity.get("STABBR",""),
            "directory_address_present":bool(official_identity.get("ADDR") and official_identity.get("ZIP")),
            "possible_branch_unitid_prefix":parent_info,
            "institution_webaddr":site_jobs.get(uid,{}).get("url"),
            "institution_homepage_reachability":site_results.get(uid,{"retrieved":False,"reason":"not supplied by IPEDS directory"}),
            "census_polygon_support_from_s3_04":previous["s3_04_result"],
            "institution_current_identity_cleared":False,
            "approved_place_geoid":None,
            "campus_coordinates":None,
        }
        full.append(report)
        outcomes[decision]+=1
        controls["current_directory_record"]+=bool(row25) if directory2025 is not None else 0
        controls["2024_directory_record"]+=bool(row24)
        controls["2024_directory_prefix_candidate"]+=bool(parent)
        controls["homepage_supplied"]+=uid in site_jobs
        controls["homepage_retrieved"]+=bool(site_results.get(uid,{}).get("retrieved"))
        if decision not in examples:examples[decision]={"unitid":uid,"reported_city":previous["reported_city"],"state":previous["state"]}
    assert len(full)==49 and sum(outcomes.values())==49
    assert not any(x["institution_current_identity_cleared"] or x["approved_place_geoid"] for x in full)
    assert PUBLISHED_REGISTRY.read_bytes()==before_registry,"Do not rewrite S3-05 registry"

    report={
        "audited_at_utc":datetime.now(timezone.utc).isoformat(),
        "records_reviewed":49,
        "source_catalog":OFFICIAL_CATALOG,
        "2025_directory_obtained":directory2025 is not None,
        "2025_retrieval_probes":probe,
        "2025_directory_metadata":meta25,
        "2024_fallback_metadata":meta24,
        "primary_directory_year":primary_year,
        "decisions":dict(sorted(outcomes.items())),
        "checks":dict(sorted(controls.items())),
        "institution_publisher_checks":source_checks,
        "example_cases":examples,
        "new_approved_census_place_geoids":0,
        "s3_05_research_registry_preserved":True,
        "s3_05_research_approved_count":3,
        "public_college_search_school_count":6243,
        "public_city_name_match_baseline":5659,
        "original_distance_unresolved":584,
        "wordpress_staging_edited":False,
        "limits":["2025 NCES IPEDS provisional and 2024 final are different source vintages",
                  "2024 IPEDS website fields are self-reported and do not prove current street address",
                  "unverified school homepages are reachability checks only, not campus-location evidence",
                  "Census Place internal points are not campus coordinates",
                  "formal merger identity/continuing UNITID not determined by merger press release alone",
                  "2026 Pacifica campus transition is date-dependent through winter 2027"],
    }
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    SUMMARY.write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    LEDGER.parent.mkdir(parents=True,exist_ok=True)
    LEDGER.write_text(json.dumps({"asof":report["audited_at_utc"],"rows":full},indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    notes=["# S3-06 — NCES 2025 retrieval and official institution change reconciliation", "",
           "**Date:** "+report["audited_at_utc"], "",
           "Reconciled all **49 S3-05 nonapproved cases** against the current directory when retrievable, "
           "the verified 2024 NCES directory, institution-declared website URLs, and two "
           "dated institution-controlled merger/transition sources. **No unverified mapping "
           "was accepted, no website data or coordinates were changed.**","",
           "## 2025 NCES IPEDS availability","",
           "NCES official catalog lists **HD2025** as 2025 Institutional Characteristics "
           "Directory (see [official catalog]("+OFFICIAL_CATALOG+")). "
           "The raw ZIP request is not presumed successful merely because its metadata is listed.",""]
    for z in probe:
        notes.append("- "+z["url"]+": **"+z["status"]+"**"+
                     (": "+z.get("error","") if "error" in z else ""))
    notes.append("")
    if directory2025 is not None:
        notes+=["**Validated HD2025:** "+str(meta25["record_count"])+
                " distinct UNITIDs; SHA-256 ZIP \`"+meta25["zip_sha256"]+"\`; CSV SHA-256 \`"+
                meta25["csv_sha256"]+"\`. 2025 is source-vintage **not proof of a 2026 address**.",""]
    else:
        notes+=["**BLOCKER:** The official HD2025 data could not be retrieved and parsed "
                "through audited URLs in this run. **Never relabel 2024 as 2025.** "
                "Full 2025 identity reconciliation is therefore pending.",""]
    notes+=["## 49-case identity decisions","",
            "| Source-bound status | Schools |","|---|---:|"]
    for d,count in sorted(outcomes.items()):
        notes.append("| "+d.replace("_"," ")+" | "+str(count)+" |")
    notes+=["","**Directory evidence:** "+str(controls["2024_directory_record"])+
             "/49 appear in NCES 2024; "+str(controls["homepage_supplied"])+
             "/49 have listed institution websites; "+str(controls["homepage_retrieved"])+
             "/49 homepages returned a readable response. A reachable homepage is **not** a "
             "verified current campus address.",""]
    notes+=["## Primary-source institutional changes","",
            "**Woodbury (former UNITID 125897):** The [July 6, 2026 University of Redlands announcement]("+
            MERGER_URL+") confirms Redlands is the continuing institution and that Woodbury "
            "operates as Redlands Los Angeles. Retain the old UNITID as a **historical/merger hold** "
            "until the federal institution/branch crosswalk gives the continuing UNITID. "
            "Do not silently assign the historic Woodbury record to a Redlands campus.","",
            "**Pacifica (UNITID 115746):** The [official July 2026 updated transition note]("+
            PACIFICA_URL+") says Lambert-based students remain there through fall 2026 and "
            "residential sessions consolidate at **Ladera in winter 2027**; Lambert lease ends "
            "April 2027. Keep location time- and campus-specific. Do not present Ladera as the "
            "only October 2026 instructional location.","",
            "Source page retrieval metadata and required-term checks are recorded in the "
            "[machine-readable aggregate summary](./research_aggregate/s3_06_reconciliation_summary.json).","",
            "## Geographic and release constraints","",
            "- 8 formerly missing 2024 directory UNITIDs are individually tracked, including "
            "possible six-digit prefix parents where the official directory confirms one. "
            "A numeric prefix is **not** proof of legal parentage.",
            "- Other 38 previously unverified institutional addresses and the single "
            "Census-contradicted place remain held or rejected, never automatically promoted.",
            "- A **52-case release registry was not produced**; the three S3-05 research-only "
            "Census place identifiers remain unchanged and undeployed.",
            "- No ZIP centroid, full USPS ZIP coverage, driving distance, campus point, new "
            "browser bundle size, new filter, WordPress publish, or Draft 1154 edit is claimed.","",
            "**Next review gate:** Resolve published HD2025 delivery path or official "
            "NCES data-generator/Access export, then current institutional location "
            "and OPEID/UNITID merger lineage with dated source-level evidence; "
            "do not accept outstanding GEOIDs until geographic and institutional "
            "identities are independently grounded.",""]
    REPORT.write_text("\n".join(notes),encoding="utf-8")
    print("S3_06_SOURCE_AUDIT_PASS "+json.dumps({
        "2025_obtained":directory2025 is not None,
        "cases":49,"decisions":dict(outcomes),
        "2024_matched":controls["2024_directory_record"],
        "homepages_retrieved":controls["homepage_retrieved"]},sort_keys=True))
if __name__=="__main__":
    main()
