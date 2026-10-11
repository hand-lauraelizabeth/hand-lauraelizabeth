"""S3-09: original College Scorecard 2026 provenance of all 456 long UNITID values.

Research only. Preserve 6243 source rows, do not conflate Scorecard UNITID
with NCES UNITID, federal OPEID, a legal branch or a physical campus.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
from io import BytesIO, TextIOWrapper
import csv
import gzip
import hashlib
import json
from urllib.request import Request, urlopen
from zipfile import ZipFile

from audit_sprint3_geography import ROOT
from recover_sprint3_07 import checked_official_archive
from build_sprint2_national import build, JSON_PATH, GZIP_PATH, BUDGET_BYTES

BASE = ROOT / "research_aggregate"
SUMMARY = BASE / "s3_09_identity_provenance_summary.json"
LEDGER = ROOT / "research_work/s3_09_all_456_id_ledger.json"
REPORT = ROOT / "S3_09_SOURCE_IDENTITY_REPORT.md"
SCHEMA = ROOT / "S3_09_IDENTIFIER_SCHEMA.md"
MANIFEST = ROOT / "data/national/manifest.v1.json"

def original_scorecard_archive(manifest):
    url=manifest["source_archive_url"]
    expected=manifest["source_archive_sha256"]
    if url!="https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_06102026.zip":
        raise ValueError("Unexpected Scorecard archive URL")
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 CollegeSearch-S3-09 source-provenance/1.0"})
    with urlopen(req,timeout=110) as response:
        raw=response.read(50_000_001)
        final=response.geturl()
    if len(raw)>50_000_000: raise ValueError("Oversized source archive")
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=expected: raise RuntimeError("S3-09 source ZIP SHA drift, refusing to classify")
    if not raw.startswith(b"PK"): raise ValueError("Not a ZIP archive")
    return raw,{"original_url":url,"final_url":final,"zip_bytes":len(raw),"sha256":sha}

def get_source_rows(raw,expected_keys):
    with ZipFile(BytesIO(raw)) as z:
        candidates=[f for f in z.infolist() if f.filename.lower().endswith(".csv") and not f.is_dir()]
        if len(candidates)!=1:raise RuntimeError("Expected single Scorecard CSV "+repr([f.filename for f in candidates]))
        member=candidates[0]
        with z.open(member) as f:
            file=TextIOWrapper(f,encoding="utf-8-sig",errors="replace",newline="")
            csv.field_size_limit(80_000_000)
            reader=csv.DictReader(file)
            fields={h.upper():h for h in reader.fieldnames or []}
            required={"UNITID","OPEID","OPEID6","INSTNM","CITY","STABBR","CURROPER"}
            if not required.issubset(fields):
                raise RuntimeError("Source missing columns "+repr(required-set(fields)))
            rows={}
            stats=Counter()
            for rec in reader:
                stats["source_rows"]+=1
                uid=(rec.get(fields["UNITID"]) or "").strip()
                if not uid.isdigit(): stats["non_numeric_source_unitid"]+=1;continue
                if len(uid)==8:stats["source_eight_digit_rows"]+=1
                operating=(rec.get(fields["CURROPER"]) or "").strip()
                if operating=="1":stats["operating_source_rows"]+=1
                if uid not in expected_keys: continue
                if uid in rows:raise RuntimeError("Duplicate source Scorecard UNITID: "+uid)
                rows[uid]={
                   "unitid":uid,"opeid":(rec.get(fields["OPEID"]) or "").strip(),
                   "opeid6":(rec.get(fields["OPEID6"]) or "").strip(),
                   "name":(rec.get(fields["INSTNM"]) or "").strip(),
                   "city":(rec.get(fields["CITY"]) or "").strip(),
                   "state":(rec.get(fields["STABBR"]) or "").strip(),
                   "operating":operating}
            stats["matched_source_keys"]=len(rows)
            stats["csv_columns"]=len(fields)
            stats["source_csv_uncompressed_bytes"]=member.file_size
            stats["source_csv_name"]=member.filename
    return rows,dict(stats)

def fixed(value,digits):
    return value if value.isdigit() and len(value)==digits else None

def main():
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    rebuilt,_,_=build()  # independently SHA validates 13 immutable Scorecard projection shards
    national=json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if rebuilt!=national:raise RuntimeError("Source shard reconstruction differs from committed JSON")
    if gzip.decompress(GZIP_PATH.read_bytes())!=JSON_PATH.read_bytes():raise RuntimeError("gzip roundtrip differs")
    if GZIP_PATH.stat().st_size>BUDGET_BYTES:raise RuntimeError("Current browser gzip over 750 KiB")
    schools=national["institutions"]
    short={k for k in schools if len(k)==6}
    extended={k for k in schools if len(k)==8}
    assert len(schools)==6243 and len(short)==5787 and len(extended)==456
    assert all(k.isdigit() for k in schools)

    original=None
    source={"manifest_url":manifest["source_archive_url"],
            "recorded_source_archive_sha256":manifest["source_archive_sha256"],
            "verified_directly_this_run":False}
    stats={"raw_source_csv_rows_verified_this_run":None}
    try:
        data,source_check=original_scorecard_archive(manifest)
        original,stats=get_source_rows(data,set(schools))
        if len(original)!=6243:raise RuntimeError("Original CSV does not contain every national key")
        wrong=[k for k,v in schools.items()
               if original[k]["name"]!=v["name"] or original[k]["city"]!=v["city"]
               or original[k]["state"]!=v["state"] or original[k]["operating"]!="1"]
        if wrong:raise RuntimeError("Original CSV identity differs: "+repr(wrong[:10]))
        assert stats["source_rows"]==6273 and stats["operating_source_rows"]==6243
        source.update(source_check)
        source["verified_directly_this_run"]=True
    except (TimeoutError, ConnectionError, OSError) as e:
        # Error 403 from ED CDN is a retrieval blocker, not a license to substitute a
        # third-party derivative or to state the original UNITID/OPEID columns were read.
        source["unavailable_error"]=type(e).__name__+": "+str(e)[:180]
        original=None
    # Source-shard ID provenance is verified via local SHA-256, but does not expose
    # original OPEID6 or OPEID8. Nulls mean unknown, NOT proof no OPEID exists.
    if original is None:
        original={k:{"unitid":k,"opeid":"","opeid6":"",
                     "name":v["name"],"city":v["city"],"state":v["state"],
                     "operating":"1"} for k,v in schools.items()}
    exact_raw_identity_verified=bool(source["verified_directly_this_run"])

    nces,meta,probes=checked_official_archive()
    if not meta:raise RuntimeError("NCES 2025 source inaccessible "+repr(probes))
    prev=json.loads((BASE/"s3_07_hd2025_source_recovery.json").read_text())
    if meta["zip_sha256"]!=prev["hd2025_metadata"]["zip_sha256"]:
        raise RuntimeError("Official NCES 2025 source ZIP SHA drift")

    classes=Counter()
    states=defaultdict(Counter)
    prefixes=Counter()
    details=[]
    source_opeid_equal=0
    for key in sorted(extended):
        row=original[key]
        prefix=key[:6]
        is_in_scorecard=prefix in short
        is_in_nces=prefix in nces
        ope8=fixed(row["opeid"],8) if exact_raw_identity_verified else None
        ope6=fixed(row["opeid6"],6) if exact_raw_identity_verified else None
        shared_opeid6=bool(ope6 and prefix in original
                          and fixed(original[prefix]["opeid6"],6)==ope6)
        if is_in_scorecard and is_in_nces and shared_opeid6:
            category="scorecard_and_nces_prefix_with_original_scorecard_opeid6_shared"
        elif is_in_scorecard and is_in_nces:
            category="scorecard_and_nces_prefix_observed_opeid_relationship_unverified"
        elif is_in_scorecard:
            category="scorecard_prefix_only"
        elif is_in_nces:
            category="nces_prefix_only"
        else:
            category="prefix_not_observed_in_either"
        classes[category]+=1
        states[row["state"]][category]+=1
        prefixes[prefix]+=1
        if ope8==key:source_opeid_equal+=1
        if key in nces:raise RuntimeError("Eight-digit ID unexpectedly in 2025 six-digit NCES UNITID universe")
        details.append({
            "record_key":key,
            "source_field_in_manifest":"unitid",
            "source_id_classification":"scorecard_2026_projected_extended_8_digit_key",
            "name":row["name"],"city":row["city"],"state":row["state"],
            "source_opeid8":ope8,"source_opeid6":ope6,
            "source_opeids_directly_verified":exact_raw_identity_verified,
            "numeric_prefix":prefix,
            "prefix_in_national_scorecard":is_in_scorecard,
            "prefix_in_2025_nces_ipeds":is_in_nces,
            "raw_opeid6_shared_with_prefix":shared_opeid6 if exact_raw_identity_verified else None,
            "evidence_class":category,
            "official_ipeds_unitid_of_this_extended_record":None,
            "legal_parent_unitid":None,"approved_campus_point":None,
            "approved_census_place_geoid":None,
        })
    assert len(details)==456 and sum(classes.values())==456
    assert len({x["record_key"] for x in details})==456
    assert all(x["official_ipeds_unitid_of_this_extended_record"] is None for x in details)
    assert all(x["legal_parent_unitid"] is None and x["approved_campus_point"] is None for x in details)

    now=datetime.now(timezone.utc).isoformat()
    ledger_bytes=json.dumps({"audited_utc":now,"records":details},ensure_ascii=False,separators=(",",":")).encode()
    ledger_gzip=gzip.compress(ledger_bytes,compresslevel=9,mtime=0)
    outcome={
        "audit_utc":now,
        "original_scorecard_bulk_source":source,
        "raw_zip_downloaded_and_parsed":exact_raw_identity_verified,
        "raw_scorecard_csv_statistics":stats,
        "source_manifest_shards_sha_checked":13,
        "source_manifest_sha256":hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "national_json_sha256":hashlib.sha256(JSON_PATH.read_bytes()).hexdigest(),
        "nces_hd2025_sha256":meta["zip_sha256"],
        "national_record_count":6243,
        "six_digit_keys":5787,
        "eight_digit_keys":456,
        "scorecard_projected_source_identities_hash_verified":6243,
        "all_456_extracted_from_checked_in_source_shards":True,
        "all_456_original_bulk_UNITID_values_rechecked_this_run":exact_raw_identity_verified,
        "eight_digit_source_key_equals_opeid8_confirmed_count":source_opeid_equal if exact_raw_identity_verified else None,
        "opeid6_and_opeid8_could_be_retrieved":exact_raw_identity_verified,
        "classification_counts":dict(sorted(classes.items())),
        "per_state_classes":{k:dict(sorted(v.items())) for k,v in sorted(states.items())},
        "unique_numeric_prefixes":len(prefixes),
        "top_prefix_counts":[{"prefix":k,"record_count":v} for k,v in prefixes.most_common(15)],
        "new_official_ipeds_unitid_crosswalk_approvals":0,
        "new_legal_parent_relation_approvals":0,"new_geocodes_approved":0,
        "national_source_rows_preserved":6243,
        "existing_browser_gzip_bytes":GZIP_PATH.stat().st_size,
        "existing_browser_budget_limit":BUDGET_BYTES,
        "existing_browser_headroom":BUDGET_BYTES-GZIP_PATH.stat().st_size,
        "research_ledger_gzip_bytes_separate_from_browser":len(ledger_gzip),
        "wordpress_edited":False,"browser_data_replaced":False,
        "source_caveat":"Original ED bulk ZIP unavailable via direct CDN on this runner; 13 source projection shards and pinned manifest still verified, but Scorecard raw OPEID8/OPEID6 remain null until retrieval.",
        "release_notes":"Existing 456 eight-digit source-projected keys should not be labeled independently verified 6-digit NCES UNITIDs. Preserve source exact string identity, no guess at campus/parent.",
    }
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    SUMMARY.write_text(json.dumps(outcome,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    LEDGER.parent.mkdir(parents=True,exist_ok=True)
    LEDGER.write_text(json.dumps({"audited_utc":now,"records":details},indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    report=[
      "# S3-09 — National source identifier provenance (456 eight-digit keys)",
      "",
      "**Audit:** "+now+" UTC. **Research only — WordPress/production dataset unchanged.**",
      "",
      "## Verified facts",
      "",
      "All **6,243** national records and 13 previously SHA-pinned projection shards validate identically. "
      "The source manifest declares the June 10, 2026 College Scorecard institution-level ZIP with "
      "archive SHA-256 "+manifest["source_archive_sha256"]+". **5,787 national record keys are six digits; "
      "456 are eight digits.** Every eight-digit value occurs in those checked-in source-derived shards. "
      "The official **2025 NCES IPEDS directory** was also re-downloaded with pinned SHA-256 "+
      meta["zip_sha256"]+".",
      "",
      "## Original Scorecard ZIP retrieval",
      "",
    ]
    if exact_raw_identity_verified:
        report.append("**Original bulk archive verified:** source downloaded with SHA pin and all 6,243 UNITID/name/city/state records exact. Original OPEID6/OPEID8 source columns inspected.")
        report.append("Scorecard original UNITID8 equals original OPEID8: "+str(source_opeid_equal)+" records.")
    else:
        report.append("**BLOCKED:** official source ZIP "+manifest["source_archive_url"]+
                      " returned "+source.get("unavailable_error","unavailable")+
                      ". Therefore **this run has NOT independently verified the original CSV UNITID/OPEID fields**. "
                      "Eight-digit IDs are SHA-validated in the national projected source shards, "
                      "but genuine raw OPEID6 and OPEID8 values are **unknown/null**. "
                      "The earlier manifest's source-archive SHA is retained as a recorded provenance claim, not falsely counted as a newly downloaded archive.")
    report.extend([
      "",
      "## Classification for all 456 source-projected extended keys",
      "",
      "| Evidence class (not a legal parent/branch proof) | Records |",
      "|---|---:|",
    ])
    for k,v in sorted(classes.items()):
        report.append("| "+k.replace("_"," ")+" | "+str(v)+" |")
    report.extend([
      "",
      "Distinct six-digit numeric prefixes: "+str(len(prefixes))+". A prefix that exists as an official 2025 NCES UNITID may indicate a reporting-family relationship, but it is not a certified parent crosswalk. Never inherit its geolocation.",
      "",
      "## Schema and data-release planning",
      "",
      "See [identity migration contract](./S3_09_IDENTIFIER_SCHEMA.md). Stable source record keys must remain strings and all 456 eight-digit records must be preserved. "
      "Do not collapse Scorecard projected source UNITID, six-digit NCES survey identifier, eight-digit OPEID, or physical campus into a single field. "
      "Until the original 2026 ZIP or authoritative crosswalk can be fetched, both OPEID fields remain **null**, not inferred from the numeric prefix.",
      "",
      "The full no-coordinate 456-row classification ledger is stored as a 30-day GitHub Actions artifact. "
      "Persistent aggregate evidence: [S3-09 JSON](./research_aggregate/s3_09_identity_provenance_summary.json).",
      "",
      "Original unchanged Sprint 2 data payload gzip: "+str(GZIP_PATH.stat().st_size)+" bytes / "+str(BUDGET_BYTES)+
      " budget, headroom "+str(BUDGET_BYTES-GZIP_PATH.stat().st_size)+
      ". No enriched browser asset created; research-ledger gzip estimate "+str(len(ledger_gzip))+" bytes is not a browser release measurement.",
      "",
      "No new parent/NCES UNITID approvals, campus points, ZIP distance, browser filter, or WordPress edits.",
      "",
      "Publisher references: [College Scorecard source](https://collegescorecard.ed.gov/data/), "
      "[Scorecard institutional technical documentation](https://collegescorecard.ed.gov/files/InstitutionDataDocumentation.pdf), "
      "[official NCES institution groupings](https://nces.ed.gov/ipeds/use-the-data/institutional-groupings-in-ipeds).",
    ])
    REPORT.write_text("\n".join(report)+"\n",encoding="utf-8")
    schema=[
      "# S3-09 — Proposed nonbreaking identity schema (not deployed)",
      "",
      "| Property | Interpretation |",
      "|---|---|",
      "| record_key | Required source-scoped opaque string, exactly as present in national 2026 Scorecard projection (6 or 8 digits); preserve 6,243 keys. |",
      "| scorecard_source_unitid | Source-reported UNITID field in the original Scorecard projection. Retain eight-digit strings without declaring them NCES six-digit reporting IDs. |",
      "| nces_ipeds_unitid | Nullable, six-digit official reporting-unit identifier; populate with exact corroborating NCES records/crosswalk, never truncation. |",
      "| opeid6 | Nullable six-digit federal aid identifier directly copied from raw federal Scorecard OPEID6 once accessible. |",
      "| opeid8 | Nullable eight-digit federal aid identifier directly copied from raw Scorecard OPEID. Do not copy the eight-digit UNITID key into it. |",
      "| source_id_class | six_digit_scorecard_source or eight_digit_scorecard_source; no automatic legal campus/branch label. |",
      "| parent_record_key | Null unless affirmative official dated crosswalk proves a reporting relationship, not same six-digit prefix alone. |",
      "| verified_campus_point | Null absent campus-specific verified physical address and point, not Scorecard reporting city or Census internal point. |",
      "| provenance | Source URL, archive SHA, shard SHA, source field, survey vintage, any NCES/OPEID crosswalk version, evidence review status. |",
      "",
      "## Deployment gate",
      "",
      "1. Keep existing 6,243 exact source keys and current one-active-filter/locale/size behavior unchanged. Introduce the schema as a research adapter/optional sidecar before user-facing copy.",
      "2. Do not label all 6,243 keys certified IPEDS UNITIDs; show College Scorecard source record identifier as the neutral term.",
      "3. Reattempt official June 2026 bulk ZIP or dated federal UNITID/OPEID crosswalk through authorized source; leave OPEID6/OPEID8 and legal parent unknown until verified.",
      "4. Regression test exact 5,787/456 partition, IDs as strings, source hash/unique keys, no merging of branch locations, null on missing info and unchanged sort/filter results.",
      "5. Any proposed new browser payload needs an independent deterministic 750 KiB gzip comparison; original file used 177,188 bytes, not evidence that a new asset passes.",
      "6. Separate owner approval and authenticated WordPress Draft + mobile/accessibility/host-LCP QA for public wording or feature launch.",
      "",
    ]
    SCHEMA.write_text("\n".join(schema),encoding="utf-8")
    print("S3_09_SOURCE_AUDIT_PASS "+json.dumps({
       "raw_zip":exact_raw_identity_verified,"schools":6243,"six":5787,"extended":456,
       "classes":dict(classes),"prefixes":len(prefixes),"nces2025_verified":True,
       "old_gzip_bytes":GZIP_PATH.stat().st_size
    },sort_keys=True))

if __name__=="__main__":
    main()
