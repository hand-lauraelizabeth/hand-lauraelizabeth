"""S3-07 official NCES HD2025 source recovery and 49-case institution identity audit.

No dependency on live Census geocoding: S3-05's approved place identities and
S3-03's source-pinned candidates are reused, not re-adjudicated.
No campus points or WordPress changes.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import re

from audit_sprint3_identity import run as regenerate_official_name_candidates
from audit_sprint3_geography import ROOT
from reconcile_sprint3_06 import extract_directory, url_probe, read_url

OFFICIAL_ZIP = "https://nces.ed.gov/ipeds/complete-data-files/HD2025.zip"
CATALOG = "https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx?gotoReportId=7"
PREVIOUS_BAD_URLS = [
 "https://nces.ed.gov/ipeds/datacenter/data/HD2025.zip",
 "https://nces.ed.gov/ipeds/datacenter/data/HD2025_P.zip",
]
RESULT = ROOT / "research_aggregate/s3_07_hd2025_source_recovery.json"
NOTES = ROOT / "S3_07_IPEDS_RECOVERY.md"
QUEUE = ROOT / "research_work/s3_07_49_case_comparison.json"
PRIOR_REGISTRY = ROOT / "research_aggregate/s3_05_approved_city_place_registry.json"
PRIOR_S3_06 = ROOT / "research_aggregate/s3_06_reconciliation_summary.json"

def load_cases():
    regenerate_official_name_candidates()  # SHA-pins the Census Place archive and 6,243 Scorecard rows.
    base = json.loads((ROOT / "research_work/s3_03_review_queue.json").read_text())["items"]
    proposed = []
    for row in base:
        if row["baseline_category"] == "ambiguous_place_name":
            proposed.append(row)
        else:
            opts = {x["geoid"] for sub in row.get("probes",{}).values() for x in sub}
            if len(opts) == 1:
                proposed.append(row)
    assert len(proposed)==52, len(proposed)
    regbytes = PRIOR_REGISTRY.read_bytes()
    registry = json.loads(regbytes)
    assert registry["accepted_records"] == 3 and not registry["deployment_approved"]
    approved_ids = {x["unitid"] for x in registry["records"]}
    assert len(approved_ids) == 3
    assert approved_ids.issubset({row["unitid"] for row in proposed})
    cases=[x for x in proposed if x["unitid"] not in approved_ids]
    assert len(cases)==49 and len({c["unitid"] for c in cases})==49
    return cases,regbytes

def checked_official_archive():
    zipraw,probe = url_probe(OFFICIAL_ZIP,limit=25_000_000,timeout=65)
    if zipraw is None:
        return None,None,[probe]
    try:
        data,metadata=extract_directory(zipraw)
        metadata.update({
            "url":OFFICIAL_ZIP,"final_url":probe.get("final_url"),
            "bytes":probe.get("bytes"),"vintage":"2025",
            "release_designation":"2025 provisional 2025–26 institutional directory; confirm against NCES release memo",
        })
        return data,metadata,[{**probe,"validation":"original NCES hosted ZIP and required schema checked"}]
    except Exception as e:
        return None,None,[{**probe,"validation":"invalid archive or schema","error":repr(e)[:190]}]

def source_directory_2024():
    url="https://nces.ed.gov/ipeds/datacenter/data/HD2024.zip"
    raw=read_url(url,maxbytes=25_000_000,timeout=55)
    directory,details=extract_directory(raw)
    assert details["record_count"]==6072,details["record_count"]
    # independent S3-04 source pin
    assert details["zip_sha256"]=="d98425c123d7c0e872aec6e83960dfb501884818bf17385c340790f3d1f28345"
    return directory,details

def main():
    cases,registry_bytes = load_cases()
    directory25,meta25,attempts=checked_official_archive()
    directory24,meta24=source_directory_2024()
    previous=json.loads(PRIOR_S3_06.read_text())
    assert previous["records_reviewed"]==49
    group_counts=Counter()
    older_group_counts=defaultdict(Counter)
    field_changes=Counter()
    decisions=Counter()
    example_differences=[]
    results=[]
    for case in cases:
        uid=case["unitid"]
        old=directory24.get(uid)
        new=directory25.get(uid) if directory25 is not None else None
        if directory25 is None:
            group="no_2025_source"
        elif old and new:
            group="present_both"
        elif new and not old:
            group="new_in_2025_directory"
        elif old and not new:
            group="absent_from_2025_directory"
        else:
            group="missing_both"
        group_counts[group]+=1
        older_group_counts[case["baseline_category"]][group]+=1
        names_changed=bool(old and new and old.get("INSTNM","")!=new.get("INSTNM",""))
        cities_changed=bool(old and new and old.get("CITY","")!=new.get("CITY",""))
        states_changed=bool(old and new and old.get("STABBR","")!=new.get("STABBR",""))
        if names_changed:field_changes["name_changed"]+=1
        if cities_changed:field_changes["city_changed"]+=1
        if states_changed:field_changes["state_changed"]+=1
        parent=uid[:6] if len(uid)>6 else None
        has_parent=bool(parent and (directory25 or {}).get(parent))
        if parent:field_changes["long_unitid_with_six_digit_prefix"]+=1
        if has_parent:field_changes["six_digit_prefix_also_reported_in_2025"]+=1

        # Merger/transition cases always fail closed, regardless of directory membership.
        if uid=="125897":
            decision="hold_woodbury_merger_continuing_unitid"
        elif uid=="115746":
            decision="hold_pacifica_campus_transition"
        elif uid=="491923":
            decision="reject_unsupported_census_place_candidate"
        elif directory25 is None:
            decision="hold_hd2025_source_unavailable"
        elif new is None:
            decision="hold_missing_2025_directory_identity"
        elif states_changed or new.get("STABBR","")!=case["state"]:
            decision="hold_state_or_location_record_conflict"
        else:
            decision="hold_2025_directory_record_campus_unverified"
        decisions[decision]+=1
        if (names_changed or cities_changed or states_changed or group!="present_both") and len(example_differences)<25:
            example_differences.append({
                "unitid":uid,"2024_name":old.get("INSTNM") if old else None,
                "2025_name":new.get("INSTNM") if new else None,
                "2024_city":old.get("CITY") if old else None,
                "2025_city":new.get("CITY") if new else None,
                "year_group":group,
            })
        results.append({
            "unitid":uid, "state":case["state"],"scorecard_city":case["city"],
            "source_name_2024":old.get("INSTNM") if old else None,
            "source_name_2025":new.get("INSTNM") if new else None,
            "source_city_2024":old.get("CITY") if old else None,
            "source_city_2025":new.get("CITY") if new else None,
            "source_state_2025":new.get("STABBR") if new else None,
            "source_zip_2025":new.get("ZIP") if new else None,
            "year_group":group,
            "s3_07_decision":decision,
            "possible_six_digit_unitid_prefix":parent,
            "prefix_exists_2025":has_parent,
            "reviewed_census_geoid":None,
            "campus_coordinate":None,
            "location_approved_for_public_release":False,
        })
    assert len(results)==49 and sum(group_counts.values())==49
    assert sum(decisions.values())==49
    assert PRIOR_REGISTRY.read_bytes()==registry_bytes
    now=datetime.now(timezone.utc).isoformat()
    evidence={
        "audited_utc":now,
        "official_nces_catalog":CATALOG,
        "official_hd2025_file_url":OFFICIAL_ZIP,
        "official_hd2025_retrieved":directory25 is not None,
        "official_source_probe":attempts,
        "hd2025_metadata":meta25,
        "hd2024_metadata":meta24,
        "records_compared":49,
        "cross_year_unitid_membership":dict(sorted(group_counts.items())),
        "by_s3_03_original_category":{k:dict(sorted(v.items())) for k,v in sorted(older_group_counts.items())},
        "record_field_change_counts":dict(sorted(field_changes.items())),
        "decision_counts":dict(sorted(decisions.items())),
        "source_identity_examples":example_differences,
        "new_location_approvals":0,
        "s3_05_research_registry_unchanged":True,
        "prior_research_only_census_place_identifiers":3,
        "original_unresolved_for_location_release":584,
        "existing_city_label_match_baseline":5659,
        "total_college_institutions":6243,
        "public_deployment_authorized":False,
        "constraints":[
            "Presence of a UNITID in IPEDS 2025 is not proof of current campus building, closure/merger legal identity, or exact address.",
            "Any 2025 release is provisional and may include imputation; release vintage is separate from current 2026 street-address verification.",
            "A 6-digit prefix shared by UNITIDs is not evidence of legal parent-child lineage.",
            "Woodbury July 2026 merger and Pacifica fall 2026/winter 2027 campus transition retain explicit holds.",
            "Census internal points are not campus coordinates or routing/geographic accessibility metrics.",
        ],
    }
    RESULT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(evidence,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    QUEUE.parent.mkdir(parents=True,exist_ok=True)
    QUEUE.write_text(json.dumps({"audited_utc":now,"cases":results},indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    doc=[
        "# S3-07 — Official NCES HD2025 source recovery and 49-case comparison","",
        "**Audited (UTC):** "+now,"",
        "**Research only.** Source records and case decisions are not campus geocodes, ZIP coverage, driving distances, or authorization to change WordPress.","",
        "## Official NCES source and provenance","",
        "- [NCES Complete Data Files catalog]("+CATALOG+")",
        "- Official HD2025 ZIP URL: "+OFFICIAL_ZIP,
    ]
    if meta25:
        doc += [
            "- **Verified authentic NCES hosted ZIP**; "+str(meta25["record_count"])+" unique official 2025 UNITIDs.",
            "- ZIP SHA-256: \x60"+meta25["zip_sha256"]+"\x60",
            "- extracted CSV SHA-256: \x60"+meta25["csv_sha256"]+"\x60",
            "- archive byte size: "+str(meta25["bytes"]),
            "- release caveat: 2025–26 provisional institutional directory; not an October 2026 campus registry.",
        ]
    else:
        doc += [
            "- **Not recovered.** Official source request/ZIP/schema failed; reason recorded in source-probe JSON. No 2024 record was mislabeled as 2025.",
        ]
    doc += ["",
        "2024 control archive: SHA-256 \x60"+meta24["zip_sha256"]+"\x60, "+str(meta24["record_count"])+" unique UNITIDs.",
        "The earlier guessed /ipeds/datacenter/data/HD2025.zip and HD2025_P.zip endpoints returned HTTP 404; S3-07 tests the publisher's /ipeds/complete-data-files/ distribution instead.","",
        "## Source-year reconciliation for the 49 unresolved S3-05 cases","",
        "| Comparison result | Schools |", "|---|---:|",
    ]
    for name,count in sorted(group_counts.items()):
        doc.append("| "+name.replace("_"," ")+" | "+str(count)+" |")
    doc+=["","Differences in names: "+str(field_changes["name_changed"])+
        "; differences in city: "+str(field_changes["city_changed"])+
        "; differences in state: "+str(field_changes["state_changed"])+".",
        "Neither missing entries nor name changes prove a closure or merger. All changes require publisher identity evidence.",
        "",
        "## Pending dispositions","",
        "| Disposition | Records |", "|---|---:|"]
    for decision,count in sorted(decisions.items()):
        doc.append("| "+decision.replace("_"," ")+" | "+str(count)+" |")
    doc += ["",
        "Woodbury (UNITID 125897) remains on an explicit post-merger identity hold; Pacifica (115746) remains on a two-campus transition hold; the previous unsupported Census place candidate (491923) stays rejected.",
        "All new location approvals: **0**. Existing 3 research-only Census place IDs are unchanged. Baseline 5,659/6,243 school-city matches and 584 outstanding location-release uncertainties are unchanged.",
        "",
        "Complete 49-case comparison, including names, source-year city/state, and potential six-digit UNITID prefixes, is retained as a 30-day GitHub Actions artifact governed by repository access.",
        "",
        "## Separate release gates","",
        "Current institutional/campus identity and addresses require current institution-controlled sources and verified parent/branch reporting; 2025 IPEDS alone is not campus geolocation. Future ZIP features must separately verify current USPS coverage, Census ZCTA precision, browser gzip budget, and physical-device/mobile QA.",
        "No WordPress edits or deployable distance feature were made.",
        "",
        "Publisher references: [NCES IPEDS](https://nces.ed.gov/ipeds), [Data Center complete files]("+CATALOG+"), [official archive]("+OFFICIAL_ZIP+"), [Woodbury/Redlands merger](https://www.redlands.edu/about/office-of-the-president/presidents-messages/2026/university-of-redlands-and-woodbury-university-complete-historic-merger), [Pacifica transition](https://www.pacifica.edu/pacificas-campus-transition/).",
    ]
    NOTES.write_text("\n".join(doc)+"\n",encoding="utf-8")
    print("S3_07_SOURCE_AUDIT_PASS "+json.dumps({
        "recovered":directory25 is not None,
        "hd2025_records":meta25["record_count"] if meta25 else None,
        "comparisons":dict(group_counts),
        "decisions":dict(decisions),
        "new_location_approvals":0,
    },sort_keys=True))

if __name__=="__main__":
    main()
