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
    manifest=json.loads(MANIFEST.read_text())
    rebuilt,_,_=build()  # independently SHA validates 13 immutable original source shards
    national=json.loads(JSON_PATH.read_text())
    if rebuilt!=national:raise RuntimeError("Committed national JSON differs from source-shard reconstruction")
    if gzip.decompress(GZIP_PATH.read_bytes())!=JSON_PATH.read_bytes():raise RuntimeError("gzip mismatch")
    if GZIP_PATH.stat().st_size>BUDGET_BYTES:raise RuntimeError("existing gzip over 750 KiB")
    schools=national["institutions"]
    short={k for k in schools if len(k)==6}
    long={k for k in schools if len(k)==8}
    if len(schools)!=6243 or len(short)!=5787 or len(long)!=456:
        raise RuntimeError("Unexpected nationwide ID counts")
    raw,source=original_scorecard_archive(manifest)
    original,statistics=get_source_rows(raw,set(schools))
    if len(original)!=6243:raise RuntimeError("Original Scorecard archive does not have all 6243 source UNITIDs")
    bad=[key for key,school in schools.items()
         if original[key]["name"]!=school["name"]
         or original[key]["city"]!=school["city"]
         or original[key]["state"]!=school["state"]
         or original[key]["operating"]!="1"]
    if bad: raise RuntimeError("Scorecard source-vs-compact identity mismatch: "+repr(bad[:9]))
    assert statistics["source_rows"]==6273 and statistics["operating_source_rows"]==6243

    nces,meta,probes=checked_official_archive()
    if not meta:raise RuntimeError("Official HD2025 unavailable "+repr(probes))
    prev=json.loads((BASE/"s3_07_hd2025_source_recovery.json").read_text())
    if meta["zip_sha256"]!=prev["hd2025_metadata"]["zip_sha256"]:
        raise RuntimeError("IPEDS 2025 digest drift")

    classes=Counter()
    field_quality=Counter()
    state_stats=defaultdict(Counter)
    entries=[]
    for key in sorted(long):
        item=original[key]
        ope8=fixed(item["opeid"],8)
        ope6=fixed(item["opeid6"],6)
        prefix=key[:6]
        prefix_scorecard=original.get(prefix)
        prefix_nces=nces.get(prefix)
        match_ope6=bool(prefix_scorecard and ope6 and fixed(prefix_scorecard["opeid6"],6)==ope6)
        if match_ope6 and prefix_nces:
            category="federal_source_opeid6_shared_with_six_digit_prefix_record"
        elif prefix_scorecard and prefix_nces:
            category="prefix_observed_in_scorecard_and_nces_opeid6_not_confirmed_shared"
        elif prefix_scorecard:
            category="prefix_observed_in_scorecard_only"
        elif prefix_nces:
            category="prefix_observed_in_nces_only"
        else:
            category="no_six_digit_prefix_source_record"
        classes[category]+=1
        state_stats[item["state"]][category]+=1
        if ope8 is None:field_quality["opeid8_missing_or_invalid"]+=1
        if ope6 is None:field_quality["opeid6_missing_or_invalid"]+=1
        if key==ope8:field_quality["scorecard_unitid8_equals_opeid8"]+=1
        if key in nces:raise RuntimeError("Unexpected 8-digit key in NCES 2025 UNITID")
        entries.append({
          "record_key":key,
          "source_unitid_raw":key,
          "source_record_type":"scorecard_report_unit_8_digit_source_id",
          "source_opeid8":ope8,"source_opeid6":ope6,
          "source_name":item["name"],"source_city":item["city"],"source_state":item["state"],
          "six_digit_numeric_prefix":prefix,
          "prefix_in_scorecard":bool(prefix_scorecard),
          "prefix_in_nces_2025":bool(prefix_nces),
          "same_scorecard_opeid6_as_prefix_record":match_ope6,
          "category":category,
          "nces_ipeds_unitid_confirmed_for_this_record":None,
          "verified_legal_parent_unitid":None,
          "approved_campus_coordinates":None,
          "approved_census_place_geoid":None,
        })
    assert len(entries)==456 and sum(classes.values())==456
    assert len({x["record_key"] for x in entries})==456
    assert all(x["nces_ipeds_unitid_confirmed_for_this_record"] is None for x in entries)
    assert all(x["verified_legal_parent_unitid"] is None for x in entries)

    now=datetime.now(timezone.utc).isoformat()
    compressed=gzip.compress(json.dumps(entries,separators=(",",":"),ensure_ascii=False).encode(),compresslevel=9,mtime=0)
    results={
      "audit_utc":now,"official_scorecard_zip":source,"official_csv":statistics,
      "official_nces_2025_zip_sha256":meta["zip_sha256"],
      "scorecard_shard_manifest_sha256":hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
      "source_compact_v2_sha256":hashlib.sha256(JSON_PATH.read_bytes()).hexdigest(),
      "institution_records":6243,"six_digit_record_keys":5787,"eight_digit_record_keys":456,
      "exact_original_scorecard_unitid_name_city_state_matches":6243,
      "all_456_long_values_proven_exact_original_scorecard_UNITID_field":True,
      "source_opeid_field_quality":dict(field_quality),
      "extended_456_source_categories":dict(sorted(classes.items())),
      "by_state":{k:dict(sorted(v.items())) for k,v in sorted(state_stats.items())},
      "old_national_gzip_bytes":GZIP_PATH.stat().st_size,
      "old_national_budget_bytes":BUDGET_BYTES,
      "old_national_budget_headroom_bytes":BUDGET_BYTES-GZIP_PATH.stat().st_size,
      "research_ledger_gzip_bytes_not_browser_payload":len(compressed),
      "new_nces_ipeds_unitid_links_approved":0,"new_legal_branch_links_approved":0,
      "new_campus_geo_links_approved":0,"nationwide_records_preserved":6243,
      "word_press_edited":False,"publication_authorized":False,
      "limits":[
        "8-digit Scorecard UNITID is original federal source data, not fabricated by matcher. NCES 2025 six-digit UNITID identity remains separate.",
        "Scorecard source UNITID, OPEID6 and OPEID8 are separately reported fields and must not be numerically conflated.",
        "Shared OPEID6 and a numeric Scorecard UNITID prefix are association signals, not certified legal parent-child relationships or campus coordinates.",
        "The existing browser JSON remains unchanged; future provenance schema requires authorized reviewed publication."
      ],
    }
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    SUMMARY.write_text(json.dumps(results,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    LEDGER.parent.mkdir(parents=True,exist_ok=True)
    LEDGER.write_text(json.dumps({"audited_utc":now,"records":entries},indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    paragraphs=[
      "# S3-09 — Original Scorecard UNITID provenance for all 456 extended IDs","",
      "**Audited UTC:** "+now,"",
      "## What the original federal bulk archive proves","",
      "Downloaded the original US Department of Education College Scorecard June 10, 2026 archive from "
      +source["original_url"]+" with SHA-256 "+source["sha256"]+" matching the 13-shard national manifest. "
      "The source CSV contains "+str(statistics["source_rows"])+" rows, of which "+
      str(statistics["operating_source_rows"])+" are operating. **All 6,243 national records match the original "
      "CSV UNITID, name, city, state and operating status exactly**, including **all 456 eight-digit UNITID values**. "
      "Thus these extended IDs are genuine College Scorecard source keys, not IDs fabricated by the matcher. "
      "They must not, however, be represented as six-digit NCES IPEDS UNITIDs or confused with OPEIDs.","",
      "- Six-digit Scorecard UNITID values: **5,787**.",
      "- Eight-digit Scorecard UNITID values: **456**.",
      "- Official 2025 NCES IPEDS directory ZIP SHA-256: "+meta["zip_sha256"]+".",
      "- Original source OPEID8 equals the eight-digit Scorecard UNITID in "+
      str(field_quality["scorecard_unitid8_equals_opeid8"])+" cases. Similar length never implies OPEID equivalence.","",
      "## Classification of all 456 extended source values","",
      "| Source evidence (not legal parent-child proof) | Rows |","|---|---:|"
    ]
    for k,v in sorted(classes.items()):
        paragraphs.append("| "+k.replace("_"," ")+" | "+str(v)+" |")
    paragraphs.extend([
      "","All 456 are Scorecard source-record IDs. An apparent six-digit UNITID prefix is a candidate association "
      "only, even if the source reports matching OPEID6. Legal parent, NCES six-digit survey identity, "
      "campus address and coordinates remain unverified/nullable.","",
      "## Publication-safe design","",
      "See [S3-09 identifier migration specification](./S3_09_IDENTIFIER_SCHEMA.md). Preserve the "
      "existing stable exact-string Scorecard key; separate optional six-digit NCES UNITID, explicit "
      "source OPEID6 and source OPEID8, parent relationship with authority/date, and physical campus location. "
      "Do not omit or merge the 456 extended source entries. Do not claim that the entire keyspace is IPEDS UNITIDs.","",
      "## Asset constraints","",
      "The **existing unchanged** Sprint 2 browser gzip payload is "+str(GZIP_PATH.stat().st_size)+
      " bytes with "+str(BUDGET_BYTES-GZIP_PATH.stat().st_size)+" bytes headroom under 750 KiB. "
      "The proposed enriched browser asset has **not** been built or size-tested; the separate research-only "
      "456-case ledger would gzip to "+str(len(compressed))+" bytes, which is NOT a release-budget assertion.","",
      "The complete 456 source/OPEID records are retained in a 30-day GitHub Actions research artifact; "
      "source/classification aggregates persist in [JSON summary](./research_aggregate/s3_09_identity_provenance_summary.json). "
      "No WordPress, data, live filter, geocode, or geographic launch changes.","",
      "References: [College Scorecard source and downloads](https://collegescorecard.ed.gov/data/); "
      "[official institution documentation](https://collegescorecard.ed.gov/files/InstitutionDataDocumentation.pdf); "
      "[NCES reporting-unit distinctions](https://nces.ed.gov/ipeds/use-the-data/institutional-groupings-in-ipeds)."
    ])
    REPORT.write_text("\n".join(paragraphs)+"\n")
    plan=[
      "# S3-09 — Proposed identifier schema (not deployed)","",
      "## Separate these identities (strings, not integers)","",
      "| Field | Rule |","|---|---|",
      "| record_key | Required opaque stable string: exact original Scorecard source UNITID, preserving all 6,243 rows and all 456 eight-digit IDs. |",
      "| scorecard_unitid_raw | Required original source UNITID from the SHA-pinned 2026 Scorecard archive. |",
      "| source_dataset | Scorecard most recent institution, released June 10, 2026. |",
      "| nces_ipeds_unitid | Nullable six-digit NCES reporting-unit identifier; must be independently corroborated, not derived by trimming record_key. |",
      "| opeid6 | Nullable six-digit value taken from exact raw Scorecard OPEID6, not inferred from UNITID. |",
      "| opeid8 | Nullable eight-digit value taken from exact raw Scorecard OPEID, never confused with the eight-digit UNITID. |",
      "| reported_unit_kind | Enum: Scorecard original six-digit record; Scorecard original extended record; separately verified campus; unresolved. |",
      "| parent_unitid | Null until explicit federal dated crosswalk independently approves a relation; numeric prefix and common OPEID6 alone not sufficient. |",
      "| verified_campus_location | False/null until authoritative campus location provenance independently checked. |",
      "| census_place_geoid | Nullable validated Census place proxy, not campus coordinates or driving distance. |",
      "| provenance | Publisher URL; source ZIP SHA; source field; release/vintage; per-relationship evidence and verification date. |",
      "",
      "## Separate release (not part of S3-09)","",
      "1. Keep original 6,243-key JSON lookup and single-active-filter behavior exactly unchanged; add a nonbreaking lookup adapter or optional compact provenance sidecar.",
      "2. Correct user-facing wording from all keyed by IPEDS UNITID to source-scoped College Scorecard record IDs after owner review; do not change the WordPress pages during research.",
      "3. Populate OPEIDs from the source, not numeric prefixes; keep nces_ipeds_unitid and parent_unitid null unless explicit crosswalk supports the record.",
      "4. Unit test 6,243 distinct unchanged keys, 5,787 six-digit + 456 eight-digit, source SHA, original name/city/state equality, unchanged filter and sorting results.",
      "5. Check deterministic gzip for any new sidecar/combined browser asset. Limit <= 750 KiB; verify dynamic controls, mobile QA, accessibility and host LCP independently.",
      "6. No new automatic six-digit parent campus coordinates, distance metrics, USPS-ZIP or campus accessibility assumptions.",
      "",
      "## Next work gate","",
      "Obtain official dated OPEID-to-UNITID crosswalk for the source vintage, and decide which six-digit NCES relationships can be verified. Do not conflate original extended Scorecard source IDs with OPEIDs; preserve the 456 institution/campus records.",""
    ]
    SCHEMA.write_text("\n".join(plan),encoding="utf-8")
    print("S3_09_SOURCE_CHECK_PASS "+json.dumps({"national":6243,"six_digit":5787,"eight_digit":456,
      "categories":dict(classes),"opeid_equal_unitid8":field_quality["scorecard_unitid8_equals_opeid8"],
      "scorecard_archive_sha256":source["sha256"],"existing_gzip_bytes":GZIP_PATH.stat().st_size,
      "research_ledger_gzip_bytes":len(compressed)},sort_keys=True))

if __name__=="__main__":
    main()
